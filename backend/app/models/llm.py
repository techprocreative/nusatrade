import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, JSON, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class LLMConversation(Base):
    __tablename__ = "llm_conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    title = Column(String(255), nullable=True)
    context = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class LLMMessage(Base):
    __tablename__ = "llm_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("llm_conversations.id"))
    role = Column(String(20))
    content = Column(String)
    tokens_used = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)


class MarketAnalysis(Base):
    __tablename__ = "market_analysis"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    symbol = Column(String(20))
    timeframe = Column(String(10))
    analysis_type = Column(String(50))
    content = Column(String)
    sentiment_score = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
