"""
LLM Settings API endpoints for managing user-specific LLM configurations.
"""
import logging
import time
from typing import Optional
from uuid import UUID

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.core.config import settings as app_settings
from app.models.llm_settings import LLMSettings, DEFAULT_FEATURE_SETTINGS, DEFAULT_PROMPT_SETTINGS
from app.models.user import User
from app.schemas.llm_settings import (
    LLMSettingsOut,
    LLMSettingsUpdate,
    LLMConnectionTestRequest,
    LLMConnectionTestResponse,
    ModelsListResponse,
    ModelInfo,
    PromptSettingsUpdate,
    DefaultPromptsOut,
)
from app.services.council_content_processor import (
    COUNCIL_SUMMARY_SYSTEM_PROMPT,
    COUNCIL_SUMMARY_USER_TEMPLATE,
    COUNCIL_MINUTES_SUMMARY_SYSTEM_PROMPT,
    COUNCIL_MINUTES_SUMMARY_USER_TEMPLATE,
)
from app.services.email_generator import (
    EMAIL_SYSTEM_PROMPT,
    EMAIL_USER_TEMPLATE,
)
from app.services.infographic_planner import (
    INFOGRAPHIC_SYSTEM_PROMPT,
    INFOGRAPHIC_USER_TEMPLATE,
)
from app.services.council_infographic_planner import (
    COUNCIL_INFOGRAPHIC_SYSTEM_PROMPT,
    COUNCIL_INFOGRAPHIC_USER_TEMPLATE,
)
from app.services.content_processor import (
    FORMAT_SYSTEM_PROMPT,
    FORMAT_USER_TEMPLATE,
    MINUTE_FORMAT_SYSTEM_PROMPT,
    MINUTE_FORMAT_USER_TEMPLATE,
    SUMMARY_SYSTEM_PROMPT,
    SUMMARY_USER_TEMPLATE,
    MINUTE_SUMMARY_SYSTEM_PROMPT,
    MINUTE_SUMMARY_USER_TEMPLATE,
)
from app.services.document_checker import (
    DOCUMENT_CHECK_SYSTEM_PROMPT,
    DOCUMENT_CHECK_USER_TEMPLATE,
)
from app.services.slide_generator import (
    SLIDE_GENERATION_SYSTEM_PROMPT,
    SLIDE_GENERATION_USER_TEMPLATE,
    SLIDE_REFINEMENT_SYSTEM_PROMPT,
    SLIDE_REFINEMENT_USER_TEMPLATE,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings/llm", tags=["llm-settings"])


def _get_or_create_settings(db: Session, user_id: UUID) -> LLMSettings:
    """Get user's LLM settings or create default if not exists."""
    settings = db.query(LLMSettings).filter(LLMSettings.user_id == user_id).first()

    if not settings:
        # Create default settings for user
        settings = LLMSettings(
            user_id=user_id,
            provider=app_settings.LLM_PROVIDER,
            api_base_url=app_settings.LLM_API_BASE,
            default_model=app_settings.LLM_MODEL,
            embedding_model=app_settings.EMBEDDING_MODEL,
            embedding_api_base=app_settings.EMBEDDING_API_BASE,
            embedding_dim=app_settings.EMBEDDING_DIM,
            feature_settings=DEFAULT_FEATURE_SETTINGS,
            prompt_settings=DEFAULT_PROMPT_SETTINGS,
        )
        db.add(settings)
        db.commit()
        db.refresh(settings)
        logger.info(f"Created default LLM settings for user {user_id}")

    return settings


def _settings_to_response(settings: LLMSettings) -> LLMSettingsOut:
    """Convert LLMSettings model to response schema."""
    return LLMSettingsOut(
        id=settings.id,
        user_id=settings.user_id,
        provider=settings.provider,
        api_base_url=settings.api_base_url,
        has_api_key=settings.api_key_encrypted is not None and len(settings.api_key_encrypted) > 0,
        default_model=settings.default_model,
        embedding_model=settings.embedding_model,
        embedding_api_base=settings.embedding_api_base,
        embedding_dim=settings.embedding_dim,
        feature_settings=settings.feature_settings or DEFAULT_FEATURE_SETTINGS,
        prompt_settings=settings.prompt_settings or DEFAULT_PROMPT_SETTINGS,
        created_at=settings.created_at,
        updated_at=settings.updated_at,
    )


@router.get("", response_model=LLMSettingsOut)
def get_llm_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current user's LLM settings.

    If no settings exist, creates default settings based on environment configuration.
    """
    settings = _get_or_create_settings(db, current_user.id)
    return _settings_to_response(settings)


@router.put("", response_model=LLMSettingsOut)
def update_llm_settings(
    data: LLMSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update current user's LLM settings.

    Only provided fields will be updated.
    """
    settings = _get_or_create_settings(db, current_user.id)

    # Update basic settings
    if data.provider is not None:
        settings.provider = data.provider
    if data.api_base_url is not None:
        settings.api_base_url = data.api_base_url
    if data.default_model is not None:
        settings.default_model = data.default_model

    # Handle API key
    if data.api_key is not None:
        if data.api_key == "":
            settings.api_key_encrypted = None  # Clear API key
        else:
            # TODO: Encrypt API key before storing
            settings.api_key_encrypted = data.api_key

    # Update embedding settings
    if data.embedding_model is not None:
        settings.embedding_model = data.embedding_model
    if data.embedding_api_base is not None:
        settings.embedding_api_base = data.embedding_api_base
    if data.embedding_dim is not None:
        settings.embedding_dim = data.embedding_dim

    # Update feature settings (merge with existing)
    if data.feature_settings is not None:
        current_features = settings.feature_settings or DEFAULT_FEATURE_SETTINGS.copy()
        for feature, feature_settings in data.feature_settings.items():
            if feature in current_features:
                current_features[feature].update(feature_settings)
            else:
                current_features[feature] = feature_settings
        settings.feature_settings = current_features

    # Update prompt settings (merge with existing)
    if data.prompt_settings is not None:
        current_prompts = settings.prompt_settings or DEFAULT_PROMPT_SETTINGS.copy()
        for key, value in data.prompt_settings.items():
            current_prompts[key] = value
        settings.prompt_settings = current_prompts

    db.commit()
    db.refresh(settings)

    logger.info(f"Updated LLM settings for user {current_user.id}")
    return _settings_to_response(settings)


@router.post("/test", response_model=LLMConnectionTestResponse)
async def test_llm_connection(
    data: LLMConnectionTestRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Test connection to LLM server.

    Sends a simple test request to verify connectivity and model availability.
    """
    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if data.provider in ["ollama"]:
                # Ollama native API test
                api_url = data.api_base_url.rstrip("/v1").rstrip("/")
                response = await client.post(
                    f"{api_url}/api/chat",
                    json={
                        "model": data.model,
                        "messages": [{"role": "user", "content": "Hello"}],
                        "stream": False,
                        "options": {"num_predict": 10},
                    },
                )
            else:
                # OpenAI-compatible API test
                headers = {}
                if data.api_key:
                    headers["Authorization"] = f"Bearer {data.api_key}"

                response = await client.post(
                    f"{data.api_base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json={
                        "model": data.model,
                        "messages": [{"role": "user", "content": "Hello"}],
                        "max_tokens": 10,
                    },
                )

            elapsed_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                return LLMConnectionTestResponse(
                    success=True,
                    message="接続成功",
                    response_time_ms=elapsed_ms,
                    model_info={"name": data.model},
                )
            else:
                error_text = response.text[:500] if response.text else "Unknown error"
                return LLMConnectionTestResponse(
                    success=False,
                    message=f"接続エラー: HTTP {response.status_code}",
                    response_time_ms=elapsed_ms,
                    error_detail=error_text,
                )

    except httpx.ConnectError as e:
        return LLMConnectionTestResponse(
            success=False,
            message="接続失敗: サーバーに接続できません",
            error_detail=str(e),
        )
    except httpx.TimeoutException:
        return LLMConnectionTestResponse(
            success=False,
            message="接続失敗: タイムアウト",
            error_detail="リクエストが30秒後にタイムアウトしました",
        )
    except Exception as e:
        logger.error(f"Connection test failed: {e}", exc_info=True)
        return LLMConnectionTestResponse(
            success=False,
            message="接続失敗: 予期しないエラー",
            error_detail=str(e),
        )


@router.get("/models", response_model=ModelsListResponse)
async def list_available_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List available models from the configured LLM server.

    Returns a list of models available on the current user's configured LLM server.
    """
    settings = _get_or_create_settings(db, current_user.id)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            if settings.provider == "ollama":
                # Ollama API
                api_url = settings.api_base_url.rstrip("/v1").rstrip("/")
                response = await client.get(f"{api_url}/api/tags")

                if response.status_code == 200:
                    data = response.json()
                    models = []
                    for model_data in data.get("models", []):
                        name = model_data.get("name", "")
                        # Extract size from name or details
                        size = None
                        details = model_data.get("details", {})
                        if details:
                            param_size = details.get("parameter_size", "")
                            if param_size:
                                size = param_size

                        models.append(ModelInfo(
                            name=name,
                            size=size,
                            family=details.get("family"),
                            modified_at=model_data.get("modified_at"),
                        ))
                    return ModelsListResponse(models=models, provider=settings.provider)

            else:
                # OpenAI-compatible API
                headers = {}
                if settings.api_key_encrypted:
                    headers["Authorization"] = f"Bearer {settings.api_key_encrypted}"

                response = await client.get(
                    f"{settings.api_base_url.rstrip('/')}/models",
                    headers=headers,
                )

                if response.status_code == 200:
                    data = response.json()
                    models = []
                    for model_data in data.get("data", []):
                        models.append(ModelInfo(
                            name=model_data.get("id", ""),
                        ))
                    return ModelsListResponse(models=models, provider=settings.provider)

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="モデル一覧の取得に失敗しました",
        )

    except httpx.ConnectError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="LLMサーバーに接続できません",
        )
    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="LLMサーバーへの接続がタイムアウトしました",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list models: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"モデル一覧の取得中にエラーが発生しました: {str(e)}",
        )


@router.get("/defaults", response_model=LLMSettingsOut)
def get_default_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get system default LLM settings (from environment variables).

    This endpoint returns the default configuration without user customizations.
    """
    # Return default settings based on environment variables
    default = LLMSettings(
        provider=app_settings.LLM_PROVIDER,
        api_base_url=app_settings.LLM_API_BASE,
        default_model=app_settings.LLM_MODEL,
        embedding_model=app_settings.EMBEDDING_MODEL,
        embedding_api_base=app_settings.EMBEDDING_API_BASE,
        embedding_dim=app_settings.EMBEDDING_DIM,
        feature_settings=DEFAULT_FEATURE_SETTINGS,
        prompt_settings=DEFAULT_PROMPT_SETTINGS,
    )

    # Create a mock response
    from datetime import datetime
    return LLMSettingsOut(
        id=UUID("00000000-0000-0000-0000-000000000000"),
        user_id=None,
        provider=default.provider,
        api_base_url=default.api_base_url,
        has_api_key=False,
        default_model=default.default_model,
        embedding_model=default.embedding_model,
        embedding_api_base=default.embedding_api_base,
        embedding_dim=default.embedding_dim,
        feature_settings=default.feature_settings,
        prompt_settings=default.prompt_settings,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )


@router.post("/reset", response_model=LLMSettingsOut)
def reset_to_defaults(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reset user's LLM settings to system defaults.
    """
    settings = db.query(LLMSettings).filter(LLMSettings.user_id == current_user.id).first()

    if settings:
        # Reset all fields to defaults
        settings.provider = app_settings.LLM_PROVIDER
        settings.api_base_url = app_settings.LLM_API_BASE
        settings.api_key_encrypted = None
        settings.default_model = app_settings.LLM_MODEL
        settings.embedding_model = app_settings.EMBEDDING_MODEL
        settings.embedding_api_base = app_settings.EMBEDDING_API_BASE
        settings.embedding_dim = app_settings.EMBEDDING_DIM
        settings.feature_settings = DEFAULT_FEATURE_SETTINGS
        settings.prompt_settings = DEFAULT_PROMPT_SETTINGS

        db.commit()
        db.refresh(settings)
        logger.info(f"Reset LLM settings to defaults for user {current_user.id}")
    else:
        settings = _get_or_create_settings(db, current_user.id)

    return _settings_to_response(settings)


@router.get("/prompts/defaults", response_model=DefaultPromptsOut)
def get_default_prompts(
    current_user: User = Depends(get_current_user),
):
    """
    Get the hardcoded default prompts.

    These are the system defaults that are used when no custom prompts are set.
    """
    return DefaultPromptsOut(
        # Council content processing
        council_materials_system=COUNCIL_SUMMARY_SYSTEM_PROMPT,
        council_materials_user=COUNCIL_SUMMARY_USER_TEMPLATE,
        council_minutes_system=COUNCIL_MINUTES_SUMMARY_SYSTEM_PROMPT,
        council_minutes_user=COUNCIL_MINUTES_SUMMARY_USER_TEMPLATE,
        # Email generation
        email_system=EMAIL_SYSTEM_PROMPT,
        email_user=EMAIL_USER_TEMPLATE,
        # Infographic generation - Notebook
        infographic_system=INFOGRAPHIC_SYSTEM_PROMPT,
        infographic_user=INFOGRAPHIC_USER_TEMPLATE,
        # Infographic generation - Council
        council_infographic_system=COUNCIL_INFOGRAPHIC_SYSTEM_PROMPT,
        council_infographic_user=COUNCIL_INFOGRAPHIC_USER_TEMPLATE,
        # Document formatting
        format_system=FORMAT_SYSTEM_PROMPT,
        format_user=FORMAT_USER_TEMPLATE,
        # Minutes formatting
        minute_format_system=MINUTE_FORMAT_SYSTEM_PROMPT,
        minute_format_user=MINUTE_FORMAT_USER_TEMPLATE,
        # Document summary
        summary_system=SUMMARY_SYSTEM_PROMPT,
        summary_user=SUMMARY_USER_TEMPLATE,
        # Minutes summary
        minute_summary_system=MINUTE_SUMMARY_SYSTEM_PROMPT,
        minute_summary_user=MINUTE_SUMMARY_USER_TEMPLATE,
        # Document checker
        document_check_system=DOCUMENT_CHECK_SYSTEM_PROMPT,
        document_check_user=DOCUMENT_CHECK_USER_TEMPLATE,
        # Slide generation
        slide_generation_system=SLIDE_GENERATION_SYSTEM_PROMPT,
        slide_generation_user=SLIDE_GENERATION_USER_TEMPLATE,
        # Slide refinement
        slide_refinement_system=SLIDE_REFINEMENT_SYSTEM_PROMPT,
        slide_refinement_user=SLIDE_REFINEMENT_USER_TEMPLATE,
    )


@router.put("/prompts", response_model=LLMSettingsOut)
def update_prompts(
    data: PromptSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update custom prompts for the current user.

    Set a value to null to use the default prompt.
    """
    settings = _get_or_create_settings(db, current_user.id)

    current_prompts = settings.prompt_settings or DEFAULT_PROMPT_SETTINGS.copy()
    for key, value in data.prompt_settings.items():
        current_prompts[key] = value
    settings.prompt_settings = current_prompts

    db.commit()
    db.refresh(settings)

    logger.info(f"Updated prompts for user {current_user.id}")
    return _settings_to_response(settings)


@router.post("/prompts/reset", response_model=LLMSettingsOut)
def reset_prompts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reset all custom prompts to defaults.
    """
    settings = _get_or_create_settings(db, current_user.id)
    settings.prompt_settings = DEFAULT_PROMPT_SETTINGS

    db.commit()
    db.refresh(settings)

    logger.info(f"Reset prompts to defaults for user {current_user.id}")
    return _settings_to_response(settings)
