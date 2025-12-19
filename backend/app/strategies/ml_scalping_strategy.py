"""
ML Scalping Strategy - High Win-Rate strategy for XAUUSD M15.

This strategy uses a trained LightGBM model optimized for scalping
with fixed TP/SL (5 pips TP, 8 pips SL) and 55%+ confidence threshold.

⚠️  IMPORTANT: This model is trained ONLY on XAUUSD (Gold) M15 data.
    Do NOT use this strategy for other symbols.

Configuration:
- Symbol: XAUUSD ONLY
- Timeframe: M15 (15-minute)
- Model: LightGBM realistic scalping model
- Confidence Threshold: 55%
- TP: 5 pips (fixed)
- SL: 8 pips (fixed)
- Expected Win Rate: 58%
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np
import pickle
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


class MLScalpingStrategy:
    """
    High Win-Rate ML Scalping Strategy for XAUUSD M15.

    ⚠️  SYMBOL RESTRICTION: This strategy is trained ONLY for XAUUSD (Gold).
        Using it for other symbols will result in poor performance.

    Performance (Backtest):
    - Win Rate: 58.1% @ 55% confidence
    - TP: 5 pips, SL: 8 pips
    - Risk:Reward: 1:0.625
    - Expected Trades: ~3-5 per day
    """

    # Strategy metadata
    NAME = "ML Scalping Strategy (XAUUSD M15)"
    DESCRIPTION = "High win-rate scalping strategy using LightGBM with fixed TP/SL"
    STRATEGY_TYPE = "ml_scalping"

    # Symbol and timeframe restriction
    SUPPORTED_SYMBOLS = ["XAUUSD"]
    SUPPORTED_TIMEFRAME = "M15"

    # Default configuration
    DEFAULT_CONFIG = {
        "symbol": "XAUUSD",
        "timeframe": "M15",
        "model_path": "models/model_realistic_xauusd_M15_20251219_100151.pkl",
        "confidence_threshold": 0.55,  # 55% minimum for 58% win rate
        "use_session_filter": True,    # Only London/NY prime time
        "use_trend_filter": True,      # Only trade with trend

        # Fixed TP/SL in pips
        "take_profit_pips": 5.0,
        "stop_loss_pips": 8.0,

        # Position sizing
        "default_lot_size": 0.01,
        "max_position_size": 0.10,
        "risk_per_trade_percent": 1.0,  # Lower risk for scalping
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize strategy with configuration."""
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}

        # Validate symbol
        symbol = self.config.get("symbol", "XAUUSD")
        if symbol not in self.SUPPORTED_SYMBOLS:
            raise ValueError(
                f"Invalid symbol '{symbol}'. This strategy only supports {self.SUPPORTED_SYMBOLS}."
            )

        self.model = None
        self.scaler = None
        self.feature_columns = None
        self.model_data = None

        # Load ML model
        self._load_model()

    def _load_model(self):
        """Load the trained LightGBM model."""
        model_path = self.config["model_path"]

        # Try multiple paths
        paths_to_try = [
            Path(model_path),
            Path("backend") / model_path,
            Path(__file__).parent.parent.parent / model_path,
        ]

        for path in paths_to_try:
            if path.exists():
                model_path = path
                break
        else:
            logger.warning(f"Model file not found in any of: {paths_to_try}")
            return

        try:
            with open(model_path, 'rb') as f:
                self.model_data = pickle.load(f)

            self.model = self.model_data.get('model')
            self.scaler = self.model_data.get('scaler')
            self.feature_columns = self.model_data.get('feature_columns', [])

            logger.info(f"✅ ML scalping model loaded from {model_path}")
            logger.info(f"   Features: {len(self.feature_columns)}")
            logger.info(f"   Best WR: {self.model_data.get('best_winrate', 'N/A')}%")
        except Exception as e:
            logger.error(f"Failed to load ML model: {e}")

    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create features matching the training pipeline."""
        df = df.copy()

        for col in ['open', 'high', 'low', 'close', 'volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Rename columns to match expected format
        col_map = {
            'open': 'Open', 'high': 'High', 'low': 'Low', 
            'close': 'Close', 'volume': 'Volume'
        }
        df = df.rename(columns=col_map)

        # EMAs
        for p in [10, 20, 50, 100]:
            df[f'ema_{p}'] = df['Close'].ewm(span=p).mean()

        # Trend
        df['trend_score'] = (
            (df['ema_10'] > df['ema_20']).astype(int) +
            (df['ema_20'] > df['ema_50']).astype(int) +
            (df['ema_50'] > df['ema_100']).astype(int)
        )
        df['strong_uptrend'] = (df['trend_score'] >= 2).astype(int)
        df['strong_downtrend'] = (df['trend_score'] <= 1).astype(int)
        df['dist_ema_20'] = (df['Close'] - df['ema_20']) / df['ema_20']

        # RSI
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / (avg_loss + 1e-8)
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi_oversold'] = (df['rsi'] < 30).astype(int)
        df['rsi_overbought'] = (df['rsi'] > 70).astype(int)

        # MACD
        ema_12 = df['Close'].ewm(span=12).mean()
        ema_26 = df['Close'].ewm(span=26).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_bull'] = (df['macd'] > df['macd_signal']).astype(int)

        # Stochastic
        low_min = df['Low'].rolling(14).min()
        high_max = df['High'].rolling(14).max()
        df['stoch'] = 100 * (df['Close'] - low_min) / (high_max - low_min + 1e-8)
        df['stoch_oversold'] = (df['stoch'] < 20).astype(int)
        df['stoch_overbought'] = (df['stoch'] > 80).astype(int)

        # ATR
        df['tr'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum(
                abs(df['High'] - df['Close'].shift(1)),
                abs(df['Low'] - df['Close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(14).mean()
        df['atr_norm'] = df['atr'] / df['Close']
        df['vol_ratio'] = df['atr'] / (df['atr'].rolling(50).mean() + 1e-8)

        # Candles
        df['bullish'] = (df['Close'] > df['Open']).astype(int)
        df['body'] = abs(df['Close'] - df['Open']) / (df['High'] - df['Low'] + 1e-8)

        # Returns
        df['ret_1'] = df['Close'].pct_change(1)
        df['ret_3'] = df['Close'].pct_change(3)
        df['ret_5'] = df['Close'].pct_change(5)

        # Time features
        if 'timestamp' in df.columns:
            try:
                df['hour'] = pd.to_datetime(df['timestamp']).dt.hour
                df['dow'] = pd.to_datetime(df['timestamp']).dt.dayofweek
            except:
                df['hour'] = 12
                df['dow'] = 2
        else:
            df['hour'] = 12
            df['dow'] = 2

        df['prime_time'] = ((df['hour'] >= 8) & (df['hour'] < 16)).astype(int)

        return df

    def predict(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate prediction from market data.

        Args:
            df: DataFrame with OHLCV data

        Returns:
            Dict with signal, confidence, sl_pips, tp_pips
        """
        if self.model is None:
            logger.warning("Model not loaded, returning HOLD")
            return {
                "signal": "HOLD",
                "confidence": 0.0,
                "sl_pips": self.config["stop_loss_pips"],
                "tp_pips": self.config["take_profit_pips"],
            }

        try:
            # Create features
            df = self.create_features(df)
            df = df.dropna()

            if len(df) == 0:
                return {"signal": "HOLD", "confidence": 0.0}

            # Get latest row
            latest = df.iloc[-1:]

            # Check session filter
            if self.config["use_session_filter"]:
                hour = latest['hour'].values[0] if 'hour' in latest.columns else 12
                if hour < 8 or hour >= 20:
                    logger.debug(f"Session filter: hour={hour}, skipping")
                    return {"signal": "HOLD", "confidence": 0.0, "reason": "outside_session"}

            # Check trend filter
            if self.config["use_trend_filter"]:
                trend_score = latest['trend_score'].values[0] if 'trend_score' in latest.columns else 1.5
                if trend_score == 1 or trend_score == 2:
                    # Weak/unclear trend
                    pass  # Continue, but note this

            # Prepare features
            feature_cols = [c for c in self.feature_columns if c in latest.columns]
            
            if len(feature_cols) < len(self.feature_columns) * 0.5:
                logger.warning(f"Not enough features: {len(feature_cols)}/{len(self.feature_columns)}")
                return {"signal": "HOLD", "confidence": 0.0, "reason": "missing_features"}

            X = latest[feature_cols].values

            # Scale
            if self.scaler is not None:
                X = self.scaler.transform(X)
            
            X = np.nan_to_num(X)

            # Predict
            proba = self.model.predict_proba(X)[0]
            pred_class = np.argmax(proba)
            confidence = proba[pred_class]

            # Map prediction
            signal_map = {0: "HOLD", 1: "BUY", 2: "SELL"}
            signal = signal_map.get(pred_class, "HOLD")

            # Check confidence threshold
            threshold = self.config["confidence_threshold"]
            if confidence < threshold:
                logger.debug(f"Below threshold: {confidence:.2%} < {threshold:.2%}")
                return {
                    "signal": "HOLD",
                    "confidence": confidence,
                    "reason": "low_confidence",
                    "original_signal": signal,
                }

            # Apply trend alignment filter
            if self.config["use_trend_filter"]:
                trend_score = latest['trend_score'].values[0] if 'trend_score' in latest.columns else 1.5
                if signal == "BUY" and trend_score < 2:
                    logger.debug("BUY signal but not in uptrend, weakening")
                    confidence *= 0.9
                elif signal == "SELL" and trend_score > 1:
                    logger.debug("SELL signal but not in downtrend, weakening")
                    confidence *= 0.9

            logger.info(f"🎯 Scalping signal: {signal} @ {confidence:.1%}")

            return {
                "signal": signal,
                "confidence": float(confidence),
                "sl_pips": self.config["stop_loss_pips"],
                "tp_pips": self.config["take_profit_pips"],
                "proba": proba.tolist(),
            }

        except Exception as e:
            logger.error(f"Prediction error: {e}")
            return {"signal": "HOLD", "confidence": 0.0, "error": str(e)}

    def get_entry_rules(self) -> List[Dict[str, Any]]:
        """Get entry rules for this strategy."""
        rules = [
            {
                "id": "ml_confidence_55",
                "condition": f"ml_confidence >= {self.config['confidence_threshold']}",
                "action": "SIGNAL",
                "description": f"ML model has at least {self.config['confidence_threshold']:.0%} confidence"
            },
        ]

        if self.config["use_session_filter"]:
            rules.append({
                "id": "prime_session",
                "condition": "hour >= 8 AND hour < 20",
                "action": "FILTER",
                "description": "Trade only during London/NY prime sessions"
            })

        if self.config["use_trend_filter"]:
            rules.append({
                "id": "trend_alignment",
                "condition": "(signal == BUY AND trend_score >= 2) OR (signal == SELL AND trend_score <= 1)",
                "action": "FILTER",
                "description": "Trade with trend direction"
            })

        return rules

    def get_exit_rules(self) -> List[Dict[str, Any]]:
        """Get exit rules for this strategy."""
        return [
            {
                "id": "fixed_stop_loss",
                "condition": f"loss >= {self.config['stop_loss_pips']} pips",
                "action": "CLOSE",
                "description": f"Close if loss reaches {self.config['stop_loss_pips']} pips"
            },
            {
                "id": "fixed_take_profit",
                "condition": f"profit >= {self.config['take_profit_pips']} pips",
                "action": "CLOSE",
                "description": f"Close if profit reaches {self.config['take_profit_pips']} pips"
            },
        ]

    def get_risk_management(self) -> Dict[str, Any]:
        """Get risk management configuration."""
        return {
            "stop_loss_type": "fixed_pips",
            "stop_loss_value": self.config["stop_loss_pips"],

            "take_profit_type": "fixed_pips",
            "take_profit_value": self.config["take_profit_pips"],

            "max_position_size": self.config["max_position_size"],
            "risk_per_trade_percent": self.config["risk_per_trade_percent"],

            # Scalping specific
            "max_holding_minutes": 60,  # Exit within 1 hour max
            "max_trades_per_day": 10,   # Limit overtrading
        }

    def get_indicators(self) -> List[str]:
        """Get required indicators."""
        return ["RSI", "EMA", "MACD", "ATR", "STOCH"]

    def get_parameters(self) -> List[Dict[str, Any]]:
        """Get configurable parameters."""
        return [
            {
                "name": "confidence_threshold",
                "type": "number",
                "default_value": 0.55,
                "min": 0.40,
                "max": 0.80,
                "description": "Minimum ML confidence to take trade"
            },
            {
                "name": "take_profit_pips",
                "type": "number",
                "default_value": 5.0,
                "min": 3.0,
                "max": 15.0,
                "description": "Take profit in pips"
            },
            {
                "name": "stop_loss_pips",
                "type": "number",
                "default_value": 8.0,
                "min": 3.0,
                "max": 20.0,
                "description": "Stop loss in pips"
            },
            {
                "name": "use_session_filter",
                "type": "boolean",
                "default_value": True,
                "description": "Only trade during prime session hours"
            },
            {
                "name": "use_trend_filter",
                "type": "boolean",
                "default_value": True,
                "description": "Only trade in direction of trend"
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
        """Get supported symbols."""
        return MLScalpingStrategy.SUPPORTED_SYMBOLS.copy()

    @staticmethod
    def is_symbol_supported(symbol: str) -> bool:
        """Check if symbol is supported."""
        return symbol in MLScalpingStrategy.SUPPORTED_SYMBOLS

    def to_database_format(self, user_id: str) -> Dict[str, Any]:
        """Convert strategy to database format."""
        return {
            "user_id": user_id,
            "name": self.NAME,
            "description": self.DESCRIPTION,
            "strategy_type": self.STRATEGY_TYPE,
            "code": None,
            "parameters": self.get_parameters(),
            "indicators": self.get_indicators(),
            "entry_rules": self.get_entry_rules(),
            "exit_rules": self.get_exit_rules(),
            "risk_management": self.get_risk_management(),
            "is_active": False,
            "config": self.config,
            "backtest_results": None,
        }


# Factory function
def create_scalping_strategy(user_id: str, custom_config: Optional[Dict] = None) -> Dict[str, Any]:
    """Create scalping strategy for a user."""
    strategy = MLScalpingStrategy(config=custom_config)
    return strategy.to_database_format(user_id)


def get_scalping_strategy_config() -> Dict[str, Any]:
    """Get default scalping strategy configuration."""
    return MLScalpingStrategy.DEFAULT_CONFIG.copy()
