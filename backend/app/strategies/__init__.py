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

__all__ = [
    "MLProfitableStrategy",
    "create_default_ml_strategy",
    "get_default_strategy_config",
]
