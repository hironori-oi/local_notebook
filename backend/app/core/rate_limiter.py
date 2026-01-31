"""
Rate limiting middleware for FastAPI.

This module provides rate limiters with the following features:
- Per-IP rate limiting
- Configurable limits for different endpoint groups
- In-memory backend for local development
- Redis backend for distributed deployments (cloud)
"""

import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from threading import Lock
from typing import Callable, Dict, Optional

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class RateLimitEntry:
    """Tracks rate limit state for a single client."""

    count: int = 0
    window_start: float = field(default_factory=time.time)


class BaseRateLimiter(ABC):
    """Abstract base class for rate limiters."""

    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    @abstractmethod
    def is_allowed(self, client_id: str) -> tuple[bool, int, int]:
        """
        Check if a request from the given client is allowed.

        Args:
            client_id: Unique identifier for the client (usually IP address)

        Returns:
            Tuple of (is_allowed, remaining_requests, reset_time_seconds)
        """
        pass

    @abstractmethod
    def reset(self, client_id: str) -> None:
        """Reset rate limit for a specific client."""
        pass


class InMemoryRateLimiter(BaseRateLimiter):
    """
    In-memory rate limiter using sliding window algorithm.

    Suitable for single-instance deployments or development.
    Note: State is not shared across instances in distributed deployments.

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
        super().__init__(max_requests, window_seconds)
        self.cleanup_interval = cleanup_interval
        self._entries: Dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._lock = Lock()
        self._request_count = 0

    def is_allowed(self, client_id: str) -> tuple[bool, int, int]:
        """Check if a request from the given client is allowed."""
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


class RedisRateLimiter(BaseRateLimiter):
    """
    Redis-backed rate limiter using sliding window algorithm.

    Suitable for distributed deployments where state must be shared
    across multiple instances.

    Attributes:
        max_requests: Maximum number of requests allowed per window
        window_seconds: Window size in seconds
    """

    def __init__(
        self,
        max_requests: int,
        window_seconds: int,
        redis_url: Optional[str] = None,
    ):
        super().__init__(max_requests, window_seconds)
        self._redis_url = redis_url or settings.REDIS_URL
        self._redis = None

    def _get_redis(self):
        """Lazy initialization of Redis client."""
        if self._redis is None:
            import redis

            self._redis = redis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    def is_allowed(self, client_id: str) -> tuple[bool, int, int]:
        """Check if a request from the given client is allowed."""
        try:
            redis_client = self._get_redis()
            key = f"rate_limit:{client_id}"
            now = time.time()
            window_start = now - self.window_seconds

            # Use pipeline for atomic operations
            pipe = redis_client.pipeline()

            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)

            # Add current request timestamp
            pipe.zadd(key, {str(now): now})

            # Count requests in the current window
            pipe.zcard(key)

            # Set expiry on the key
            pipe.expire(key, self.window_seconds + 1)

            results = pipe.execute()
            count = results[2]

            remaining = max(0, self.max_requests - count)
            reset_time = self.window_seconds

            if count <= self.max_requests:
                return True, remaining, reset_time
            else:
                return False, 0, reset_time

        except Exception as e:
            # If Redis fails, allow the request (fail-open)
            logger.warning(f"Redis rate limiter error, allowing request: {e}")
            return True, self.max_requests - 1, self.window_seconds

    def reset(self, client_id: str) -> None:
        """Reset rate limit for a specific client."""
        try:
            redis_client = self._get_redis()
            key = f"rate_limit:{client_id}"
            redis_client.delete(key)
        except Exception as e:
            logger.warning(f"Redis rate limiter reset error: {e}")


# Factory function to create rate limiter
def create_rate_limiter(
    max_requests: int,
    window_seconds: int,
    use_redis: Optional[bool] = None,
) -> BaseRateLimiter:
    """
    Create a rate limiter based on deployment mode.

    Args:
        max_requests: Maximum number of requests allowed per window
        window_seconds: Window size in seconds
        use_redis: Override to force Redis (True) or in-memory (False)

    Returns:
        Rate limiter instance
    """
    if use_redis is None:
        # Auto-detect based on deployment mode
        use_redis = settings.DEPLOYMENT_MODE == "cloud"

    if use_redis:
        logger.info(
            f"Creating Redis rate limiter: {max_requests} requests / {window_seconds}s"
        )
        return RedisRateLimiter(max_requests, window_seconds)
    else:
        logger.info(
            f"Creating in-memory rate limiter: {max_requests} requests / {window_seconds}s"
        )
        return InMemoryRateLimiter(max_requests, window_seconds)


# Global rate limiters (created lazily based on deployment mode)
_auth_limiter: Optional[BaseRateLimiter] = None
_api_limiter: Optional[BaseRateLimiter] = None


def get_auth_limiter() -> BaseRateLimiter:
    """Get the auth rate limiter (singleton)."""
    global _auth_limiter
    if _auth_limiter is None:
        _auth_limiter = create_rate_limiter(
            max_requests=settings.RATE_LIMIT_AUTH_REQUESTS,
            window_seconds=settings.RATE_LIMIT_AUTH_WINDOW,
        )
    return _auth_limiter


def get_api_limiter() -> BaseRateLimiter:
    """Get the API rate limiter (singleton)."""
    global _api_limiter
    if _api_limiter is None:
        _api_limiter = create_rate_limiter(
            max_requests=settings.RATE_LIMIT_API_REQUESTS,
            window_seconds=settings.RATE_LIMIT_API_WINDOW,
        )
    return _api_limiter


# Backwards compatibility: expose as module-level variables
# These are lazy-initialized when first accessed
class _LazyLimiter:
    def __init__(self, getter):
        self._getter = getter
        self._instance = None

    def __getattr__(self, name):
        if self._instance is None:
            self._instance = self._getter()
        return getattr(self._instance, name)


auth_limiter = _LazyLimiter(get_auth_limiter)
api_limiter = _LazyLimiter(get_api_limiter)


def get_client_ip(request: Request) -> str:
    """
    Extract client IP from request, considering proxy headers securely.

    Security considerations:
    - X-Forwarded-For can be spoofed by clients, so we only trust it when
      TRUST_PROXY_HEADERS is enabled (i.e., when behind a trusted reverse proxy)
    - X-Real-IP is typically set by the reverse proxy and is more reliable
    - When not behind a proxy, we use the direct client IP

    Args:
        request: FastAPI request object

    Returns:
        Client IP address
    """
    # If proxy headers are trusted (when behind a known reverse proxy)
    if settings.TRUST_PROXY_HEADERS:
        # Prefer X-Real-IP (typically set by Nginx/reverse proxy to true client IP)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        # Fall back to X-Forwarded-For
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the leftmost IP (original client)
            # Note: This is safe when TRUST_PROXY_HEADERS is only enabled
            # behind a trusted proxy that properly sets this header
            ips = [ip.strip() for ip in forwarded.split(",")]
            if ips:
                return ips[0]

    # Direct connection or untrusted proxy - use actual client IP
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
        method = request.method
        client_ip = get_client_ip(request)

        # Skip rate limiting for CORS preflight requests (OPTIONS)
        if method == "OPTIONS":
            return await call_next(request)

        # Skip rate limiting for health checks
        if "/health" in path:
            return await call_next(request)

        # Choose rate limiter based on path
        if "/auth/" in path:
            limiter = get_auth_limiter()
            limit_type = "auth"
        else:
            limiter = get_api_limiter()
            limit_type = "api"

        is_allowed, remaining, reset_time = limiter.is_allowed(client_ip)

        if not is_allowed:
            logger.warning(
                f"Rate limit exceeded for {client_ip} on {path} ({limit_type})"
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": f"リクエストが多すぎます。{reset_time}秒後に再試行してください。"
                },
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
    limiter: Optional[BaseRateLimiter] = None,
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
        _limiter = create_rate_limiter(max_requests, window_seconds)

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


# Backwards compatibility alias
RateLimiter = InMemoryRateLimiter
