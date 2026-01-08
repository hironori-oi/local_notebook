"""
Custom exceptions and global exception handlers.

This module provides a consistent error handling system with:
- Typed exception classes for different error categories
- Error codes for programmatic error handling
- User-friendly Japanese error messages
"""

import logging
from enum import Enum

from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """Error codes for programmatic error handling."""

    # General errors
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"

    # Authentication/Authorization errors
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_TOKEN = "INVALID_TOKEN"

    # Resource errors
    NOT_FOUND = "NOT_FOUND"
    ALREADY_EXISTS = "ALREADY_EXISTS"

    # Request errors
    BAD_REQUEST = "BAD_REQUEST"
    INVALID_INPUT = "INVALID_INPUT"

    # Service errors
    LLM_CONNECTION_ERROR = "LLM_CONNECTION_ERROR"
    EMBEDDING_ERROR = "EMBEDDING_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"

    # Rate limiting
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: str = None,
        error_code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
    ):
        self.message = message
        self.status_code = status_code
        self.detail = detail or message
        self.error_code = error_code
        super().__init__(self.message)


class NotFoundError(AppException):
    """Resource not found."""

    def __init__(self, message: str = "リソースが見つかりません"):
        super().__init__(
            message, status.HTTP_404_NOT_FOUND, error_code=ErrorCode.NOT_FOUND
        )


class UnauthorizedError(AppException):
    """Authentication required."""

    def __init__(
        self,
        message: str = "認証が必要です",
        error_code: ErrorCode = ErrorCode.UNAUTHORIZED,
    ):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, error_code=error_code)


class ForbiddenError(AppException):
    """Access denied."""

    def __init__(self, message: str = "アクセスが拒否されました"):
        super().__init__(
            message, status.HTTP_403_FORBIDDEN, error_code=ErrorCode.FORBIDDEN
        )


class BadRequestError(AppException):
    """Invalid request."""

    def __init__(
        self,
        message: str = "無効なリクエストです",
        error_code: ErrorCode = ErrorCode.BAD_REQUEST,
    ):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, error_code=error_code)


class LLMConnectionError(AppException):
    """LLM server connection error."""

    def __init__(self, message: str = "LLMサーバーへの接続に失敗しました"):
        super().__init__(
            message,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.LLM_CONNECTION_ERROR,
        )


class EmbeddingError(AppException):
    """Embedding generation error."""

    def __init__(self, message: str = "埋め込みベクトルの生成に失敗しました"):
        super().__init__(
            message,
            status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code=ErrorCode.EMBEDDING_ERROR,
        )


class RateLimitError(AppException):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str = "リクエスト制限を超過しました。しばらく経ってから再試行してください。",
    ):
        super().__init__(
            message,
            status.HTTP_429_TOO_MANY_REQUESTS,
            error_code=ErrorCode.RATE_LIMIT_EXCEEDED,
        )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle custom application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "message": exc.message,
            "error_code": exc.error_code.value,
        },
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
            "message": "入力内容に問題があります",
            "error_code": ErrorCode.VALIDATION_ERROR.value,
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
            "message": "サーバーエラーが発生しました。しばらく経ってから再試行してください。",
            "error_code": ErrorCode.UNKNOWN_ERROR.value,
        },
    )
