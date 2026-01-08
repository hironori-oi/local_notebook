"""
LLM Client - Abstraction layer for LLM providers (Ollama, vLLM, etc.)

Supports Ollama native API (/api/chat) and OpenAI-compatible API (/v1/chat/completions).
The provider can be switched via LLM_PROVIDER environment variable or user-specific DB settings.
"""

import json
import logging
from typing import TYPE_CHECKING, AsyncGenerator, Dict, List, Optional
from uuid import UUID

import httpx

from app.core.config import settings

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class LLMClient:
    """
    Unified LLM client supporting multiple providers.

    Supported providers:
    - ollama: Local Ollama server using native API (/api/chat)
    - vllm: vLLM server using OpenAI-compatible API (/v1/chat/completions)
    """

    def __init__(
        self,
        api_base: Optional[str] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
        timeout: float = 120.0,
        max_tokens: Optional[int] = None,
    ):
        self.api_base = api_base or settings.LLM_API_BASE
        self.model = model or settings.LLM_MODEL
        self.provider = provider or settings.LLM_PROVIDER
        self.timeout = timeout
        self.max_tokens = max_tokens or settings.LLM_MAX_TOKENS

    async def chat(
        self,
        messages: List[Dict],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> str:
        """
        Send chat completion request and return the response content.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response (not yet implemented)

        Returns:
            The assistant's response content as a string
        """
        # Use provided max_tokens or fall back to instance default
        tokens_limit = max_tokens or self.max_tokens

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                if self.provider == "ollama":
                    # Ollama native API
                    resp = await client.post(
                        f"{self.api_base}/api/chat",
                        json={
                            "model": self.model,
                            "messages": messages,
                            "stream": False,
                            "options": {
                                "temperature": temperature,
                                "num_predict": tokens_limit,
                            },
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return data["message"]["content"]
                else:
                    # OpenAI-compatible API (vLLM, etc.)
                    resp = await client.post(
                        f"{self.api_base}/v1/chat/completions",
                        json={
                            "model": self.model,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": tokens_limit,
                            "stream": stream,
                        },
                    )
                    resp.raise_for_status()
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
        except httpx.TimeoutException as e:
            error_msg = f"LLM request timed out after {self.timeout}s (model: {self.model}, provider: {self.provider})"
            logger.error(error_msg)
            raise TimeoutError(error_msg) from e
        except httpx.ConnectError as e:
            error_msg = f"Failed to connect to LLM server at {self.api_base} (provider: {self.provider})"
            logger.error(error_msg)
            raise ConnectionError(error_msg) from e
        except httpx.HTTPStatusError as e:
            error_msg = f"LLM server returned error: HTTP {e.response.status_code} - {e.response.text[:200]}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e
        except Exception as e:
            error_msg = (
                f"LLM request failed: {type(e).__name__}: {str(e) or 'No details'}"
            )
            logger.error(error_msg)
            raise

    async def chat_stream(
        self,
        messages: List[Dict],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Send chat completion request with streaming and yield response chunks.

        Args:
            messages: List of message dicts with 'role' and 'content' keys
            temperature: Sampling temperature (0.0 - 1.0)
            max_tokens: Maximum tokens to generate

        Yields:
            Response content chunks as they arrive
        """
        # Use provided max_tokens or fall back to instance default
        tokens_limit = max_tokens or self.max_tokens

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            if self.provider == "ollama":
                # Ollama native streaming API
                async with client.stream(
                    "POST",
                    f"{self.api_base}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": True,
                        "options": {
                            "temperature": temperature,
                            "num_predict": tokens_limit,
                        },
                    },
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                content = data.get("message", {}).get("content", "")
                                if content:
                                    yield content
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                continue
            else:
                # OpenAI-compatible streaming API
                async with client.stream(
                    "POST",
                    f"{self.api_base}/v1/chat/completions",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": tokens_limit,
                        "stream": True,
                    },
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str.strip() == "[DONE]":
                                break
                            try:
                                data = json.loads(data_str)
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                            except json.JSONDecodeError:
                                continue

    async def health_check(self) -> Dict:
        """
        Check if the LLM server is reachable and responsive.

        Returns:
            Dict with 'status', 'provider', 'model', and optional 'error' keys
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if self.provider == "ollama":
                    # Ollama native API - check tags endpoint
                    resp = await client.get(f"{self.api_base}/api/tags")
                else:
                    # OpenAI-compatible API
                    resp = await client.get(f"{self.api_base}/v1/models")

                if resp.status_code == 200:
                    return {
                        "status": "healthy",
                        "provider": self.provider,
                        "model": self.model,
                        "api_base": self.api_base,
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "provider": self.provider,
                        "model": self.model,
                        "error": f"HTTP {resp.status_code}",
                    }
        except Exception as e:
            return {
                "status": "unreachable",
                "provider": self.provider,
                "model": self.model,
                "api_base": self.api_base,
                "error": str(e),
            }


# Default client instance
_default_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Get the default LLM client instance (singleton)."""
    global _default_client
    if _default_client is None:
        _default_client = LLMClient()
    return _default_client


async def call_llm(messages: List[Dict]) -> str:
    """
    Convenience function for simple chat completion.

    This maintains backward compatibility with existing code.
    """
    client = get_llm_client()
    return await client.chat(messages)


# =============================================================================
# Generation LLM Client (for infographic/slide generation)
# =============================================================================

_generation_client: Optional[LLMClient] = None


def get_generation_llm_client() -> LLMClient:
    """
    Get the generation-specific LLM client instance (singleton).

    Uses GENERATION_LLM_MODEL if set, otherwise falls back to LLM_MODEL.
    Uses GENERATION_LLM_MAX_TOKENS for longer outputs needed for structured generation.
    Uses a longer timeout (300s) for complex generation tasks.
    """
    global _generation_client
    if _generation_client is None:
        model = settings.GENERATION_LLM_MODEL or settings.LLM_MODEL
        _generation_client = LLMClient(
            model=model,
            max_tokens=settings.GENERATION_LLM_MAX_TOKENS,
            timeout=300.0,  # 5 minutes for large model generation
        )
    return _generation_client


async def call_generation_llm(messages: List[Dict], temperature: float = 0.3) -> str:
    """
    Call LLM for content generation tasks (infographics, slides, etc.).

    Uses a slightly higher temperature than the default chat for more
    creative structured output generation.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        temperature: Sampling temperature (default: 0.3 for balanced creativity)

    Returns:
        The assistant's response content as a string
    """
    client = get_generation_llm_client()
    return await client.chat(messages, temperature=temperature)


# =============================================================================
# User-specific LLM Settings Functions
# =============================================================================

# Cache for user settings (short TTL)
_user_settings_cache: Dict[UUID, tuple] = {}  # user_id -> (settings, timestamp)
_CACHE_TTL_SECONDS = 30


def get_user_llm_settings(db: "Session", user_id: UUID) -> Optional["LLMSettings"]:
    """
    Get user-specific LLM settings from database.

    Uses a short-lived cache to reduce database queries.

    Args:
        db: Database session
        user_id: User's UUID

    Returns:
        LLMSettings model or None if not found
    """
    import time

    from app.models.llm_settings import LLMSettings

    # Check cache
    if user_id in _user_settings_cache:
        cached_settings, timestamp = _user_settings_cache[user_id]
        if time.time() - timestamp < _CACHE_TTL_SECONDS:
            return cached_settings

    # Query database
    user_settings = db.query(LLMSettings).filter(LLMSettings.user_id == user_id).first()

    # Update cache
    if user_settings:
        _user_settings_cache[user_id] = (user_settings, time.time())

    return user_settings


def clear_user_settings_cache(user_id: Optional[UUID] = None):
    """
    Clear user settings cache.

    Args:
        user_id: Specific user to clear, or None to clear all
    """
    global _user_settings_cache
    if user_id:
        _user_settings_cache.pop(user_id, None)
    else:
        _user_settings_cache.clear()


def create_llm_client_for_user(
    db: "Session",
    user_id: UUID,
    feature: str = "chat",
) -> LLMClient:
    """
    Create an LLM client configured with user-specific settings.

    Args:
        db: Database session
        user_id: User's UUID
        feature: Feature name to get specific settings for
                 (chat, format, summary, email, infographic)

    Returns:
        Configured LLMClient instance
    """
    user_settings = get_user_llm_settings(db, user_id)

    if user_settings:
        # Use user-specific settings
        model = user_settings.get_model_for_feature(feature)
        temperature = user_settings.get_temperature_for_feature(feature)
        max_tokens = user_settings.get_max_tokens_for_feature(feature)

        return LLMClient(
            api_base=user_settings.api_base_url,
            model=model,
            provider=user_settings.provider,
            timeout=(
                300.0
                if feature in ["format", "summary", "email", "infographic"]
                else 120.0
            ),
            max_tokens=max_tokens,
        )
    else:
        # Fall back to environment-based settings
        if feature in ["format", "summary", "email", "infographic"]:
            return get_generation_llm_client()
        else:
            return get_llm_client()


async def call_llm_with_user_settings(
    db: "Session",
    user_id: UUID,
    messages: List[Dict],
    feature: str = "chat",
    temperature: Optional[float] = None,
) -> str:
    """
    Call LLM using user-specific settings.

    Args:
        db: Database session
        user_id: User's UUID
        messages: List of message dicts with 'role' and 'content' keys
        feature: Feature name for settings lookup
        temperature: Override temperature (uses user setting if None)

    Returns:
        The assistant's response content as a string
    """
    user_settings = get_user_llm_settings(db, user_id)

    if user_settings:
        client = create_llm_client_for_user(db, user_id, feature)
        temp = (
            temperature
            if temperature is not None
            else user_settings.get_temperature_for_feature(feature)
        )
        return await client.chat(messages, temperature=temp)
    else:
        # Fall back to default behavior
        if feature in ["format", "summary", "email", "infographic"]:
            return await call_generation_llm(messages, temperature=temperature or 0.3)
        else:
            client = get_llm_client()
            return await client.chat(messages, temperature=temperature or 0.1)
