from typing import Optional
from pydantic import BaseModel

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.trading import (
    OrderCreate,
    OrderClose,
    TradeOut,
    PositionOut,
    PositionSizeRequest,
    PositionSizeResponse,
    CalculateSLTPRequest,
    CalculateSLTPResponse,
)
from app.services import trading_service
from app.config import get_settings
from app.core.logging import get_logger
from app.core.validators import (
    validate_uuid,
    validate_symbol,
    validate_lot_size,
    validate_price,
    validate_sl_tp,
)


router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)


class TradeOutWithMT5(BaseModel):
    """Trade response with MT5 execution status."""
    trade: TradeOut
    mt5_execution: dict

    class Config:
        from_attributes = True


@router.get("/positions", response_model=list[PositionOut])
def list_positions(db: Session = Depends(deps.get_db), current_user=Depends(deps.get_current_user)):
    return trading_service.list_positions(db, current_user.id)


@router.post("/orders", response_model=TradeOutWithMT5, status_code=status.HTTP_201_CREATED)
async def create_order(order: OrderCreate, db: Session = Depends(deps.get_db), current_user=Depends(deps.get_current_user)):
    # Validate symbol format
    validated_symbol = validate_symbol(order.symbol)

    # Validate lot size
    validated_lot_size = validate_lot_size(order.lot_size, min_lot=0.01, max_lot=settings.max_lot_size)

    # Validate price
    validated_price = validate_price(order.price, validated_symbol)

    # Validate SL/TP levels
    validated_sl, validated_tp = validate_sl_tp(
        stop_loss=order.stop_loss,
        take_profit=order.take_profit,
        entry_price=validated_price,
        order_type=order.order_type,
    )

    # Check max positions limit
    current_positions = trading_service.list_positions(db, current_user.id)
    if len(current_positions) >= settings.max_positions_per_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {settings.max_positions_per_user} open positions reached"
        )

    # Calculate required margin (simplified calculation)
    # For accurate margin, need to query MT5 via connector
    leverage = 100  # Default, should come from broker connection
    contract_size = 100000  # Standard lot
    estimated_margin = (validated_price * validated_lot_size * contract_size) / leverage

    logger.info(f"Opening order for user {current_user.id}: {validated_symbol} {order.order_type} {validated_lot_size} lots")
    logger.info(f"Estimated margin required: ${estimated_margin:.2f}")

    # Check if connector is online (if connection_id provided)
    if order.connection_id:
        if not trading_service.is_connector_online(order.connection_id):
            logger.warning(f"Connector {order.connection_id} is not online")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="MT5 connector is not online. Please ensure the connector is running."
            )

    # Open the order and send to MT5
    # Note: This will raise HTTPException if MT5 execution fails (with rollback)
    try:
        trade, mt5_result = await trading_service.open_order_with_mt5(
            db,
            current_user.id,
            symbol=validated_symbol,  # Use validated symbol
            order_type=order.order_type,
            lot_size=validated_lot_size,  # Use validated lot size
            price=validated_price,  # Use validated price
            stop_loss=validated_sl,  # Use validated SL
            take_profit=validated_tp,  # Use validated TP
            connection_id=order.connection_id,
        )
    except HTTPException:
        # Re-raise HTTP exceptions (from trading_service)
        raise
    except Exception as e:
        logger.error(f"Unexpected error opening order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while opening the order"
        )

    logger.info(f"Order executed successfully on MT5 via connector {order.connection_id}")

    return TradeOutWithMT5(trade=TradeOut.model_validate(trade), mt5_execution=mt5_result)


@router.put("/orders/{order_id}/close", response_model=TradeOutWithMT5)
async def close_order(order_id: str, payload: OrderClose, db: Session = Depends(deps.get_db), current_user=Depends(deps.get_current_user)):
    # Validate UUID format
    order_uuid = validate_uuid(order_id, "order_id")

    trade, mt5_result = await trading_service.close_order_with_mt5(db, current_user.id, str(order_uuid), payload.close_price)
    if not trade:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    
    if mt5_result.get("success"):
        logger.info(f"Close order sent to MT5 successfully for order {order_id}")
    else:
        logger.warning(f"MT5 close execution failed: {mt5_result.get('error', 'Unknown error')}")
    
    return TradeOutWithMT5(trade=TradeOut.model_validate(trade), mt5_execution=mt5_result)


@router.get("/history", response_model=list[TradeOut])
def trade_history(db: Session = Depends(deps.get_db), current_user=Depends(deps.get_current_user)):
    return trading_service.list_trades(db, current_user.id)


@router.get("/signals")
def signals():
    return []


@router.get("/dashboard/stats")
def dashboard_stats(
    db: Session = Depends(deps.get_db), 
    current_user=Depends(deps.get_current_user)
):
    """
    Get dashboard statistics for the current user.
    Uses real balance from MT5 via connector when available.
    """
    from datetime import datetime
    from app.api.websocket.connection_manager import connection_manager
    
    # Get all positions and trades
    positions = trading_service.list_positions(db, current_user.id)
    trades = trading_service.list_trades(db, current_user.id)
    
    # Calculate stats
    open_positions_count = len(positions)
    
    # Calculate equity from positions (handle None values)
    total_unrealized_pnl = sum(
        float(pos.profit or 0) for pos in positions
    ) if positions else 0.0
    
    # Calculate today's P/L from closed trades
    today = datetime.utcnow().date()
    today_trades = [t for t in trades if t.close_time and t.close_time.date() == today]
    today_pnl = sum(float(t.profit or 0) for t in today_trades) if today_trades else 0.0
    
    # Calculate total realized P/L (only closed trades with profit)
    closed_trades = [t for t in trades if t.close_time is not None]
    total_realized_pnl = sum(float(t.profit or 0) for t in closed_trades) if closed_trades else 0.0
    
    # Try to get real balance from MT5 via connector
    mt5_account = connection_manager.get_user_account_info(current_user.email)
    
    if mt5_account:
        # Use real MT5 account data
        current_balance = mt5_account["balance"]
        current_equity = mt5_account["equity"]
        logger.info(f"Using real MT5 balance for user {current_user.id}: ${current_balance:.2f}")
    else:
        # Fallback: Calculate from trades (for users without active connector)
        base_balance = 10000.0  # Default starting balance
        current_balance = base_balance + total_realized_pnl
        current_equity = current_balance + total_unrealized_pnl
        logger.debug(f"No active MT5 connection, using calculated balance for user {current_user.id}")
    
    # Calculate win rate (from closed trades only)
    winning_trades = [t for t in closed_trades if t.profit and float(t.profit) > 0]
    win_rate = (len(winning_trades) / len(closed_trades) * 100) if closed_trades else 0.0
    
    return {
        "balance": round(current_balance, 2),
        "equity": round(current_equity, 2),
        "open_positions": open_positions_count,
        "today_pnl": round(today_pnl, 2),
        "total_pnl": round(total_realized_pnl, 2),
        "unrealized_pnl": round(total_unrealized_pnl, 2),
        "total_trades": len(closed_trades),
        "win_rate": round(win_rate, 1),
        "has_live_connection": mt5_account is not None,
    }


@router.post("/position-size/calculate", response_model=PositionSizeResponse)
def calculate_position_size(
    request: PositionSizeRequest,
    current_user=Depends(deps.get_current_user)
):
    """
    Calculate position size based on risk management.
    
    Formula: Position Size = (Account Balance * Risk %) / (Stop Loss Pips * Pip Value)
    """
    # Calculate stop loss in pips
    if request.entry_price > request.stop_loss:  # BUY order
        stop_loss_pips = (request.entry_price - request.stop_loss) / 0.0001
    else:  # SELL order
        stop_loss_pips = (request.stop_loss - request.entry_price) / 0.0001
    
    # Calculate risk amount
    risk_amount = request.account_balance * (request.risk_percent / 100)
    
    # Pip value for standard lot (most forex pairs)
    pip_value = 10.0  # $10 per pip for 1 standard lot
    
    # Calculate lot size
    lot_size = risk_amount / (stop_loss_pips * pip_value)
    
    # Apply limits
    lot_size = max(0.01, min(lot_size, settings.max_lot_size))
    lot_size = round(lot_size, 2)  # Round to 2 decimal places
    
    # Calculate margin (simplified)
    leverage = 100
    contract_size = 100000
    margin_required = (request.entry_price * lot_size * contract_size) / leverage
    
    logger.info(f"Position size calculated for user {current_user.id}: {lot_size} lots, risk ${risk_amount:.2f}")
    
    return PositionSizeResponse(
        lot_size=lot_size,
        risk_amount=risk_amount,
        stop_loss_pips=stop_loss_pips,
        margin_required=margin_required
    )


@router.post("/calculate-sl-tp")
def calculate_sl_tp_endpoint(
    request: CalculateSLTPRequest,
    current_user=Depends(deps.get_current_user)
):
    """
    Calculate SL and TP based on risk management settings.
    
    Supports:
    - Fixed pips SL/TP
    - ATR-based SL/TP (requires ATR value)
    - Risk:Reward ratio for TP
    - Percentage-based SL
    """
    from app.services.risk_management import (
        calculate_stop_loss,
        calculate_take_profit,
        SLType,
        TPType,
    )
    
    # Map string types to enums
    sl_type_map = {
        "fixed_pips": SLType.FIXED_PIPS,
        "atr_based": SLType.ATR_BASED,
        "percentage": SLType.PERCENTAGE,
    }
    tp_type_map = {
        "fixed_pips": TPType.FIXED_PIPS,
        "risk_reward": TPType.RISK_REWARD,
        "atr_based": TPType.ATR_BASED,
    }
    
    sl_type = sl_type_map.get(request.sl_type, SLType.ATR_BASED)
    tp_type = tp_type_map.get(request.tp_type, TPType.RISK_REWARD)
    
    # Calculate SL
    stop_loss = calculate_stop_loss(
        entry_price=request.entry_price,
        direction=request.direction,
        sl_type=sl_type,
        sl_value=request.sl_value,
        atr=request.atr,
    )
    
    # Calculate TP
    take_profit = calculate_take_profit(
        entry_price=request.entry_price,
        direction=request.direction,
        tp_type=tp_type,
        tp_value=request.tp_value,
        stop_loss=stop_loss,
        atr=request.atr,
    )
    
    # Calculate distances in pips
    sl_distance_pips = abs(request.entry_price - stop_loss) * 10000
    tp_distance_pips = abs(take_profit - request.entry_price) * 10000
    
    # Calculate risk:reward
    risk_reward = tp_distance_pips / sl_distance_pips if sl_distance_pips > 0 else 0
    
    return CalculateSLTPResponse(
        stop_loss=stop_loss,
        take_profit=take_profit,
        sl_distance_pips=round(sl_distance_pips, 1),
        tp_distance_pips=round(tp_distance_pips, 1),
        risk_reward_ratio=round(risk_reward, 2),
    )


@router.get("/risk-profiles")
def get_risk_profiles(current_user=Depends(deps.get_current_user)):
    """
    Get available risk management profiles.
    """
    from app.services.risk_management import RISK_PROFILES
    from app.services.trailing_stop import TRAILING_CONFIGS
    
    profiles = {}
    for name, config in RISK_PROFILES.items():
        trailing = TRAILING_CONFIGS.get(name)
        profiles[name] = {
            "sl_type": config.sl_type.value,
            "sl_value": config.sl_value,
            "tp_type": config.tp_type.value,
            "tp_value": config.tp_value,
            "risk_per_trade_percent": config.risk_per_trade_percent,
            "max_position_size": config.max_position_size,
            "trailing_stop": {
                "enabled": trailing.enabled if trailing else False,
                "type": trailing.trailing_type.value if trailing else "fixed_pips",
                "activation_pips": trailing.activation_pips if trailing else 20,
                "trail_distance_pips": trailing.trail_distance_pips if trailing else 15,
                "atr_multiplier": trailing.atr_multiplier if trailing else 1.5,
                "breakeven_enabled": trailing.breakeven_enabled if trailing else True,
                "breakeven_pips": trailing.breakeven_pips if trailing else 15,
            } if trailing else None,
        }
    
    return {"profiles": profiles}


@router.get("/position-monitor/status")
def get_position_monitor_status(current_user=Depends(deps.get_current_user)):
    """
    Get position monitor service status.
    
    Returns:
    - is_running: Whether the monitor is active
    - last_sync: Last position sync time
    - managed_connections: Number of connections being monitored
    - total_positions: Total positions with trailing stop management
    """
    from app.services.position_monitor import position_monitor
    return position_monitor.get_status()


@router.post("/position-monitor/sync")
async def trigger_position_sync(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """
    Manually trigger position sync from MT5.
    
    Requests position updates from all connected MT5 terminals.
    """
    from app.api.websocket.connection_manager import connection_manager
    from app.models.broker import BrokerConnection
    
    # Get user's active connections
    connections = db.query(BrokerConnection).filter(
        BrokerConnection.user_id == current_user.id,
        BrokerConnection.is_active == True,
    ).all()
    
    synced = []
    for conn in connections:
        conn_id = str(conn.id)
        if connection_manager.is_connector_online(conn_id):
            try:
                await connection_manager.send_to_connector(conn_id, {
                    "type": "GET_POSITIONS",
                    "request_id": f"manual_sync_{conn_id}",
                })
                synced.append(conn_id)
            except Exception as e:
                logger.warning(f"Failed to sync positions from {conn_id}: {e}")
    
    return {
        "status": "sync_requested",
        "connections_synced": len(synced),
        "connection_ids": synced,
    }
