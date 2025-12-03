"""
Configuration for Janus-Pro-7B Image Generation Server
"""
import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Model settings
    MODEL_NAME: str = "deepseek-ai/Janus-Pro-7B"
    DEVICE: str = "cuda"
    TORCH_DTYPE: str = "bfloat16"  # bfloat16 or float16

    # Generation defaults
    DEFAULT_WIDTH: int = 384
    DEFAULT_HEIGHT: int = 384
    DEFAULT_CFG_WEIGHT: float = 5.0
    DEFAULT_TEMPERATURE: float = 1.0
    DEFAULT_TOP_P: float = 1.0

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 9000

    # Concurrency
    MAX_CONCURRENT_REQUESTS: int = 1  # Image generation is memory-intensive

    class Config:
        env_file = ".env"


settings = Settings()
