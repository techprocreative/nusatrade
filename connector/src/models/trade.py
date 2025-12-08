from dataclasses import dataclass


@dataclass
class Trade:
    id: str
    symbol: str
    order_type: str
    lot_size: float
    stop_loss: float | None = None
    take_profit: float | None = None
