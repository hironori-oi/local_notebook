"""
LLM Settings model for storing user-specific LLM configurations.
"""
import uuid
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from app.db.base import Base


# Default feature settings
DEFAULT_FEATURE_SETTINGS = {
    "chat": {
        "model": None,  # None means use default_model
        "temperature": 0.1,
        "max_tokens": 4096,
    },
    "format": {
        "model": None,
        "temperature": 0.1,
        "max_tokens": 8192,
    },
    "summary": {
        "model": None,
        "temperature": 0.2,
        "max_tokens": 8192,
    },
    "email": {
        "model": None,
        "temperature": 0.3,
        "max_tokens": 8192,
    },
    "infographic": {
        "model": None,
        "temperature": 0.3,
        "max_tokens": 8192,
    },
}

# Default prompt settings (None means use hardcoded defaults in code)
DEFAULT_PROMPT_SETTINGS = {
    # Council content processing (審議会資料処理)
    "council_materials_system": None,
    "council_materials_user": None,
    "council_minutes_system": None,
    "council_minutes_user": None,
    # Email generation (メール生成)
    "email_system": None,
    "email_user": None,
    # Infographic generation - Notebook (インフォグラフィック - ノートブック)
    "infographic_system": None,
    "infographic_user": None,
    # Infographic generation - Council (インフォグラフィック - 審議会)
    "council_infographic_system": None,
    "council_infographic_user": None,
    # Document formatting (テキスト整形)
    "format_system": None,
    "format_user": None,
    # Minutes formatting (議事録整形)
    "minute_format_system": None,
    "minute_format_user": None,
    # Document summary (資料要約)
    "summary_system": None,
    "summary_user": None,
    # Minutes summary (議事録要約)
    "minute_summary_system": None,
    "minute_summary_user": None,
    # Document checker (校正チェック)
    "document_check_system": None,
    "document_check_user": None,
    # Slide generation (スライド生成)
    "slide_generation_system": None,
    "slide_generation_user": None,
    # Slide refinement (スライド修正)
    "slide_refinement_system": None,
    "slide_refinement_user": None,
}


class LLMSettings(Base):
    """
    Store LLM configuration settings per user.

    If user_id is NULL, this represents the system default settings.
    Each user can have at most one settings record.
    """
    __tablename__ = "llm_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # User association (NULL = system default)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        unique=True,
    )

    # Basic LLM settings
    provider = Column(String(50), nullable=False, default="ollama")
    api_base_url = Column(String(500), nullable=False, default="http://localhost:11434/v1")
    api_key_encrypted = Column(Text, nullable=True)  # Encrypted API key for OpenAI/Anthropic
    default_model = Column(String(200), nullable=False, default="gpt-oss-120b")

    # Embedding settings
    embedding_model = Column(String(200), nullable=False, default="embeddinggemma:300m")
    embedding_api_base = Column(String(500), nullable=False, default="http://localhost:11434/v1")
    embedding_dim = Column(Integer, nullable=False, default=768)

    # Feature-specific settings (JSONB)
    feature_settings = Column(
        JSONB,
        nullable=False,
        default=DEFAULT_FEATURE_SETTINGS,
    )

    # Prompt settings (JSONB) - stores custom prompts for various features
    prompt_settings = Column(
        JSONB,
        nullable=False,
        default=DEFAULT_PROMPT_SETTINGS,
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="llm_settings")

    def get_feature_setting(self, feature: str, key: str, default=None):
        """
        Get a specific feature setting value.

        Args:
            feature: Feature name (chat, format, summary, email, infographic)
            key: Setting key (model, temperature, max_tokens)
            default: Default value if not found

        Returns:
            The setting value or default
        """
        if not self.feature_settings:
            return default
        feature_config = self.feature_settings.get(feature, {})
        return feature_config.get(key, default)

    def get_model_for_feature(self, feature: str) -> str:
        """
        Get the model to use for a specific feature.
        Returns the feature-specific model if set, otherwise the default model.
        """
        feature_model = self.get_feature_setting(feature, "model")
        return feature_model if feature_model else self.default_model

    def get_temperature_for_feature(self, feature: str) -> float:
        """Get temperature setting for a feature."""
        defaults = {
            "chat": 0.1,
            "format": 0.1,
            "summary": 0.2,
            "email": 0.3,
            "infographic": 0.3,
        }
        return self.get_feature_setting(feature, "temperature", defaults.get(feature, 0.1))

    def get_max_tokens_for_feature(self, feature: str) -> int:
        """Get max_tokens setting for a feature."""
        defaults = {
            "chat": 4096,
            "format": 8192,
            "summary": 8192,
            "email": 8192,
            "infographic": 8192,
        }
        return self.get_feature_setting(feature, "max_tokens", defaults.get(feature, 4096))

    def get_prompt(self, prompt_key: str, default: str = None) -> str | None:
        """
        Get a custom prompt by key.

        Args:
            prompt_key: Prompt key (e.g., 'council_materials_system')
            default: Default value if not found or None

        Returns:
            The custom prompt or default
        """
        if not self.prompt_settings:
            return default
        value = self.prompt_settings.get(prompt_key)
        return value if value else default
