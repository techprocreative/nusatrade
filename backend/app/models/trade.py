import uuid
from datetime import datetime

from sqlalchemy import Column, String, DateTime, Numeric, BigInteger, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class Trade(Base):
    __tablename__ = "trades"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    connection_id = Column(UUID(as_uuid=True), ForeignKey("broker_connections.id"))
    ticket = Column(BigInteger)
    symbol = Column(String(20), nullable=False)
    trade_type = Column(String(10), nullable=False)
    lot_size = Column(Numeric(10, 2))
    open_price = Column(Numeric(20, 5))
    close_price = Column(Numeric(20, 5))
    stop_loss = Column(Numeric(20, 5))
    take_profit = Column(Numeric(20, 5))
    profit = Column(Numeric(20, 2))
    commission = Column(Numeric(20, 2))
    swap = Column(Numeric(20, 2))
    open_time = Column(DateTime)
    close_time = Column(DateTime)
    magic_number = Column(Integer)
    comment = Column(String)
    source = Column(String(50))
    status = Column(String(20), default="open")  # open, closed, pending
    ml_model_id = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Position(Base):
    __tablename__ = "positions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    connection_id = Column(UUID(as_uuid=True), ForeignKey("broker_connections.id"))
    ticket = Column(BigInteger)
    symbol = Column(String(20))
    trade_type = Column(String(10))
    lot_size = Column(Numeric(10, 2))
    open_price = Column(Numeric(20, 5))
    current_price = Column(Numeric(20, 5))
    stop_loss = Column(Numeric(20, 5))
    take_profit = Column(Numeric(20, 5))
    profit = Column(Numeric(20, 2))
    open_time = Column(DateTime)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Signal(Base):
    __tablename__ = "signals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    ml_model_id = Column(UUID(as_uuid=True), ForeignKey("ml_models.id"), nullable=True)
    symbol = Column(String(20))
    direction = Column(String(10))
    confidence = Column(Numeric(5, 2))
    entry_price = Column(Numeric(20, 5))
    stop_loss = Column(Numeric(20, 5))
    take_profit = Column(Numeric(20, 5))
    status = Column(String(50), default="pending")
    # Reference to the trade that was executed from this signal
    executed_trade_id = Column(UUID(as_uuid=True), ForeignKey("trades.id"), nullable=True)
    executed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
