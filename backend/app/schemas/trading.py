from datetime import datetime
from decimal import Decimal
from typing import Optional
import uuid

from pydantic import BaseModel, Field, field_serializer, ConfigDict


class OrderCreate(BaseModel):
    symbol: str
    order_type: str = Field(..., pattern="^(BUY|SELL)$")
    lot_size: float
    price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    connection_id: Optional[str] = None


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
