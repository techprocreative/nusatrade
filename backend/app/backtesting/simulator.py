"""Trade simulation with realistic market conditions."""

import random
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class SimulationConfig:
    """Configuration for trade simulation."""
    
    # Slippage settings
    slippage_mode: str = "fixed"  # "fixed", "random", "volatility_based"
    slippage_pips: float = 0.5
    max_slippage_pips: float = 3.0
    
    # Spread settings
    spread_mode: str = "fixed"  # "fixed", "variable"
    base_spread_pips: float = 1.0
    max_spread_pips: float = 5.0
    
    # Commission
    commission_per_lot: float = 7.0  # USD per lot
    
    # Execution
    partial_fill_probability: float = 0.0  # 0 = always full fill
    rejection_probability: float = 0.0  # 0 = never reject


class TradeSimulator:
    """Simulates realistic trade execution conditions."""

    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()

    def calculate_slippage(
        self,
        order_type: str,
        volatility: Optional[float] = None,
    ) -> float:
        """Calculate slippage in price units (pips * 0.0001)."""
        if self.config.slippage_mode == "fixed":
            slippage_pips = self.config.slippage_pips
        elif self.config.slippage_mode == "random":
            slippage_pips = random.uniform(0, self.config.max_slippage_pips)
        elif self.config.slippage_mode == "volatility_based":
            base = self.config.slippage_pips
            vol_factor = volatility if volatility else 1.0
            slippage_pips = min(base * vol_factor, self.config.max_slippage_pips)
        else:
            slippage_pips = self.config.slippage_pips

        # Slippage is always against the trader
        price_slippage = slippage_pips * 0.0001
        return price_slippage if order_type.upper() == "BUY" else -price_slippage

    def calculate_spread(self, volatility: Optional[float] = None) -> float:
        """Calculate spread in price units."""
        if self.config.spread_mode == "fixed":
            spread_pips = self.config.base_spread_pips
        elif self.config.spread_mode == "variable":
            # Widen spread based on volatility
            vol_factor = volatility if volatility else 1.0
            spread_pips = min(
                self.config.base_spread_pips * vol_factor,
                self.config.max_spread_pips
            )
        else:
            spread_pips = self.config.base_spread_pips

        return spread_pips * 0.0001

    def calculate_fill_price(
        self,
        order_type: str,
        requested_price: float,
        volatility: Optional[float] = None,
    ) -> Dict:
        """Calculate the actual fill price with slippage and spread."""
        slippage = self.calculate_slippage(order_type, volatility)
        spread = self.calculate_spread(volatility)

        if order_type.upper() == "BUY":
            # Buy at ask (bid + spread) + slippage
            fill_price = requested_price + spread + slippage
        else:
            # Sell at bid - slippage
            fill_price = requested_price + slippage

        return {
            "fill_price": fill_price,
            "slippage": abs(slippage),
            "spread": spread,
            "requested_price": requested_price,
        }

    def calculate_commission(self, lot_size: float) -> float:
        """Calculate commission for a trade."""
        return self.config.commission_per_lot * lot_size

    def should_reject_order(self) -> bool:
        """Determine if order should be rejected (slippage too high, etc)."""
        if self.config.rejection_probability > 0:
            return random.random() < self.config.rejection_probability
        return False

    def simulate_execution(
        self,
        order_type: str,
        requested_price: float,
        lot_size: float,
        volatility: Optional[float] = None,
    ) -> Dict:
        """Simulate full order execution."""
        if self.should_reject_order():
            return {
                "success": False,
                "reason": "Order rejected - market conditions",
            }

        fill_info = self.calculate_fill_price(order_type, requested_price, volatility)
        commission = self.calculate_commission(lot_size)

        return {
            "success": True,
            "fill_price": fill_info["fill_price"],
            "slippage": fill_info["slippage"],
            "spread": fill_info["spread"],
            "commission": commission,
            "lot_size": lot_size,
        }
