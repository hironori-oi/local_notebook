import secrets
import warnings
from typing import Literal, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


# Insecure default values that should never be used in production
INSECURE_JWT_SECRETS = {
    "CHANGE_ME_TO_RANDOM_SECRET_KEY",
    "secret",
    "your-secret-key",
    "changeme",
    "password",
    "",
}


class Settings(BaseSettings):
    PROJECT_NAME: str = "Internal AI Notebook"
    API_V1_PREFIX: str = "/api/v1"

    # ===========================================
    # Environment Mode
    # ===========================================
    ENV: Literal["development", "production"] = "development"

    # ===========================================
    # Database
    # ===========================================
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/notebookdb"

    # ===========================================
    # LLM Provider Configuration
    # ===========================================
    # Provider: "ollama" or "vllm"
    LLM_PROVIDER: Literal["ollama", "vllm"] = "ollama"

    # LLM API (OpenAI-compatible)
    LLM_API_BASE: str = "http://localhost:11434/v1"
    LLM_MODEL: str = "gpt-oss-120b"
    LLM_TIMEOUT: int = 120  # seconds
    LLM_MAX_TOKENS: int = 4096  # Maximum tokens to generate in response

    # ===========================================
    # Generation LLM Configuration
    # (For infographic/slide generation - uses LLM_MODEL if not set)
    # ===========================================
    GENERATION_LLM_MODEL: Optional[str] = None
    GENERATION_LLM_MAX_TOKENS: int = 8192

    # ===========================================
    # Generated Files Storage
    # ===========================================
    GENERATED_FILES_DIR: str = "data/generated"

    # ===========================================
    # Embedding Configuration
    # ===========================================
    EMBEDDING_API_BASE: str = "http://localhost:11434/v1"
    EMBEDDING_MODEL: str = "embeddinggemma:300m"
    # embeddinggemma:300m outputs 768 dimensions, PLaMo-Embedding-1B outputs 2048
    EMBEDDING_DIM: int = 768
    EMBEDDING_TIMEOUT: int = 60  # seconds

    # ===========================================
    # Authentication
    # ===========================================
    JWT_SECRET_KEY: str = "CHANGE_ME_TO_RANDOM_SECRET_KEY"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours

    # ===========================================
    # Rate Limiting
    # ===========================================
    RATE_LIMIT_AUTH_REQUESTS: int = 5  # Max login attempts
    RATE_LIMIT_AUTH_WINDOW: int = 900  # 15 minutes in seconds
    RATE_LIMIT_API_REQUESTS: int = 100  # Max API requests
    RATE_LIMIT_API_WINDOW: int = 60  # 1 minute in seconds

    # ===========================================
    # Proxy Settings (for IP detection)
    # ===========================================
    # Comma-separated list of trusted proxy IPs/networks
    # When behind a reverse proxy, set this to the proxy's IP
    # Example: "127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"
    TRUSTED_PROXIES: str = ""
    # Whether to trust X-Forwarded-For header (only enable behind trusted proxy)
    TRUST_PROXY_HEADERS: bool = False

    # ===========================================
    # Application Settings
    # ===========================================
    UPLOAD_DIR: str = "data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # ===========================================
    # Chat History Settings
    # ===========================================
    # Maximum number of previous messages to include in LLM context
    MAX_CHAT_HISTORY_MESSAGES: int = 20
    # Maximum total characters for chat history (to prevent token overflow)
    MAX_CHAT_HISTORY_CHARS: int = 8000

    # ===========================================
    # Content Processing Settings (for email generation)
    # ===========================================
    # Maximum input text length for formatting (characters)
    CONTENT_FORMAT_MAX_LENGTH: int = 20000
    # Maximum input text length for summarization (characters)
    CONTENT_SUMMARY_MAX_LENGTH: int = 30000
    # Maximum characters for fallback content in email generation
    # Note: Set high enough to include all speakers in meeting minutes
    CONTENT_FALLBACK_MAX_LENGTH: int = 15000

    # ===========================================
    # YouTube Transcription Settings
    # ===========================================
    # External Whisper server URL (runs on separate machine with GPU)
    # Example: http://192.168.1.100:8001
    WHISPER_SERVER_URL: Optional[str] = None
    TEMP_AUDIO_DIR: str = "data/audio_temp"
    MAX_VIDEO_DURATION_MINUTES: int = 60

    # ===========================================
    # Redis & Celery Configuration
    # ===========================================
    REDIS_URL: str = "redis://localhost:6379/0"
    # If not set, REDIS_URL is used for both broker and backend
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None

    @property
    def celery_broker_url(self) -> str:
        """Get Celery broker URL (defaults to REDIS_URL)."""
        return self.CELERY_BROKER_URL or self.REDIS_URL

    @property
    def celery_result_backend(self) -> str:
        """Get Celery result backend URL (defaults to REDIS_URL)."""
        return self.CELERY_RESULT_BACKEND or self.REDIS_URL

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret(cls, v: str) -> str:
        """Validate JWT secret key for security."""
        if v in INSECURE_JWT_SECRETS:
            # In development, generate a random key with warning
            import os
            if os.getenv("ENV", "development") == "production":
                raise ValueError(
                    "JWT_SECRET_KEY must be set to a secure random value in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
            # Development mode: generate temporary key with warning
            warnings.warn(
                "Using auto-generated JWT_SECRET_KEY. Set JWT_SECRET_KEY in .env for production.",
                UserWarning,
            )
            return secrets.token_hex(32)

        if len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 characters long for security. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return v

    class Config:
        env_file = ".env"


settings = Settings()
