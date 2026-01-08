import logging
import os

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import (admin, assets, auth, chat, council_agendas,
                        council_chat, council_infographics, council_meetings,
                        council_notes, council_search, councils,
                        document_checker, email, export, folders, health,
                        infographic, llm_settings, minutes, notebooks, notes,
                        processing, search, slide_generator, sources,
                        transcription)
from app.core.config import settings
from app.core.exceptions import (AppException, app_exception_handler,
                                 generic_exception_handler,
                                 validation_exception_handler)
from app.core.rate_limiter import RateLimitMiddleware

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
app.include_router(folders.router, prefix=settings.API_V1_PREFIX)
app.include_router(chat.router, prefix=settings.API_V1_PREFIX)
app.include_router(notes.router, prefix=settings.API_V1_PREFIX)
app.include_router(infographic.router, prefix=settings.API_V1_PREFIX)
app.include_router(email.router, prefix=settings.API_V1_PREFIX)
app.include_router(minutes.router, prefix=settings.API_V1_PREFIX)
app.include_router(assets.router, prefix=settings.API_V1_PREFIX)
app.include_router(llm_settings.router, prefix=settings.API_V1_PREFIX)
app.include_router(processing.router, prefix=settings.API_V1_PREFIX)
app.include_router(export.router, prefix=settings.API_V1_PREFIX)
app.include_router(search.router, prefix=settings.API_V1_PREFIX)
app.include_router(admin.router, prefix=settings.API_V1_PREFIX)

# Council management routers (審議会管理)
app.include_router(councils.router, prefix=settings.API_V1_PREFIX)
app.include_router(council_meetings.router, prefix=settings.API_V1_PREFIX)
app.include_router(council_agendas.router, prefix=settings.API_V1_PREFIX)
app.include_router(council_notes.router, prefix=settings.API_V1_PREFIX)
app.include_router(council_chat.router, prefix=settings.API_V1_PREFIX)
app.include_router(council_search.router, prefix=settings.API_V1_PREFIX)
app.include_router(council_infographics.router, prefix=settings.API_V1_PREFIX)

# Transcription router (YouTube文字起こし)
app.include_router(transcription.router, prefix=settings.API_V1_PREFIX)

# Document Checker router (ドキュメントチェッカー)
app.include_router(document_checker.router, prefix=settings.API_V1_PREFIX)

# Slide Generator router (スライド生成)
app.include_router(slide_generator.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def read_root():
    """Root endpoint - basic API status."""
    return {
        "message": "OK",
        "service": settings.PROJECT_NAME,
        "version": "0.1.0",
    }
