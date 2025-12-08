import uuid
from datetime import datetime, date

from sqlalchemy import Column, String, DateTime, Date, Numeric, Integer, JSON, ForeignKey, BigInteger, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class BacktestSession(Base):
    __tablename__ = "backtest_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    strategy_id = Column(UUID(as_uuid=True), ForeignKey("strategies.id"))
    symbol = Column(String(20))
    timeframe = Column(String(10))
    start_date = Column(Date)
    end_date = Column(Date)
    initial_balance = Column(Numeric(20, 2))
    config = Column(JSON, nullable=True)
    status = Column(String(50), default="running")
    created_at = Column(DateTime, default=datetime.utcnow)


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("backtest_sessions.id"))
    net_profit = Column(Numeric(20, 2))
    total_trades = Column(Integer)
    winning_trades = Column(Integer)
    losing_trades = Column(Integer)
    win_rate = Column(Numeric(5, 2))
    profit_factor = Column(Numeric(10, 2))
    max_drawdown = Column(Numeric(10, 2))
    max_drawdown_pct = Column(Numeric(5, 2))
    sharpe_ratio = Column(Numeric(10, 2))
    sortino_ratio = Column(Numeric(10, 2))
    calmar_ratio = Column(Numeric(10, 2))
    expectancy = Column(Numeric(20, 2))
    avg_win = Column(Numeric(20, 2))
    avg_loss = Column(Numeric(20, 2))
    equity_curve = Column(JSON)
    trades = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)


class HistoricalData(Base):
    __tablename__ = "historical_data"
    __table_args__ = (UniqueConstraint("symbol", "timeframe", "timestamp", name="uq_historical_data"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False)
    open = Column(Numeric(20, 5))
    high = Column(Numeric(20, 5))
    low = Column(Numeric(20, 5))
    close = Column(Numeric(20, 5))
    volume = Column(Numeric(20, 2))
