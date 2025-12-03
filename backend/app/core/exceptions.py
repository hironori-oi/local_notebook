"""
Custom exceptions and global exception handlers.
"""
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

logger = logging.getLogger(__name__)


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = None,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail or message
        super().__init__(self.message)


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(self, message: str = "リソースが見つかりません"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class UnauthorizedError(AppException):
    """Authentication required."""

    def __init__(self, message: str = "認証が必要です"):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class ForbiddenError(AppException):
    """Access denied."""

    def __init__(self, message: str = "アクセスが拒否されました"):
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class BadRequestError(AppException):
    """Invalid request."""

    def __init__(self, message: str = "無効なリクエストです"):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)


class LLMConnectionError(AppException):
    """LLM server connection error."""

    def __init__(self, message: str = "LLMサーバーへの接続に失敗しました"):
        super().__init__(message, status.HTTP_503_SERVICE_UNAVAILABLE)


class EmbeddingError(AppException):
    """Embedding generation error."""

    def __init__(self, message: str = "埋め込みベクトルの生成に失敗しました"):
        super().__init__(message, status.HTTP_503_SERVICE_UNAVAILABLE)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "message": exc.message},
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle validation errors with user-friendly messages."""
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        msg = error["msg"]
        errors.append(f"{field}: {msg}")

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "入力内容に問題があります",
            "errors": errors,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "サーバーエラーが発生しました。しばらく経ってから再試行してください。",
        },
    )
