"""Middleware stack for the Forex AI platform."""

import time
from collections import defaultdict
from typing import Callable, Dict

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings
from app.core.logging import (
    generate_request_id,
    get_logger,
    set_request_id,
)


logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware to inject request ID into each request."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", generate_request_id())
        set_request_id(request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log request/response details."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.perf_counter()

        # Log request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "extra_data": {
                    "method": request.method,
                    "path": request.url.path,
                    "query": str(request.query_params),
                    "client_ip": request.client.host if request.client else None,
                }
            },
        )

        response = await call_next(request)

        # Calculate duration
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Log response
        logger.info(
            f"Request completed: {request.method} {request.url.path} - {response.status_code} ({duration_ms:.2f}ms)",
            extra={
                "extra_data": {
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                }
            },
        )

        response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory rate limiting middleware."""

    def __init__(self, app: FastAPI):
        super().__init__(app)
        settings = get_settings()
        self.max_requests = settings.rate_limit_requests
        self.window_seconds = settings.rate_limit_window_seconds
        self.requests: Dict[str, list] = defaultdict(list)

    def _get_client_key(self, request: Request) -> str:
        """Get unique client identifier."""
        # Use Authorization header if present, otherwise use IP
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return f"token:{auth_header[7:20]}"  # First 13 chars of token
        return f"ip:{request.client.host if request.client else 'unknown'}"

    def _cleanup_old_requests(self, key: str, current_time: float) -> None:
        """Remove requests outside the time window."""
        cutoff = current_time - self.window_seconds
        self.requests[key] = [t for t in self.requests[key] if t > cutoff]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip rate limiting in test mode
        import os
        if os.environ.get("TESTING") == "1":
            return await call_next(request)
        
        # Skip rate limiting for health check
        if request.url.path in ["/health", "/docs", "/openapi.json"]:
            return await call_next(request)

        client_key = self._get_client_key(request)
        current_time = time.time()

        # Cleanup old requests
        self._cleanup_old_requests(client_key, current_time)

        # Check rate limit
        if len(self.requests[client_key]) >= self.max_requests:
            logger.warning(
                f"Rate limit exceeded for {client_key}",
                extra={"extra_data": {"client_key": client_key}},
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Too many requests",
                    "retry_after": self.window_seconds,
                },
                headers={"Retry-After": str(self.window_seconds)},
            )

        # Record this request
        self.requests[client_key].append(current_time)

        # Add rate limit headers
        response = await call_next(request)
        remaining = self.max_requests - len(self.requests[client_key])
        response.headers["X-RateLimit-Limit"] = str(self.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(current_time + self.window_seconds))

        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """Global error handling middleware."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:
            logger.exception(
                f"Unhandled exception: {exc}",
                extra={
                    "extra_data": {
                        "method": request.method,
                        "path": request.url.path,
                        "error_type": type(exc).__name__,
                    }
                },
            )

            settings = get_settings()
            if settings.is_development:
                detail = str(exc)
            else:
                detail = "Internal server error"

            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": detail},
            )


def setup_middleware(app: FastAPI) -> None:
    """Setup all middleware in the correct order."""
    # Order matters: first added = outermost wrapper
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)
