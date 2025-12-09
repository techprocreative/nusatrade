"""Settings service for loading configuration from database with env fallback."""

from functools import lru_cache
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.core.security import decrypt_setting_value
from app.models.settings import SystemSetting


class SettingsService:
    """Service to load settings from database with environment variable fallback."""
    
    def __init__(self, db: Session):
        self.db = db
        self._cache: dict[str, Any] = {}
    
    def get(self, key: str, default: Any = None, decrypt: bool = False) -> Any:
        """
        Get setting from database or fallback to default.
        
        Args:
            key: Setting key
            default: Default value if not found in database
            decrypt: Whether to decrypt the value if encrypted
            
        Returns:
            Setting value or default
        """
        # Check cache first
        cache_key = f"{key}:{'encrypted' if decrypt else 'plain'}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Try database
        setting = self.db.query(SystemSetting).filter(
            SystemSetting.key == key,
            SystemSetting.is_active == True
        ).first()
        
        if setting and setting.value:
            # Decrypt if needed
            if setting.is_encrypted and decrypt:
                value = decrypt_setting_value(setting.value)
            else:
                value = setting.value
            
            # Cache the value
            self._cache[cache_key] = value
            return value
        
        # Fallback to default
        return default
    
    def get_int(self, key: str, default: int = 0) -> int:
        """Get setting as integer."""
        value = self.get(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default
    
    def get_float(self, key: str, default: float = 0.0) -> float:
        """Get setting as float."""
        value = self.get(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default
    
    def get_bool(self, key: str, default: bool = False) -> bool:
        """Get setting as boolean."""
        value = self.get(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        return default
    
    def invalidate_cache(self, key: Optional[str] = None):
        """
        Invalidate settings cache.
        
        Args:
            key: Specific key to invalidate, or None to clear all
        """
        if key:
            # Remove all cache entries for this key
            keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{key}:")]
            for k in keys_to_remove:
                del self._cache[k]
        else:
            # Clear entire cache
            self._cache.clear()
    
    def get_llm_config(self, fallback_api_key: Optional[str] = None, 
                       fallback_base_url: Optional[str] = None,
                       fallback_model: str = "gpt-4-turbo-preview") -> dict:
        """
        Get LLM configuration from database with environment fallback.
        
        Args:
            fallback_api_key: Fallback API key from environment
            fallback_base_url: Fallback base URL from environment
            fallback_model: Fallback model from environment
            
        Returns:
            Dict with api_key, base_url, and model
        """
        return {
            "api_key": self.get("llm_api_key", fallback_api_key, decrypt=True),
            "base_url": self.get("llm_base_url", fallback_base_url),
            "model": self.get("llm_model", fallback_model),
        }


@lru_cache()
def get_settings_service(db: Session) -> SettingsService:
    """Get cached settings service instance."""
    return SettingsService(db)
