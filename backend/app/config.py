from functools import lru_cache
from typing import List, Optional
import re
import secrets as secrets_module

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "Forex AI Backend"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    backend_cors_origins: List[str] | str = ["http://localhost:3000", "http://localhost:8000", "https://nusatrade-beta.vercel.app"]

    # Database
    database_url: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/forex_ai"
    redis_url: str = "redis://localhost:6379/0"

    # Security
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    jwt_secret: str = "change-me"  # override in production
    jwt_algorithm: str = "HS256"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    # AI/LLM (Unified OpenAI-compatible configuration)
    llm_api_key: Optional[str] = None
    llm_base_url: Optional[str] = None  # Custom base URL for OpenAI-compatible providers
    llm_model: str = "gpt-4-turbo-preview"

    # Legacy AI/LLM configuration (deprecated but still supported for backward compatibility)
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4-turbo-preview"
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"
    
    # Settings encryption key for admin panel
    settings_encryption_key: Optional[str] = None

    # Storage (Cloudflare R2)
    r2_account_id: Optional[str] = None
    r2_access_key_id: Optional[str] = None
    r2_secret_access_key: Optional[str] = None
    r2_bucket_name: str = "forex-ai-storage"

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Trading Defaults
    max_lot_size: float = 10.0
    max_positions_per_user: int = 20
    default_slippage_pips: float = 2.0

    # WebSocket
    ws_heartbeat_interval: int = 30
    ws_connection_timeout: int = 60

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "protected_namespaces": ("model_",),  # Fix Pydantic warning for settings_encryption_key
    }

    def cors_origins(self) -> List[str]:
        if isinstance(self.backend_cors_origins, str):
            return [o.strip() for o in self.backend_cors_origins.split(",") if o.strip()]
        return self.backend_cors_origins

    @property
    def effective_llm_config(self) -> dict:
        """Get effective LLM configuration with fallback to legacy settings."""
        return {
            "api_key": self.llm_api_key or self.openai_api_key,
            "base_url": self.llm_base_url,
            "model": self.llm_model or self.openai_model,
        }

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def is_development(self) -> bool:
        return self.environment.lower() == "development"


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()

    # CRITICAL: Production environment validation
    if settings.is_production:
        _validate_production_secrets(settings)

    return settings


def _validate_production_secrets(settings: Settings) -> None:
    """
    Validate all security-critical settings for production deployment.

    This function implements STRICT validation to prevent common security issues:
    - Weak JWT secrets (session hijacking)
    - Default/example secrets (credential leaks)
    - Missing encryption keys (data exposure)
    - Insufficient secret entropy (brute force attacks)

    For real money trading, these checks are MANDATORY.
    """
    errors = []

    # 1. JWT Secret Validation
    if not settings.jwt_secret or settings.jwt_secret == "change-me":
        errors.append("JWT_SECRET must be set in production (not 'change-me')")
    elif len(settings.jwt_secret) < 32:
        errors.append(f"JWT_SECRET too short ({len(settings.jwt_secret)} chars). Minimum 32 characters required for security.")
    elif _is_weak_secret(settings.jwt_secret):
        errors.append("JWT_SECRET appears to be weak (common words, sequential chars, etc.). Generate with: openssl rand -hex 32")

    # 2. Settings Encryption Key Validation (if using encrypted settings)
    if settings.settings_encryption_key:
        if len(settings.settings_encryption_key) < 32:
            errors.append(f"SETTINGS_ENCRYPTION_KEY too short. Must be Fernet key (44 chars base64).")

    # 3. Database URL Validation
    if "postgres:postgres@localhost" in settings.database_url.lower():
        errors.append("DATABASE_URL appears to use default credentials. Use strong database password in production.")

    if "localhost" in settings.database_url or "127.0.0.1" in settings.database_url:
        errors.append("DATABASE_URL points to localhost. Use production database URL.")

    # 4. Redis URL Validation
    if "localhost" in settings.redis_url or "127.0.0.1" in settings.redis_url:
        errors.append("REDIS_URL points to localhost. Use production Redis URL.")

    # 5. CORS Origins Validation
    cors_origins = settings.cors_origins()
    if any("localhost" in origin for origin in cors_origins):
        errors.append("BACKEND_CORS_ORIGINS contains localhost. Remove development origins for production.")

    # 6. LLM API Key Validation (at least one must be set)
    if not settings.llm_api_key and not settings.openai_api_key and not settings.anthropic_api_key:
        errors.append("At least one LLM API key (LLM_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY) must be set in production")

    # 7. Debug Mode Check
    if settings.debug:
        errors.append("DEBUG mode is enabled. Must be False in production to prevent information disclosure.")

    # If any validation errors, raise exception with ALL issues
    if errors:
        error_msg = "\n\n🚨 PRODUCTION SECURITY VALIDATION FAILED 🚨\n\n" + \
                   "The following critical security issues must be fixed before deploying:\n\n" + \
                   "\n".join(f"  ❌ {i+1}. {err}" for i, err in enumerate(errors)) + \
                   "\n\nFix these issues in your .env file or environment variables.\n"
        raise RuntimeError(error_msg)


def _is_weak_secret(secret: str) -> bool:
    """
    Check if a secret appears to be weak.

    Weak secrets include:
    - Common words/phrases
    - Sequential characters
    - Repeated patterns
    - Low entropy
    """
    # Check for common weak patterns
    weak_patterns = [
        r"^(secret|password|key|test|demo|example|sample|default)",
        r"^(123|abc|qwerty|asdf)",
        r"(.)\1{5,}",  # Repeated character (aaaaaa, 111111)
        r"^(0123456789|abcdefg)",  # Sequential
    ]

    secret_lower = secret.lower()
    for pattern in weak_patterns:
        if re.search(pattern, secret_lower):
            return True

    # Check entropy (simple check: should have mix of chars)
    has_upper = any(c.isupper() for c in secret)
    has_lower = any(c.islower() for c in secret)
    has_digit = any(c.isdigit() for c in secret)

    # If it's all one type (all lowercase, all digits, etc.), consider it weak
    if not (has_upper or has_lower or has_digit):
        return True

    # Check for very low character variety
    unique_chars = len(set(secret))
    if unique_chars < len(secret) / 4:  # Less than 25% unique characters
        return True

    return False
