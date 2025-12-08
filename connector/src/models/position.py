from dataclasses import dataclass


@dataclass
class Position:
    ticket: int
    symbol: str
    type: str
    lots: float
    open_price: float
    profit: float
