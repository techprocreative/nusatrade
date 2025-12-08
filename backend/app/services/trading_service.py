from datetime import datetime
from decimal import Decimal
import uuid

from sqlalchemy.orm import Session

from app.models.trade import Trade, Position


def _calc_profit(order_type: str, open_price: float, close_price: float, lot_size: float) -> Decimal:
    pip_value = Decimal("100000")
    if order_type.upper() == "BUY":
        return (Decimal(str(close_price)) - Decimal(str(open_price))) * Decimal(str(lot_size)) * pip_value
    return (Decimal(str(open_price)) - Decimal(str(close_price))) * Decimal(str(lot_size)) * pip_value


def open_order(db: Session, user_id: str, *, symbol: str, order_type: str, lot_size: float, price: float, stop_loss=None, take_profit=None, connection_id=None) -> Trade:
    order_type = order_type.upper()
    trade = Trade(
        user_id=user_id,
        connection_id=connection_id,
        symbol=symbol,
        trade_type=order_type,
        lot_size=Decimal(str(lot_size)),
        open_price=Decimal(str(price)),
        stop_loss=Decimal(str(stop_loss)) if stop_loss else None,
        take_profit=Decimal(str(take_profit)) if take_profit else None,
        open_time=datetime.utcnow(),
        source="api",
    )
    position = Position(
        user_id=user_id,
        connection_id=connection_id,
        symbol=symbol,
        trade_type=order_type,
        lot_size=Decimal(str(lot_size)),
        open_price=Decimal(str(price)),
        current_price=Decimal(str(price)),
        open_time=datetime.utcnow(),
    )
    db.add(trade)
    db.add(position)
    db.commit()
    db.refresh(trade)
    db.refresh(position)
    return trade


def close_order(db: Session, user_id: str, order_id: str, close_price: float) -> Trade:
    try:
        order_uuid = uuid.UUID(str(order_id))
    except (ValueError, TypeError):
        return None
    trade = db.query(Trade).filter(Trade.id == order_uuid, Trade.user_id == user_id).first()
    if not trade:
        return None
    position = db.query(Position).filter(Position.connection_id == trade.connection_id, Position.symbol == trade.symbol, Position.user_id == user_id).first()
    profit = _calc_profit(trade.trade_type, float(trade.open_price or 0), close_price, float(trade.lot_size or 0))
    trade.close_price = Decimal(str(close_price))
    trade.profit = profit
    trade.close_time = datetime.utcnow()
    if position:
        db.delete(position)
    db.commit()
    db.refresh(trade)
    return trade


def list_positions(db: Session, user_id: str):
    return db.query(Position).filter(Position.user_id == user_id).all()


def list_trades(db: Session, user_id: str):
    return db.query(Trade).filter(Trade.user_id == user_id).order_by(Trade.open_time.desc()).all()
