from datetime import datetime
from decimal import Decimal
import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.trade import Trade, Position
from app.api.websocket.connection_manager import connection_manager
from app.core.logging import get_logger

logger = get_logger(__name__)


def _calc_profit(order_type: str, open_price: float, close_price: float, lot_size: float) -> Decimal:
    pip_value = Decimal("100000")
    if order_type.upper() == "BUY":
        return (Decimal(str(close_price)) - Decimal(str(open_price))) * Decimal(str(lot_size)) * pip_value
    return (Decimal(str(open_price)) - Decimal(str(close_price))) * Decimal(str(lot_size)) * pip_value


def open_order(db: Session, user_id: str, *, symbol: str, order_type: str, lot_size: float, price: float, stop_loss=None, take_profit=None, connection_id=None) -> Trade:
    """
    Create trade and position in database.

    IMPORTANT: This function no longer commits the transaction.
    The caller (open_order_with_mt5) is responsible for commit/rollback
    based on MT5 execution result.
    """
    import uuid
    order_type = order_type.upper()

    # Convert user_id to UUID if string
    user_uuid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
    conn_uuid = uuid.UUID(str(connection_id)) if connection_id else None

    trade = Trade(
        user_id=user_uuid,
        connection_id=conn_uuid,
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
        user_id=user_uuid,
        connection_id=conn_uuid,
        symbol=symbol,
        trade_type=order_type,
        lot_size=Decimal(str(lot_size)),
        open_price=Decimal(str(price)),
        current_price=Decimal(str(price)),
        open_time=datetime.utcnow(),
    )
    db.add(trade)
    db.add(position)

    # REMOVED: db.commit() - caller is responsible
    # REMOVED: db.refresh() - will be refreshed after commit

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


async def send_open_order_to_mt5(
    trade: Trade,
    connection_id: str,
    symbol: str,
    order_type: str,
    lot_size: float,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
) -> dict:
    """Send open order command to MT5 via WebSocket connector."""
    if not connection_id:
        logger.warning("No connection_id provided, skipping MT5 execution")
        return {"success": False, "error": "No connection_id provided"}
    
    # Log current connector status
    is_online = connection_manager.is_connector_online(connection_id)
    logger.info(f"Connector {connection_id} online status: {is_online}")
    
    if not is_online:
        logger.warning(f"Connector {connection_id} is not online - trade will be saved but not executed in MT5")
        return {"success": False, "error": "Connector is not online", "connection_id": connection_id}
    
    request_id = str(trade.id)
    # Use TRADE_OPEN format expected by connector's MessageHandler
    trade_command = {
        "type": "TRADE_OPEN",
        "request_id": request_id,
        "symbol": symbol,
        "order_type": order_type.upper(),
        "lot_size": lot_size,
        "comment": f"NusaTrade-{request_id[:8]}",
    }
    
    if stop_loss is not None:
        trade_command["stop_loss"] = stop_loss
    if take_profit is not None:
        trade_command["take_profit"] = take_profit
    
    try:
        logger.info(f"Sending TRADE_OPEN to connector {connection_id}: {trade_command}")
        await connection_manager.send_to_connector(connection_id, trade_command)
        logger.info(f"Sent TRADE_OPEN to connector {connection_id}: {symbol} {order_type} {lot_size} lots")
        return {"success": True, "request_id": request_id, "connection_id": connection_id}
    except Exception as e:
        logger.error(f"Failed to send TRADE_OPEN to connector: {e}")
        return {"success": False, "error": str(e), "connection_id": connection_id}


async def send_close_order_to_mt5(
    trade: Trade,
    connection_id: str,
    ticket: Optional[int] = None,
) -> dict:
    """Send close order command to MT5 via WebSocket connector."""
    if not connection_id:
        logger.warning("No connection_id provided, skipping MT5 execution")
        return {"success": False, "error": "No connection_id provided"}
    
    if not connection_manager.is_connector_online(connection_id):
        logger.warning(f"Connector {connection_id} is not online")
        return {"success": False, "error": "Connector is not online"}
    
    request_id = str(trade.id)
    # Use TRADE_CLOSE format expected by connector's MessageHandler
    trade_command = {
        "type": "TRADE_CLOSE",
        "request_id": request_id,
        "symbol": trade.symbol,
    }
    
    # If we have a ticket number (MT5 position ID), include it
    if ticket is not None:
        trade_command["ticket"] = ticket
    
    # Include lot_size for partial close support
    if trade.lot_size:
        trade_command["lot_size"] = float(trade.lot_size)
    
    try:
        await connection_manager.send_to_connector(connection_id, trade_command)
        logger.info(f"Sent TRADE_CLOSE to connector {connection_id}: {trade.symbol}")
        return {"success": True, "request_id": request_id}
    except Exception as e:
        logger.error(f"Failed to send TRADE_CLOSE to connector: {e}")
        return {"success": False, "error": str(e)}


async def open_order_with_mt5(
    db: Session,
    user_id: str,
    *,
    symbol: str,
    order_type: str,
    lot_size: float,
    price: float,
    stop_loss=None,
    take_profit=None,
    connection_id=None,
) -> tuple[Trade, dict]:
    """
    Open order in database and send to MT5 via connector.

    IMPORTANT: This uses a two-phase commit approach:
    1. Create trade and position in DB (not committed)
    2. Send to MT5 for execution
    3. If MT5 succeeds → commit to DB
    4. If MT5 fails → rollback DB transaction

    This prevents data inconsistency between DB and MT5.
    """
    # Create trade and position in database (NOT committed yet)
    trade = open_order(
        db, user_id,
        symbol=symbol,
        order_type=order_type,
        lot_size=lot_size,
        price=price,
        stop_loss=stop_loss,
        take_profit=take_profit,
        connection_id=connection_id,
    )

    # Flush to get the ID, but don't commit
    db.flush()

    try:
        # Send to MT5 via WebSocket for execution
        mt5_result = await send_open_order_to_mt5(
            trade=trade,
            connection_id=connection_id,
            symbol=symbol,
            order_type=order_type,
            lot_size=lot_size,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )

        # Check MT5 execution result
        if mt5_result.get("success"):
            # MT5 execution successful - commit to database
            db.commit()
            logger.info(f"Trade {trade.id} committed to DB after successful MT5 execution")

            return trade, mt5_result
        else:
            # MT5 execution failed - rollback database transaction
            error_msg = mt5_result.get("error", "Unknown error")
            logger.error(f"Trade {trade.id} ROLLED BACK - MT5 execution failed: {error_msg}")

            db.rollback()

            # Send error notification to user's frontend
            try:
                await connection_manager.broadcast_to_user(user_id, {
                    "type": "TRADE_ERROR",
                    "trade_id": str(trade.id),
                    "symbol": symbol,
                    "order_type": order_type,
                    "error": error_msg,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                })
            except Exception as e:
                logger.error(f"Failed to broadcast trade error: {e}")

            # Raise exception to indicate failure
            from fastapi import HTTPException
            raise HTTPException(
                status_code=503,
                detail=f"Failed to execute trade on MT5: {error_msg}"
            )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Unexpected error - rollback and raise
        logger.error(f"Unexpected error in open_order_with_mt5: {e}")
        db.rollback()
        raise


async def close_order_with_mt5(
    db: Session,
    user_id: str,
    order_id: str,
    close_price: float,
) -> tuple[Optional[Trade], dict]:
    """Close order in database and send to MT5 via connector."""
    # Get the trade first to get connection_id
    try:
        order_uuid = uuid.UUID(str(order_id))
    except (ValueError, TypeError):
        return None, {"success": False, "error": "Invalid order ID"}
    
    trade = db.query(Trade).filter(Trade.id == order_uuid, Trade.user_id == user_id).first()
    if not trade:
        return None, {"success": False, "error": "Order not found"}
    
    connection_id = trade.connection_id
    
    # Send close command to MT5 first
    mt5_result = await send_close_order_to_mt5(trade=trade, connection_id=connection_id)
    
    # Then close in database
    closed_trade = close_order(db, user_id, order_id, close_price)
    
    return closed_trade, mt5_result


def is_connector_online(connection_id: str) -> bool:
    """Check if a connector is currently online."""
    if not connection_id:
        return False
    return connection_manager.is_connector_online(connection_id)
