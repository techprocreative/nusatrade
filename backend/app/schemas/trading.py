from datetime import datetime
from decimal import Decimal
from typing import Optional, Literal
import uuid

from pydantic import BaseModel, Field, field_serializer, ConfigDict


# Enums as Literal types for validation
SLTypeEnum = Literal["fixed_pips", "atr_based", "percentage"]
TPTypeEnum = Literal["fixed_pips", "risk_reward", "atr_based"]
TrailingTypeEnum = Literal["fixed_pips", "atr_based", "percentage"]


class TrailingStopSettings(BaseModel):
    """Trailing stop configuration."""
    enabled: bool = True
    trailing_type: TrailingTypeEnum = "atr_based"
    activation_pips: float = Field(default=20.0, ge=0, description="Start trailing after X pips profit")
    trail_distance_pips: float = Field(default=15.0, ge=0, description="Fixed pip distance for trailing")
    atr_multiplier: float = Field(default=1.5, ge=0, description="ATR multiplier for ATR-based trailing")
    breakeven_enabled: bool = True
    breakeven_pips: float = Field(default=15.0, ge=0, description="Move SL to breakeven after X pips profit")


class RiskManagementSettings(BaseModel):
    """Risk management configuration for trades."""
    # Stop Loss
    sl_type: SLTypeEnum = "atr_based"
    sl_value: float = Field(default=2.0, ge=0, description="Pips, ATR multiplier, or percentage")
    
    # Take Profit
    tp_type: TPTypeEnum = "risk_reward"
    tp_value: float = Field(default=2.0, ge=0, description="Pips, R:R ratio, or ATR multiplier")
    
    # Trailing Stop
    trailing_stop: Optional[TrailingStopSettings] = None
    
    # Position sizing
    risk_per_trade_percent: float = Field(default=2.0, ge=0.1, le=10, description="Risk per trade as percentage")
    max_position_size: float = Field(default=1.0, ge=0.01, le=10)


class OrderCreate(BaseModel):
    symbol: str
    order_type: str = Field(..., pattern="^(BUY|SELL)$")
    lot_size: float
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    connection_id: Optional[str] = None
    # Optional risk management overrides
    use_atr_sl: bool = Field(default=False, description="Use ATR-based stop loss")
    sl_atr_multiplier: Optional[float] = Field(default=None, ge=0, description="ATR multiplier for SL")
    tp_risk_reward: Optional[float] = Field(default=None, ge=0, description="Risk:Reward ratio for TP")
    trailing_stop: Optional[TrailingStopSettings] = None


class PositionSizeRequest(BaseModel):
    """Request to calculate position size based on risk."""
    account_balance: float = Field(..., gt=0, description="Account balance in USD")
    risk_percent: float = Field(..., gt=0, le=10, description="Risk percentage (max 10%)")
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    symbol: str = Field(..., description="Trading symbol")


class PositionSizeResponse(BaseModel):
    """Response with calculated position size."""
    lot_size: float
    risk_amount: float
    stop_loss_pips: float
    margin_required: float


class OrderClose(BaseModel):
    close_price: float


class UpdateSLRequest(BaseModel):
    """Request to update stop loss for a position."""
    new_stop_loss: float = Field(..., gt=0)


class BreakevenRequest(BaseModel):
    """Request to move stop loss to breakeven."""
    offset_pips: float = Field(default=2.0, ge=0, description="Offset from entry in pips")


class CalculateSLTPRequest(BaseModel):
    """Request to calculate SL/TP based on risk management."""
    symbol: str
    direction: str = Field(..., pattern="^(BUY|SELL)$")
    entry_price: float = Field(..., gt=0)
    sl_type: SLTypeEnum = "atr_based"
    sl_value: float = Field(default=2.0, ge=0)
    tp_type: TPTypeEnum = "risk_reward"
    tp_value: float = Field(default=2.0, ge=0)
    atr: Optional[float] = Field(default=None, ge=0, description="Current ATR value")


class CalculateSLTPResponse(BaseModel):
    """Response with calculated SL/TP values."""
    stop_loss: float
    take_profit: float
    sl_distance_pips: float
    tp_distance_pips: float
    risk_reward_ratio: float


class TradeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symbol: str
    trade_type: str
    lot_size: float | None = None
    open_price: float | None = None
    close_price: float | None = None
    profit: float | None = None
    open_time: datetime | None = None
    close_time: datetime | None = None

    @field_serializer("id")
    def serialize_id(self, v):
        return str(v)

    @field_serializer("lot_size", "open_price", "close_price", "profit")
    def serialize_decimal(self, v):
        return float(v) if v is not None else None


class PositionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symbol: str
    trade_type: str
    lot_size: float
    open_price: float
    current_price: float | None = None
    profit: float | None = None
    open_time: datetime | None = None

    @field_serializer("id")
    def serialize_id(self, v):
        return str(v)

    @field_serializer("lot_size", "open_price", "current_price", "profit")
    def serialize_decimal(self, v):
        return float(v) if v is not None else None
