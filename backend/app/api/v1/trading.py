from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.schemas.trading import (
    OrderCreate, 
    OrderClose, 
    TradeOut, 
    PositionOut,
    PositionSizeRequest,
    PositionSizeResponse
)
from app.services import trading_service
from app.config import get_settings
from app.core.logging import get_logger


router = APIRouter()
settings = get_settings()
logger = get_logger(__name__)


@router.get("/positions", response_model=list[PositionOut])
def list_positions(db: Session = Depends(deps.get_db), current_user=Depends(deps.get_current_user)):
    return trading_service.list_positions(db, current_user.id)


@router.post("/orders", response_model=TradeOut, status_code=status.HTTP_201_CREATED)
def create_order(order: OrderCreate, db: Session = Depends(deps.get_db), current_user=Depends(deps.get_current_user)):
    # Validate lot size
    if order.lot_size <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="lot_size must be positive")
    
    if order.lot_size > settings.max_lot_size:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"lot_size cannot exceed {settings.max_lot_size}"
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
    estimated_margin = (order.price * order.lot_size * contract_size) / leverage
    
    logger.info(f"Opening order for user {current_user.id}: {order.symbol} {order.order_type} {order.lot_size} lots")
    logger.info(f"Estimated margin required: ${estimated_margin:.2f}")
    
    # Open the order
    trade = trading_service.open_order(
        db,
        current_user.id,
        symbol=order.symbol,
        order_type=order.order_type,
        lot_size=order.lot_size,
        price=order.price,
        stop_loss=order.stop_loss,
        take_profit=order.take_profit,
        connection_id=order.connection_id,
    )
    return trade


@router.put("/orders/{order_id}/close", response_model=TradeOut)
def close_order(order_id: str, payload: OrderClose, db: Session = Depends(deps.get_db), current_user=Depends(deps.get_current_user)):
    trade = trading_service.close_order(db, current_user.id, order_id, payload.close_price)
    if not trade:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return trade


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
    """
    from datetime import datetime
    
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
    
    # Mock balance (in real app, this comes from broker connection)
    base_balance = 10000.0
    current_balance = base_balance + total_realized_pnl
    current_equity = current_balance + total_unrealized_pnl
    
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
