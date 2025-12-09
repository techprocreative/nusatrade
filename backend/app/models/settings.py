"""System settings model for runtime configuration."""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Text, Boolean, DateTime, Enum
from sqlalchemy.sql import func

from app.models.base import Base


class SettingCategory(str, PyEnum):
    """Categories for system settings."""
    AI_PROVIDER = "ai_provider"
    REDIS = "redis"
    EMAIL = "email"
    RATE_LIMITING = "rate_limiting"
    TRADING = "trading"
    STORAGE = "storage"
    GENERAL = "general"


class SystemSetting(Base):
    """System settings stored in database.
    
    Allows runtime configuration changes without redeployment.
    Sensitive values are encrypted at rest.
    """
    __tablename__ = "system_settings"
    
    key = Column(String(100), primary_key=True, index=True)
    value = Column(Text, nullable=True)  # Encrypted for sensitive values
    category = Column(Enum(SettingCategory), nullable=False, index=True)
    is_encrypted = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(Text, nullable=True)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    updated_by = Column(String(100), nullable=True)  # User ID who last updated
    
    def __repr__(self):
        return f"<SystemSetting(key={self.key}, category={self.category})>"
