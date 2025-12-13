"""Rate limiting with Redis and in-memory fallback."""

import time
from typing import Optional, Tuple
import redis

from app.config import get_settings
from app.core.logging import get_logger


settings = get_settings()
logger = get_logger(__name__)


class RedisRateLimiter:
    """Redis-based rate limiter for production."""

    def __init__(self, redis_url: str):
        try:
            self.redis = redis.from_url(redis_url, decode_responses=True)
            self.redis.ping()
            self.available = True
            logger.info("Redis rate limiter initialized")
        except Exception as e:
            logger.warning(f"Redis not available: {e}. Falling back to in-memory limiter")
            self.available = False
            self._memory_store = {}

    def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> Tuple[bool, int]:
        """
        Check if request is allowed within rate limit.
        
        Returns:
            (allowed, remaining_requests)
        """
        if self.available:
            return self._redis_check(key, limit, window_seconds)
        else:
            return self._memory_check(key, limit, window_seconds)

    def _redis_check(self, key: str, limit: int, window_seconds: int) -> Tuple[bool, int]:
        """Check rate limit using Redis."""
        try:
            pipe = self.redis.pipeline()
            now = time.time()
            window_start = now - window_seconds

            # Use sorted set with timestamp as score
            pipe.zremrangebyscore(key, 0, window_start)  # Remove old entries
            pipe.zadd(key, {str(now): now})  # Add current request
            pipe.zcard(key)  # Count requests in window
            pipe.expire(key, window_seconds)  # Set TTL

            results = pipe.execute()
            count = results[2]  # zcard result

            remaining = max(0, limit - count)
            return (count <= limit, remaining)

        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            # CRITICAL CHANGE: Fail-closed instead of fail-open
            # In production, it's safer to block requests than allow unlimited access
            # This prevents DDoS/abuse when Redis is down
            from app.config import get_settings
            settings = get_settings()

            if settings.is_production:
                logger.critical(f"PRODUCTION: Blocking request due to Redis failure (fail-closed)")
                return (False, 0)  # BLOCK the request
            else:
                logger.warning(f"DEVELOPMENT: Allowing request despite Redis failure (fail-open)")
                return (True, limit)  # Allow in development

    def _memory_check(self, key: str, limit: int, window_seconds: int) -> Tuple[bool, int]:
        """Check rate limit using in-memory storage (fallback)."""
        now = time.time()
        window_start = now - window_seconds

        # Clean old entries
        if key in self._memory_store:
            self._memory_store[key] = [
                ts for ts in self._memory_store[key]
                if ts > window_start
            ]
        else:
            self._memory_store[key] = []

        # Count requests in window
        count = len(self._memory_store[key])

        if count >= limit:
            return (False, 0)

        # Add new request
        self._memory_store[key].append(now)
        return (True, limit - count - 1)

    def reset(self, key: str):
        """Reset rate limit for a key."""
        if self.available:
            try:
                self.redis.delete(key)
            except Exception as e:
                logger.error(f"Failed to reset rate limit: {e}")
        else:
            self._memory_store.pop(key, None)


class InMemoryRateLimiter:
    """Simple in-memory rate limiter (legacy, for compatibility)."""

    def __init__(self):
        self._requests: dict = {}

    def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> Tuple[bool, int]:
        """Check if request is allowed."""
        now = time.time()
        window_start = now - window_seconds

        # Clean old entries
        if key in self._requests:
            self._requests[key] = [
                (ts, c) for ts, c in self._requests[key]
                if ts > window_start
            ]

        # Count requests in window
        current_count = sum(c for _, c in self._requests.get(key, []))

        if current_count >= limit:
            return (False, 0)

        # Add new request
        if key not in self._requests:
            self._requests[key] = []
        self._requests[key].append((now, 1))

        return (True, limit - current_count - 1)


# Global rate limiter instance
_rate_limiter: Optional[RedisRateLimiter] = None


def get_rate_limiter() -> RedisRateLimiter:
    """Get or create rate limiter instance."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RedisRateLimiter(settings.redis_url)
    return _rate_limiter
