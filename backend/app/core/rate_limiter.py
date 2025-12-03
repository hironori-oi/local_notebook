"""
Rate limiting middleware for FastAPI.

This module provides a simple in-memory rate limiter with the following features:
- Per-IP rate limiting
- Configurable limits for different endpoint groups
- Automatic cleanup of expired entries
"""

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Callable, Dict, Optional

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RateLimitEntry:
    """Tracks rate limit state for a single client."""

    count: int = 0
    window_start: float = field(default_factory=time.time)


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    Attributes:
        max_requests: Maximum number of requests allowed per window
        window_seconds: Window size in seconds
        cleanup_interval: How often to clean up expired entries (in requests)
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        cleanup_interval: int = 100,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.cleanup_interval = cleanup_interval
        self._entries: Dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._lock = Lock()
        self._request_count = 0

    def is_allowed(self, client_id: str) -> tuple[bool, int, int]:
        """
        Check if a request from the given client is allowed.

        Args:
            client_id: Unique identifier for the client (usually IP address)

        Returns:
            Tuple of (is_allowed, remaining_requests, reset_time_seconds)
        """
        with self._lock:
            self._request_count += 1

            # Periodic cleanup
            if self._request_count % self.cleanup_interval == 0:
                self._cleanup_expired()

            now = time.time()
            entry = self._entries[client_id]

            # Check if window has expired
            window_elapsed = now - entry.window_start
            if window_elapsed >= self.window_seconds:
                # Reset window
                entry.window_start = now
                entry.count = 1
                remaining = self.max_requests - 1
                reset_time = self.window_seconds
                return True, remaining, reset_time

            # Check if within limit
            if entry.count < self.max_requests:
                entry.count += 1
                remaining = self.max_requests - entry.count
                reset_time = int(self.window_seconds - window_elapsed)
                return True, remaining, reset_time

            # Rate limit exceeded
            remaining = 0
            reset_time = int(self.window_seconds - window_elapsed)
            return False, remaining, reset_time

    def _cleanup_expired(self) -> None:
        """Remove expired entries to prevent memory leaks."""
        now = time.time()
        expired = [
            client_id
            for client_id, entry in self._entries.items()
            if now - entry.window_start >= self.window_seconds * 2
        ]
        for client_id in expired:
            del self._entries[client_id]
        if expired:
            logger.debug(f"Cleaned up {len(expired)} expired rate limit entries")

    def reset(self, client_id: str) -> None:
        """Reset rate limit for a specific client."""
        with self._lock:
            if client_id in self._entries:
                del self._entries[client_id]


# Global rate limiters
auth_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_AUTH_REQUESTS,
    window_seconds=settings.RATE_LIMIT_AUTH_WINDOW,
)

api_limiter = RateLimiter(
    max_requests=settings.RATE_LIMIT_API_REQUESTS,
    window_seconds=settings.RATE_LIMIT_API_WINDOW,
)


def get_client_ip(request: Request) -> str:
    """
    Extract client IP from request, considering proxy headers.

    Args:
        request: FastAPI request object

    Returns:
        Client IP address
    """
    # Check for forwarded header (when behind proxy/load balancer)
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first IP in the chain
        return forwarded.split(",")[0].strip()

    # Check for real IP header
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()

    # Fall back to direct client IP
    if request.client:
        return request.client.host

    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware for rate limiting.

    Applies different rate limits based on the request path:
    - Auth endpoints (/api/v1/auth/*): Stricter limits to prevent brute force
    - Other API endpoints: General rate limits
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        client_ip = get_client_ip(request)

        # Skip rate limiting for health checks
        if "/health" in path:
            return await call_next(request)

        # Choose rate limiter based on path
        if "/auth/" in path:
            limiter = auth_limiter
            limit_type = "auth"
        else:
            limiter = api_limiter
            limit_type = "api"

        is_allowed, remaining, reset_time = limiter.is_allowed(client_ip)

        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for {client_ip} on {path} ({limit_type})"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"リクエストが多すぎます。{reset_time}秒後に再試行してください。",
                headers={
                    "Retry-After": str(reset_time),
                    "X-RateLimit-Limit": str(limiter.max_requests),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time),
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(limiter.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        return response


def rate_limit(
    limiter: Optional[RateLimiter] = None,
    max_requests: Optional[int] = None,
    window_seconds: Optional[int] = None,
) -> Callable:
    """
    Decorator for applying rate limits to specific endpoints.

    Can be used with a pre-configured limiter or with custom limits.

    Example:
        @router.post("/login")
        @rate_limit(max_requests=5, window_seconds=60)
        async def login(request: Request):
            ...
    """
    _limiter = limiter
    if _limiter is None and max_requests and window_seconds:
        _limiter = RateLimiter(max_requests, window_seconds)

    def decorator(func: Callable) -> Callable:
        async def wrapper(request: Request, *args, **kwargs):
            if _limiter:
                client_ip = get_client_ip(request)
                is_allowed, remaining, reset_time = _limiter.is_allowed(client_ip)

                if not is_allowed:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"リクエストが多すぎます。{reset_time}秒後に再試行してください。",
                        headers={"Retry-After": str(reset_time)},
                    )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator
