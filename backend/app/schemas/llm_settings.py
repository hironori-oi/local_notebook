"""
Pydantic schemas for LLM Settings API.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, validator


class FeatureSettingBase(BaseModel):
    """Settings for a specific feature."""

    model: Optional[str] = Field(None, description="Model to use (null = use default)")
    temperature: float = Field(0.1, ge=0.0, le=2.0, description="Temperature setting")
    max_tokens: int = Field(4096, ge=100, le=32768, description="Maximum tokens")


class FeatureSettings(BaseModel):
    """All feature-specific settings."""

    chat: FeatureSettingBase = Field(
        default_factory=lambda: FeatureSettingBase(temperature=0.1, max_tokens=4096)
    )
    format: FeatureSettingBase = Field(
        default_factory=lambda: FeatureSettingBase(temperature=0.1, max_tokens=8192)
    )
    summary: FeatureSettingBase = Field(
        default_factory=lambda: FeatureSettingBase(temperature=0.2, max_tokens=8192)
    )
    email: FeatureSettingBase = Field(
        default_factory=lambda: FeatureSettingBase(temperature=0.3, max_tokens=8192)
    )
    infographic: FeatureSettingBase = Field(
        default_factory=lambda: FeatureSettingBase(temperature=0.3, max_tokens=8192)
    )


class PromptSettings(BaseModel):
    """Custom prompts for various features."""

    # Council content processing (審議会資料処理)
    council_materials_system: Optional[str] = Field(
        None, description="System prompt for council materials summary"
    )
    council_materials_user: Optional[str] = Field(
        None, description="User prompt template for council materials summary"
    )
    council_minutes_system: Optional[str] = Field(
        None, description="System prompt for council minutes summary"
    )
    council_minutes_user: Optional[str] = Field(
        None, description="User prompt template for council minutes summary"
    )
    # Email generation (メール生成)
    email_system: Optional[str] = Field(
        None, description="System prompt for email generation"
    )
    email_user: Optional[str] = Field(
        None, description="User prompt template for email generation"
    )
    # Infographic generation - Notebook (インフォグラフィック - ノートブック)
    infographic_system: Optional[str] = Field(
        None, description="System prompt for infographic generation"
    )
    infographic_user: Optional[str] = Field(
        None, description="User prompt template for infographic generation"
    )
    # Infographic generation - Council (インフォグラフィック - 審議会)
    council_infographic_system: Optional[str] = Field(
        None, description="System prompt for council infographic generation"
    )
    council_infographic_user: Optional[str] = Field(
        None, description="User prompt template for council infographic generation"
    )
    # Document formatting (テキスト整形)
    format_system: Optional[str] = Field(
        None, description="System prompt for document formatting"
    )
    format_user: Optional[str] = Field(
        None, description="User prompt template for document formatting"
    )
    # Minutes formatting (議事録整形)
    minute_format_system: Optional[str] = Field(
        None, description="System prompt for minutes formatting"
    )
    minute_format_user: Optional[str] = Field(
        None, description="User prompt template for minutes formatting"
    )
    # Document summary (資料要約)
    summary_system: Optional[str] = Field(
        None, description="System prompt for document summary"
    )
    summary_user: Optional[str] = Field(
        None, description="User prompt template for document summary"
    )
    # Minutes summary (議事録要約)
    minute_summary_system: Optional[str] = Field(
        None, description="System prompt for minutes summary"
    )
    minute_summary_user: Optional[str] = Field(
        None, description="User prompt template for minutes summary"
    )
    # Document checker (校正チェック)
    document_check_system: Optional[str] = Field(
        None, description="System prompt for document checker"
    )
    document_check_user: Optional[str] = Field(
        None, description="User prompt template for document checker"
    )
    # Slide generation (スライド生成)
    slide_generation_system: Optional[str] = Field(
        None, description="System prompt for slide generation"
    )
    slide_generation_user: Optional[str] = Field(
        None, description="User prompt template for slide generation"
    )
    # Slide refinement (スライド修正)
    slide_refinement_system: Optional[str] = Field(
        None, description="System prompt for slide refinement"
    )
    slide_refinement_user: Optional[str] = Field(
        None, description="User prompt template for slide refinement"
    )


class LLMSettingsBase(BaseModel):
    """Base schema for LLM settings."""

    provider: str = Field(
        "ollama", description="LLM provider (ollama, vllm, openai, anthropic)"
    )
    api_base_url: str = Field("http://localhost:11434/v1", description="API base URL")
    default_model: str = Field("gpt-oss-120b", description="Default model name")
    embedding_model: str = Field(
        "embeddinggemma:300m", description="Embedding model name"
    )
    embedding_api_base: str = Field(
        "http://localhost:11434/v1", description="Embedding API base URL"
    )
    embedding_dim: int = Field(768, ge=1, le=4096, description="Embedding dimension")

    @validator("provider")
    def validate_provider(cls, v):
        allowed = ["ollama", "vllm", "openai", "anthropic"]
        if v.lower() not in allowed:
            raise ValueError(f"Provider must be one of: {', '.join(allowed)}")
        return v.lower()


class LLMSettingsCreate(LLMSettingsBase):
    """Schema for creating LLM settings."""

    api_key: Optional[str] = Field(None, description="API key (for OpenAI/Anthropic)")
    feature_settings: Optional[Dict[str, Dict[str, Any]]] = Field(
        None, description="Feature-specific settings"
    )
    prompt_settings: Optional[Dict[str, Optional[str]]] = Field(
        None, description="Custom prompts for features"
    )


class LLMSettingsUpdate(BaseModel):
    """Schema for updating LLM settings (all fields optional)."""

    provider: Optional[str] = None
    api_base_url: Optional[str] = None
    api_key: Optional[str] = Field(
        None, description="API key (set to empty string to clear)"
    )
    default_model: Optional[str] = None
    embedding_model: Optional[str] = None
    embedding_api_base: Optional[str] = None
    embedding_dim: Optional[int] = Field(None, ge=1, le=4096)
    feature_settings: Optional[Dict[str, Dict[str, Any]]] = None
    prompt_settings: Optional[Dict[str, Optional[str]]] = None

    @validator("provider")
    def validate_provider(cls, v):
        if v is None:
            return v
        allowed = ["ollama", "vllm", "openai", "anthropic"]
        if v.lower() not in allowed:
            raise ValueError(f"Provider must be one of: {', '.join(allowed)}")
        return v.lower()


class LLMSettingsOut(LLMSettingsBase):
    """Schema for LLM settings response."""

    id: UUID
    user_id: Optional[UUID] = None
    has_api_key: bool = Field(False, description="Whether API key is set")
    feature_settings: Dict[str, Dict[str, Any]]
    prompt_settings: Dict[str, Optional[str]] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PromptSettingsUpdate(BaseModel):
    """Schema for updating only prompt settings."""

    prompt_settings: Dict[str, Optional[str]] = Field(
        ..., description="Custom prompts to update"
    )


class DefaultPromptsOut(BaseModel):
    """Schema for getting default prompts."""

    # Council content processing
    council_materials_system: str
    council_materials_user: str
    council_minutes_system: str
    council_minutes_user: str
    # Email generation
    email_system: str
    email_user: str
    # Infographic generation - Notebook
    infographic_system: str
    infographic_user: str
    # Infographic generation - Council
    council_infographic_system: str
    council_infographic_user: str
    # Document formatting
    format_system: str
    format_user: str
    # Minutes formatting
    minute_format_system: str
    minute_format_user: str
    # Document summary
    summary_system: str
    summary_user: str
    # Minutes summary
    minute_summary_system: str
    minute_summary_user: str
    # Document checker
    document_check_system: str
    document_check_user: str
    # Slide generation
    slide_generation_system: str
    slide_generation_user: str
    # Slide refinement
    slide_refinement_system: str
    slide_refinement_user: str


class LLMConnectionTestRequest(BaseModel):
    """Request schema for connection test."""

    provider: str = Field("ollama", description="Provider to test")
    api_base_url: str = Field(..., description="API base URL to test")
    api_key: Optional[str] = Field(None, description="API key (if required)")
    model: str = Field(..., description="Model name to test")


class LLMConnectionTestResponse(BaseModel):
    """Response schema for connection test."""

    success: bool
    message: str
    response_time_ms: Optional[int] = None
    model_info: Optional[Dict[str, Any]] = None
    error_detail: Optional[str] = None


class ModelInfo(BaseModel):
    """Information about an available model."""

    name: str
    size: Optional[str] = None
    family: Optional[str] = None
    modified_at: Optional[str] = None


class ModelsListResponse(BaseModel):
    """Response schema for available models list."""

    models: List[ModelInfo]
    provider: str
