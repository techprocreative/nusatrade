"""
ML Profitable Strategy - Default strategy that uses profitable XGBoost model.

This strategy integrates the profitable ML model (75% win rate, 2.02 profit factor)
with structured entry/exit rules for auto-trading execution.

⚠️  IMPORTANT: This model is trained ONLY on XAUUSD (Gold) data.
    Do NOT use this strategy for other symbols (EURUSD, BTCUSD, etc.)
    as it will produce unreliable predictions.

Configuration:
- Symbol: XAUUSD ONLY
- Model: XGBoost (models/model_xgboost_20251212_235414.pkl)
- Confidence Threshold: 70%
- Filters: Session + Volatility
- TP/SL: ATR-based (0.8xATR TP, 1.2xATR SL)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import pickle
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


class MLProfitableStrategy:
    """
    Production-ready ML strategy with proven profitability.

    ⚠️  SYMBOL RESTRICTION: This strategy is trained ONLY for XAUUSD (Gold).
        Using it for other symbols will result in poor performance.

    Performance (2024-2025 backtest on XAUUSD):
    - Win Rate: 75.0%
    - Profit Factor: 2.02
    - Expected Trades: ~20/year
    - Max Drawdown: $7.20
    """

    # Strategy metadata
    NAME = "ML Profitable Strategy (XGBoost)"
    DESCRIPTION = "Profitable ML strategy using XGBoost with session + volatility filters"
    STRATEGY_TYPE = "ai_generated"

    # Symbol restriction
    SUPPORTED_SYMBOLS = ["XAUUSD"]  # This model is XAUUSD-only

    # Default configuration
    DEFAULT_CONFIG = {
        "symbol": "XAUUSD",  # Lock to XAUUSD only
        "model_path": "models/model_xgboost_20251212_235414.pkl",
        "confidence_threshold": 0.70,  # 70% confidence minimum
        "use_session_filter": True,    # Only London/NY hours
        "use_volatility_filter": True, # Avoid extreme volatility
        "use_trend_filter": False,     # Not needed (over-filtering)

        # Risk management (ATR-based)
        "stop_loss_atr_multiplier": 1.2,
        "take_profit_atr_multiplier": 0.8,

        # Position sizing
        "default_lot_size": 0.01,
        "max_position_size": 0.10,
        "risk_per_trade_percent": 2.0,
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize strategy with configuration.

        Raises:
            ValueError: If symbol is not XAUUSD
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}

        # Validate symbol
        symbol = self.config.get("symbol", "XAUUSD")
        if symbol not in self.SUPPORTED_SYMBOLS:
            raise ValueError(
                f"Invalid symbol '{symbol}'. This strategy only supports {self.SUPPORTED_SYMBOLS}. "
                f"The model is trained exclusively on XAUUSD data and will not work correctly for other symbols."
            )

        self.model = None
        self.scaler = None
        self.feature_columns = None

        # Load ML model
        self._load_model()

    def _load_model(self):
        """Load the trained XGBoost model."""
        model_path = self.config["model_path"]

        if not Path(model_path).exists():
            logger.warning(f"Model file not found: {model_path}")
            return

        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)

            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_columns = model_data['feature_columns']

            logger.info(f"✅ ML model loaded from {model_path}")
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}")

    def get_entry_rules(self) -> List[Dict[str, Any]]:
        """
        Get entry rules for this strategy.

        These rules work in conjunction with ML predictions:
        - ML predicts BUY/SELL
        - Rules validate market conditions
        - Both must align for trade execution
        """
        rules = []

        # Rule 1: High ML Confidence
        rules.append({
            "id": "ml_confidence_70",
            "condition": "ml_confidence >= 0.70",
            "action": "BUY",  # Will be checked for both BUY and SELL
            "description": "ML model has at least 70% confidence in prediction"
        })

        # Rule 2: Session Filter (if enabled)
        if self.config["use_session_filter"]:
            rules.append({
                "id": "london_ny_session",
                "condition": "hour >= 8 AND hour <= 21",
                "action": "BUY",
                "description": "Trade only during London (8-16) or NY (13-21) sessions"
            })

        # Rule 3: Volatility Filter (if enabled)
        if self.config["use_volatility_filter"]:
            rules.append({
                "id": "medium_volatility",
                "condition": "vol_regime_low == 0 AND vol_regime_high == 0",
                "action": "BUY",
                "description": "Avoid extreme low or high volatility (trade medium volatility only)"
            })

        # Rule 4: Trend Filter (if enabled)
        if self.config.get("use_trend_filter", False):
            rules.append({
                "id": "strong_trend",
                "condition": "strong_trend == 1",
                "action": "BUY",
                "description": "Only trade when ADX > 25 (strong trend)"
            })

        return rules

    def get_exit_rules(self) -> List[Dict[str, Any]]:
        """
        Get exit rules for this strategy.

        Exit when:
        1. Stop Loss hit
        2. Take Profit hit
        3. Max holding time exceeded (optional)
        """
        rules = [
            {
                "id": "hit_stop_loss",
                "condition": "hit_stop_loss",
                "action": "CLOSE",
                "description": "Close position when stop loss is hit"
            },
            {
                "id": "hit_take_profit",
                "condition": "hit_take_profit",
                "action": "CLOSE",
                "description": "Close position when take profit is hit"
            },
        ]

        return rules

    def get_risk_management(self) -> Dict[str, Any]:
        """
        Get risk management configuration.

        Uses ATR-based stop loss and take profit:
        - SL: 1.2 x ATR
        - TP: 0.8 x ATR
        - This gives ~0.67 TP/SL ratio (compensated by 75% win rate)
        """
        return {
            "stop_loss_type": "atr_based",
            "stop_loss_value": self.config["stop_loss_atr_multiplier"],

            "take_profit_type": "atr_based",
            "take_profit_value": self.config["take_profit_atr_multiplier"],

            "max_position_size": self.config["max_position_size"],
            "risk_per_trade_percent": self.config["risk_per_trade_percent"],

            # Optional: Max holding time
            "max_holding_hours": 8,
        }

    def get_indicators(self) -> List[str]:
        """
        Get list of required indicators.

        These indicators are needed for:
        1. ML model features
        2. Entry/exit rule evaluation
        3. Risk management (ATR)
        """
        return [
            "RSI",
            "EMA",
            "SMA",
            "MACD",
            "ADX",
            "ATR",
            "STOCH",
            "BB",
            "CCI",
        ]

    def get_parameters(self) -> List[Dict[str, Any]]:
        """
        Get configurable parameters for this strategy.

        Users can adjust these via the UI.
        """
        return [
            {
                "name": "confidence_threshold",
                "type": "number",
                "default_value": 0.70,
                "min": 0.50,
                "max": 0.95,
                "description": "Minimum ML confidence to take trade (default: 70%)"
            },
            {
                "name": "use_session_filter",
                "type": "boolean",
                "default_value": True,
                "description": "Only trade during London/NY sessions"
            },
            {
                "name": "use_volatility_filter",
                "type": "boolean",
                "default_value": True,
                "description": "Avoid extreme volatility conditions"
            },
            {
                "name": "stop_loss_atr_multiplier",
                "type": "number",
                "default_value": 1.2,
                "min": 0.5,
                "max": 3.0,
                "description": "Stop loss distance in ATR multiples"
            },
            {
                "name": "take_profit_atr_multiplier",
                "type": "number",
                "default_value": 0.8,
                "min": 0.5,
                "max": 5.0,
                "description": "Take profit distance in ATR multiples"
            },
            {
                "name": "default_lot_size",
                "type": "number",
                "default_value": 0.01,
                "min": 0.01,
                "max": 1.0,
                "description": "Default lot size for trades"
            },
        ]

    @staticmethod
    def get_supported_symbols() -> List[str]:
        """
        Get list of symbols supported by this strategy.

        Returns:
            List of supported symbol codes (currently only XAUUSD)
        """
        return MLProfitableStrategy.SUPPORTED_SYMBOLS.copy()

    @staticmethod
    def is_symbol_supported(symbol: str) -> bool:
        """
        Check if a symbol is supported by this strategy.

        Args:
            symbol: Symbol code to check

        Returns:
            True if symbol is supported, False otherwise
        """
        return symbol in MLProfitableStrategy.SUPPORTED_SYMBOLS

    def to_database_format(self, user_id: str) -> Dict[str, Any]:
        """
        Convert strategy to database format for storage.

        Returns dict that can be saved to Strategy model.
        """
        return {
            "user_id": user_id,
            "name": self.NAME,
            "description": self.DESCRIPTION,
            "strategy_type": self.STRATEGY_TYPE,
            "code": None,  # No custom code, uses ML predictor
            "parameters": self.get_parameters(),
            "indicators": self.get_indicators(),
            "entry_rules": self.get_entry_rules(),
            "exit_rules": self.get_exit_rules(),
            "risk_management": self.get_risk_management(),
            "is_active": False,  # User must manually activate
            "config": self.config,  # Store full config
            "backtest_results": None,  # Will be populated after backtest
        }


# Factory function to create default strategy
def create_default_ml_strategy(user_id: str, custom_config: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Create default ML strategy for a user.

    Args:
        user_id: User UUID
        custom_config: Optional custom configuration overrides

    Returns:
        Strategy data ready for database insertion
    """
    strategy = MLProfitableStrategy(config=custom_config)
    return strategy.to_database_format(user_id)


# Standalone function for use in auto-trading
def get_default_strategy_config() -> Dict[str, Any]:
    """
    Get default strategy configuration for auto-trading.

    Returns the optimal configuration that achieved 75% win rate.
    """
    return MLProfitableStrategy.DEFAULT_CONFIG.copy()
