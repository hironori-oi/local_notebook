import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError

from app.core.config import settings
from app.core.exceptions import (
    AppException,
    app_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from app.core.rate_limiter import RateLimitMiddleware
from app.api.v1 import auth, health, notebooks, sources, chat, notes, infographic, slides, assets

# Configure logging
log_level = logging.DEBUG if settings.ENV == "development" else logging.INFO
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Suppress verbose logging from third-party libraries
# These libraries output excessive DEBUG logs that clutter the console
noisy_loggers = [
    "pdfminer",
    "pdfminer.psparser",
    "pdfminer.pdfparser",
    "pdfminer.pdfdocument",
    "pdfminer.pdfpage",
    "pdfminer.pdfinterp",
    "pdfminer.converter",
    "pdfminer.cmapdb",
    "pdfplumber",
    "httpx",
    "httpcore",
    "PIL",
    "multipart",
    "multipart.multipart",
    "python_multipart",
]
for logger_name in noisy_loggers:
    logging.getLogger(logger_name).setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="社内AIノート - NotebookLMライクなローカルLLM活用Webアプリ",
    version="0.1.0",
    docs_url="/api/docs" if settings.ENV == "development" else None,
    redoc_url="/api/redoc" if settings.ENV == "development" else None,
)

# Register exception handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Rate limiting middleware (must be added before CORS)
app.add_middleware(RateLimitMiddleware)

# CORS設定（社内ネットワーク向け）
# In production, set CORS_ORIGINS environment variable
cors_origins_env = os.getenv("CORS_ORIGINS", "")
if cors_origins_env:
    origins = [origin.strip() for origin in cors_origins_env.split(",")]
else:
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)

logger.info(f"Starting {settings.PROJECT_NAME} in {settings.ENV} mode")

# API v1 ルーター登録
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(health.router, prefix=settings.API_V1_PREFIX)
app.include_router(notebooks.router, prefix=settings.API_V1_PREFIX)
app.include_router(sources.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)
app.include_router(notes.router, prefix=settings.API_V1_PREFIX)
app.include_router(infographic.router, prefix=settings.API_V1_PREFIX)
app.include_router(slides.router, prefix=settings.API_V1_PREFIX)
app.include_router(assets.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def read_root():
    """Root endpoint - basic API status."""
    return {
        "message": "OK",
        "service": settings.PROJECT_NAME,
        "version": "0.1.0",
    }
