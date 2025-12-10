import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Boolean, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


# Default settings for new users
DEFAULT_USER_SETTINGS = {
    "defaultLotSize": "0.1",
    "maxLotSize": "1.0",
    "maxOpenPositions": "5",
    "defaultStopLoss": "50",
    "defaultTakeProfit": "100",
    "riskPerTrade": "2",
    "emailNotifications": True,
    "tradeAlerts": True,
    "dailySummary": False,
    "theme": "dark",
    "timezone": "Asia/Jakarta",
    "language": "en",
}


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    role = Column(String(50), default="trader")
    subscription_tier = Column(String(50), default="free")
    
    # 2FA fields
    totp_secret = Column(String(32), nullable=True)
    totp_enabled = Column(Boolean, default=False, nullable=False)
    
    # User settings/preferences stored as JSON
    settings = Column(JSON, default=dict, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == "admin"
    
    def get_settings(self) -> dict:
        """Get user settings with defaults for missing keys."""
        user_settings = self.settings or {}
        return {**DEFAULT_USER_SETTINGS, **user_settings}

