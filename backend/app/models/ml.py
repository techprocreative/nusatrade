import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, JSON, ForeignKey, Float, Integer, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


class MLModel(Base):
    __tablename__ = "ml_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id"), nullable=True)
    name = Column(String(255))
    model_type = Column(String(50))
    symbol = Column(String(20), default="EURUSD")
    timeframe = Column(String(10), default="H1")
    config = Column(JSON)
    performance_metrics = Column(JSON)
    file_path = Column(String(500))
    is_active = Column(Boolean, default=False)
    # Training status fields
    training_status = Column(String(20), default="idle")  # idle, training, completed, failed
    training_error = Column(String(500), nullable=True)
    training_started_at = Column(DateTime, nullable=True)
    training_completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MLPrediction(Base):
    __tablename__ = "ml_predictions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    model_id = Column(UUID(as_uuid=True), ForeignKey("ml_models.id"))
    symbol = Column(String(20))
    prediction = Column(JSON)
    actual_outcome = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class DefaultMLModel(Base):
    """System-wide default ML model per symbol."""
    __tablename__ = "default_ml_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20), nullable=False, unique=True, index=True)
    model_path = Column(String(500), nullable=False)
    model_id = Column(String(100), nullable=False)
    is_system_default = Column(Boolean, default=True)

    # Performance metrics (cached for quick display)
    win_rate = Column(Float, nullable=True)
    profit_factor = Column(Float, nullable=True)
    accuracy = Column(Float, nullable=True)
    total_trades = Column(Integer, nullable=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class UserDefaultModel(Base):
    """User-specific model override per symbol."""
    __tablename__ = "user_default_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(20), nullable=False)
    model_path = Column(String(500), nullable=False)
    model_id = Column(String(100), nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('user_id', 'symbol', name='uq_user_symbol'),
        Index('idx_user_symbol', 'user_id', 'symbol'),
    )

    # Relationships
    user = relationship("User", back_populates="default_models")
