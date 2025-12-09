import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, JSON, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Strategy(Base):
    __tablename__ = "strategies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    strategy_type = Column(String(50), nullable=True)  # ai_generated, custom, preset
    
    # Strategy logic
    code = Column(Text, nullable=True)  # Generated strategy code
    parameters = Column(JSON, nullable=True)  # Strategy parameters
    indicators = Column(JSON, nullable=True)  # List of indicators used
    entry_rules = Column(JSON, nullable=True)  # Entry conditions
    exit_rules = Column(JSON, nullable=True)  # Exit conditions
    risk_management = Column(JSON, nullable=True)  # Risk settings
    
    # Legacy config (for backward compatibility)
    config = Column(JSON, nullable=True)
    
    # Status
    is_active = Column(Boolean, default=False)
    is_public = Column(Boolean, default=False)
    
    # Performance (cached from last backtest)
    backtest_results = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
