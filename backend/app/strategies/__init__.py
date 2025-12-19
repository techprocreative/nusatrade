"""
Trading Strategies Module

This module contains pre-built trading strategies that can be used
with the auto-trading system.
"""

from .ml_profitable_strategy import (
    MLProfitableStrategy,
    create_default_ml_strategy,
    get_default_strategy_config,
)

from .ml_scalping_strategy import (
    MLScalpingStrategy,
    create_scalping_strategy,
    get_scalping_strategy_config,
)

__all__ = [
    # H1 Strategy (75% win rate, conservative)
    "MLProfitableStrategy",
    "create_default_ml_strategy",
    "get_default_strategy_config",
    # M15 Scalping Strategy (58% win rate, active)
    "MLScalpingStrategy",
    "create_scalping_strategy",
    "get_scalping_strategy_config",
]
