"""Monitoring and error tracking with Sentry."""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration

from app.config import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)
settings = get_settings()


def init_sentry():
    """Initialize Sentry error tracking."""
    sentry_dsn = getattr(settings, "sentry_dsn", None)
    
    if not sentry_dsn or settings.environment == "development":
        logger.info("Sentry monitoring disabled (no DSN or development mode)")
        return
    
    try:
        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=settings.environment,
            release=f"{settings.app_name}@{getattr(settings, 'app_version', '1.0.0')}",
            
            # Performance monitoring
            traces_sample_rate=getattr(settings, "sentry_traces_sample_rate", 0.1),
            profiles_sample_rate=getattr(settings, "sentry_profiles_sample_rate", 0.1),
            
            # Integrations
            integrations=[
                FastApiIntegration(transaction_style="url"),
                SqlalchemyIntegration(),
                RedisIntegration(),
                HttpxIntegration(),
            ],
            
            # Filter out sensitive data
            before_send=before_send_filter,
            
            # Additional options
            attach_stacktrace=True,
            send_default_pii=False,  # Don't send PII
            max_breadcrumbs=50,
        )
        
        logger.info(f"Sentry monitoring initialized (environment: {settings.environment})")
        
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def before_send_filter(event, hint):
    """
    Filter sensitive data before sending to Sentry.
    
    This prevents accidentally sending passwords, API keys, tokens, etc.
    """
    # Remove sensitive query parameters
    if "request" in event:
        request = event["request"]
        
        # Filter URL query params
        if "query_string" in request:
            query_string = request["query_string"]
            if any(key in query_string.lower() for key in ["password", "token", "secret", "key", "api_key"]):
                request["query_string"] = "[FILTERED]"
        
        # Filter headers
        if "headers" in request:
            sensitive_headers = {"authorization", "cookie", "x-api-key", "x-auth-token"}
            for header in sensitive_headers:
                if header in request["headers"]:
                    request["headers"][header] = "[FILTERED]"
        
        # Filter body
        if "data" in request:
            if isinstance(request["data"], dict):
                sensitive_keys = {"password", "token", "secret", "api_key", "private_key", "totp_secret"}
                for key in sensitive_keys:
                    if key in request["data"]:
                        request["data"][key] = "[FILTERED]"
    
    # Filter exception context
    if "exception" in event:
        for exception in event["exception"].get("values", []):
            if "stacktrace" in exception:
                for frame in exception["stacktrace"].get("frames", []):
                    if "vars" in frame:
                        sensitive_vars = {"password", "token", "secret", "api_key", "private_key"}
                        for var in sensitive_vars:
                            if var in frame["vars"]:
                                frame["vars"][var] = "[FILTERED]"
    
    return event


def capture_exception(exception: Exception, context: dict | None = None):
    """
    Manually capture an exception with optional context.
    
    Args:
        exception: The exception to capture
        context: Additional context (tags, user info, etc.)
    """
    if context:
        with sentry_sdk.push_scope() as scope:
            # Add tags
            if "tags" in context:
                for key, value in context["tags"].items():
                    scope.set_tag(key, value)
            
            # Add user context
            if "user" in context:
                scope.set_user(context["user"])
            
            # Add extra data
            if "extra" in context:
                for key, value in context["extra"].items():
                    scope.set_extra(key, value)
            
            sentry_sdk.capture_exception(exception)
    else:
        sentry_sdk.capture_exception(exception)


def capture_message(message: str, level: str = "info", context: dict | None = None):
    """
    Capture a message (not an exception).
    
    Args:
        message: The message to capture
        level: Message level (debug, info, warning, error, fatal)
        context: Additional context
    """
    if context:
        with sentry_sdk.push_scope() as scope:
            if "tags" in context:
                for key, value in context["tags"].items():
                    scope.set_tag(key, value)
            
            if "user" in context:
                scope.set_user(context["user"])
            
            if "extra" in context:
                for key, value in context["extra"].items():
                    scope.set_extra(key, value)
            
            sentry_sdk.capture_message(message, level=level)
    else:
        sentry_sdk.capture_message(message, level=level)


def add_breadcrumb(message: str, category: str = "default", level: str = "info", data: dict | None = None):
    """
    Add a breadcrumb for context in error reports.
    
    Args:
        message: Breadcrumb message
        category: Category (e.g., "auth", "trading", "ml")
        level: Log level
        data: Additional data
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {}
    )


def set_user_context(user_id: str, email: str | None = None, username: str | None = None):
    """Set user context for error tracking."""
    sentry_sdk.set_user({
        "id": user_id,
        "email": email,
        "username": username,
    })


def clear_user_context():
    """Clear user context (e.g., on logout)."""
    sentry_sdk.set_user(None)


def start_transaction(name: str, op: str = "http.server"):
    """
    Start a performance transaction.
    
    Args:
        name: Transaction name (e.g., "/api/v1/trading/orders")
        op: Operation type (http.server, db.query, etc.)
    
    Returns:
        Transaction object (use as context manager)
    """
    return sentry_sdk.start_transaction(name=name, op=op)


def start_span(operation: str, description: str | None = None):
    """
    Start a span for performance monitoring.
    
    Args:
        operation: Span operation (e.g., "db.query", "http.client")
        description: Span description
    
    Returns:
        Span object (use as context manager)
    """
    return sentry_sdk.start_span(op=operation, description=description)
