"""Signal generation and management service."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.models.trade import Signal
from app.core.logging import get_logger


logger = get_logger(__name__)


class SignalDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class SignalStatus(str, Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


def create_signal(
    db: Session,
    user_id: str,
    *,
    symbol: str,
    direction: SignalDirection,
    confidence: float,
    entry_price: float,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    ml_model_id: Optional[str] = None,
) -> Signal:
    """Create a new trading signal."""
    signal = Signal(
        id=uuid4(),
        user_id=user_id,
        symbol=symbol.upper(),
        direction=direction.value,
        confidence=Decimal(str(min(max(confidence, 0), 100))),
        entry_price=Decimal(str(entry_price)),
        stop_loss=Decimal(str(stop_loss)) if stop_loss else None,
        take_profit=Decimal(str(take_profit)) if take_profit else None,
        ml_model_id=UUID(ml_model_id) if ml_model_id else None,
        status=SignalStatus.PENDING.value,
        created_at=datetime.utcnow(),
    )
    
    db.add(signal)
    db.commit()
    db.refresh(signal)
    
    logger.info(f"Signal created: {signal.id} - {direction} {symbol} @ {entry_price}")
    return signal


def get_signal(db: Session, signal_id: str, user_id: str) -> Optional[Signal]:
    """Get a signal by ID for a specific user."""
    try:
        signal_uuid = UUID(signal_id)
    except ValueError:
        return None
    
    return db.query(Signal).filter(
        Signal.id == signal_uuid,
        Signal.user_id == user_id,
    ).first()


def list_signals(
    db: Session,
    user_id: str,
    *,
    status: Optional[SignalStatus] = None,
    symbol: Optional[str] = None,
    limit: int = 50,
) -> List[Signal]:
    """List signals for a user with optional filters."""
    query = db.query(Signal).filter(Signal.user_id == user_id)
    
    if status:
        query = query.filter(Signal.status == status.value)
    
    if symbol:
        query = query.filter(Signal.symbol == symbol.upper())
    
    return query.order_by(Signal.created_at.desc()).limit(limit).all()


def update_signal_status(
    db: Session,
    signal_id: str,
    user_id: str,
    new_status: SignalStatus,
    executed_trade_id: Optional[str] = None,
) -> Optional[Signal]:
    """Update a signal's status."""
    signal = get_signal(db, signal_id, user_id)
    if not signal:
        return None
    
    old_status = signal.status
    signal.status = new_status.value
    
    if executed_trade_id and new_status == SignalStatus.EXECUTED:
        # Store reference to the executed trade
        pass  # TODO: Add executed_trade_id field to Signal model
    
    db.commit()
    db.refresh(signal)
    
    logger.info(f"Signal {signal_id} status: {old_status} -> {new_status.value}")
    return signal


def cancel_signal(db: Session, signal_id: str, user_id: str) -> Optional[Signal]:
    """Cancel a pending signal."""
    signal = get_signal(db, signal_id, user_id)
    if not signal or signal.status != SignalStatus.PENDING.value:
        return None
    
    return update_signal_status(db, signal_id, user_id, SignalStatus.CANCELLED)


def calculate_position_size(
    account_balance: float,
    risk_percent: float,
    entry_price: float,
    stop_loss: float,
    pip_value: float = 10.0,
) -> float:
    """Calculate position size based on risk management."""
    if stop_loss == entry_price:
        return 0.01  # Minimum lot size
    
    risk_amount = account_balance * (risk_percent / 100)
    stop_loss_pips = abs(entry_price - stop_loss) * 10000  # For 4-digit pairs
    
    if stop_loss_pips == 0:
        return 0.01
    
    lot_size = risk_amount / (stop_loss_pips * pip_value)
    
    # Round to 2 decimal places and enforce min/max
    lot_size = max(0.01, min(10.0, round(lot_size, 2)))
    
    return lot_size


def validate_signal_parameters(
    symbol: str,
    direction: str,
    entry_price: float,
    stop_loss: Optional[float],
    take_profit: Optional[float],
) -> List[str]:
    """Validate signal parameters and return list of errors."""
    errors = []
    
    # Valid forex pairs (major and minor)
    valid_symbols = [
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD",
        "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "EURAUD", "EURCHF", "GBPCHF",
        "XAUUSD", "XAGUSD",  # Metals
    ]
    
    if symbol.upper() not in valid_symbols:
        errors.append(f"Invalid symbol: {symbol}")
    
    if direction.upper() not in ["BUY", "SELL"]:
        errors.append(f"Invalid direction: {direction}")
    
    if entry_price <= 0:
        errors.append("Entry price must be positive")
    
    if stop_loss is not None:
        if stop_loss <= 0:
            errors.append("Stop loss must be positive")
        elif direction.upper() == "BUY" and stop_loss >= entry_price:
            errors.append("Stop loss must be below entry for BUY orders")
        elif direction.upper() == "SELL" and stop_loss <= entry_price:
            errors.append("Stop loss must be above entry for SELL orders")
    
    if take_profit is not None:
        if take_profit <= 0:
            errors.append("Take profit must be positive")
        elif direction.upper() == "BUY" and take_profit <= entry_price:
            errors.append("Take profit must be above entry for BUY orders")
        elif direction.upper() == "SELL" and take_profit >= entry_price:
            errors.append("Take profit must be below entry for SELL orders")
    
    return errors
