import uuid
from datetime import datetime

from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class BrokerConnection(Base):
    __tablename__ = "broker_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    broker_name = Column(String(100), nullable=False)
    account_number = Column(String(50))
    server = Column(String(100))
    is_active = Column(Boolean, default=True)
    last_connected_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConnectorSession(Base):
    __tablename__ = "connector_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    connection_id = Column(UUID(as_uuid=True), ForeignKey("broker_connections.id"))
    session_token = Column(String(255), unique=True)
    status = Column(String(50), default="online")
    last_heartbeat = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
