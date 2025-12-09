from functools import lru_cache
from typing import List, Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    app_name: str = "Forex AI Backend"
    environment: str = "development"
    debug: bool = False
    log_level: str = "INFO"
    backend_cors_origins: List[str] | str = ["http://localhost:3000", "http://localhost:8000"]

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

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
    if settings.is_production:
        if settings.jwt_secret == "change-me":
            raise RuntimeError("jwt_secret must be set in production")
        if not settings.openai_api_key and not settings.anthropic_api_key:
            raise RuntimeError("At least one LLM API key must be set in production")
    return settings
