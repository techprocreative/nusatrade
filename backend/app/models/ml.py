import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class MLModel(Base):
    __tablename__ = "ml_models"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    name = Column(String(255))
    model_type = Column(String(50))
    config = Column(JSON)
    performance_metrics = Column(JSON)
    file_path = Column(String(500))
    is_active = Column(Boolean, default=False)
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
