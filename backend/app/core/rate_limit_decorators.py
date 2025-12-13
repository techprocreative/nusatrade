"""Endpoint-specific rate limiting decorators."""

import inspect
from functools import wraps
from typing import Callable

from fastapi import Request, HTTPException, status
from app.core.rate_limiter import get_rate_limiter


def rate_limit(
    requests_per_minute: int = 60,
    requests_per_hour: int | None = None,
    key_func: Callable[[Request], str] | None = None
):
    """
    Decorator to apply rate limiting to specific endpoints.
    
    Args:
        requests_per_minute: Maximum requests per minute
        requests_per_hour: Optional maximum requests per hour
        key_func: Optional function to generate rate limit key from request
                 Default uses client IP
    
    Usage:
        @router.post("/sensitive-endpoint")
        @rate_limit(requests_per_minute=5, requests_per_hour=50)
        async def sensitive_operation(request: Request):
            pass
    """
    def decorator(func: Callable):
        # Check if function is async
        is_async = inspect.iscoroutinefunction(func)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break
            if not request and "request" in kwargs:
                request = kwargs["request"]

            if not request:
                # No request object, skip rate limiting
                if is_async:
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

            # Generate rate limit key
            if key_func:
                key = key_func(request)
            else:
                client_ip = request.client.host if request.client else "unknown"
                key = f"{request.url.path}:{client_ip}"

            rate_limiter = get_rate_limiter()

            # Check per-minute limit
            allowed, remaining = rate_limiter.is_allowed(
                f"rpm:{key}", requests_per_minute, 60
            )

            if not allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=f"Rate limit exceeded. Maximum {requests_per_minute} requests per minute.",
                    headers={"Retry-After": "60"}
                )

            # Check per-hour limit if specified
            if requests_per_hour:
                allowed_hour, remaining_hour = rate_limiter.is_allowed(
                    f"rph:{key}", requests_per_hour, 3600
                )

                if not allowed_hour:
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail=f"Hourly rate limit exceeded. Maximum {requests_per_hour} requests per hour.",
                        headers={"Retry-After": "3600"}
                    )

            # Call the original function (check if async or sync)
            if is_async:
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)

        # FastAPI can handle async wrappers for both sync and async endpoints
        return async_wrapper
    return decorator


# Predefined rate limiters for common scenarios
def rate_limit_auth(func: Callable):
    """Rate limit for authentication endpoints (stricter)."""
    return rate_limit(requests_per_minute=5, requests_per_hour=50)(func)


def rate_limit_trading(func: Callable):
    """Rate limit for trading endpoints (moderate)."""
    return rate_limit(requests_per_minute=30, requests_per_hour=500)(func)


def rate_limit_data(func: Callable):
    """Rate limit for data/query endpoints (lenient)."""
    return rate_limit(requests_per_minute=60, requests_per_hour=1000)(func)


def rate_limit_ml(func: Callable):
    """Rate limit for ML/AI endpoints (resource intensive)."""
    return rate_limit(requests_per_minute=10, requests_per_hour=100)(func)
