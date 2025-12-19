"""Prediction Service - Unified ML prediction with strategy validation.

This service combines:
1. Trained ML model predictions
2. Strategy rule validation
3. Risk management (SL/TP) calculation

Ensuring trades are only executed when ML and strategy rules align.
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4
from dataclasses import dataclass, asdict
from threading import Lock

import pandas as pd
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.ml import MLModel, MLPrediction
from app.models.strategy import Strategy
from app.ml.features import FeatureEngineer
from app.ml.training import Trainer
from app.services.strategy_rule_engine import StrategyRuleEngine, StrategyValidationResult
from app.services.risk_management import (
    calculate_sl_tp,
    calculate_atr_from_dataframe,
    get_risk_config,
    RiskConfig,
    SLType,
    TPType,
)
from app.services.market_data import MarketDataFetcher, get_default_price


logger = get_logger(__name__)


@dataclass
class PredictionResult:
    """Result of ML prediction with strategy validation."""
    direction: str  # BUY, SELL, or HOLD
    confidence: float
    ml_signal: str  # Original ML prediction before strategy filter
    strategy_validation: Dict[str, Any]
    should_trade: bool
    entry_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    risk_reward_ratio: Optional[float]
    current_indicators: Dict[str, float]
    strategy_rules: Optional[Dict[str, List[str]]]
    trailing_stop: Optional[Dict[str, Any]]
    generated_by: str  # "ml_model" or "fallback"
    model_type: str
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PredictionService:
    """Unified prediction service combining ML + Strategy validation."""

    def __init__(self, db: Session):
        self.db = db
        self.rule_engine = StrategyRuleEngine()
        self.feature_engineer = FeatureEngineer()
        self._model_cache: Dict[str, Trainer] = {}
        self._cache_lock = Lock()  # Thread-safe cache access
    
    def generate_prediction(
        self,
        model: MLModel,
        symbol: str,
        use_strategy_rules: bool = True,
        save_to_db: bool = True,
    ) -> PredictionResult:
        """
        Generate prediction using trained ML model with strategy validation.
        
        Args:
            model: MLModel instance
            symbol: Trading symbol (e.g., "EURUSD")
            use_strategy_rules: Whether to validate against linked strategy rules
            save_to_db: Whether to save prediction to database
            
        Returns:
            PredictionResult with full prediction data
        """
        symbol = symbol.upper()
        timeframe = model.timeframe or "H1"
        
        # Step 1: Fetch market data
        market_data = MarketDataFetcher.fetch_data(symbol, timeframe, bars=200)
        
        if market_data is None or len(market_data) < 50:
            logger.error(f"Insufficient market data for {symbol}")
            return self._create_fallback_prediction(model, symbol, "Insufficient market data")
        
        # Step 2: Build features
        featured_data = self.feature_engineer.build_features(market_data)
        
        # Step 3: Get ML prediction
        ml_result = self._get_ml_prediction(model, featured_data)
        
        # Step 4: Get current price
        entry_price = MarketDataFetcher.get_current_price(symbol)
        if entry_price is None:
            entry_price = float(featured_data["close"].iloc[-1])
        
        # Step 5: Load strategy and validate rules
        strategy = None
        strategy_validation = {
            "valid": True,
            "matched_rules": [],
            "failed_rules": [],
            "message": "No strategy linked",
            "current_indicators": {}
        }
        strategy_rules = None
        
        if use_strategy_rules and model.strategy_id:
            strategy = self.db.query(Strategy).filter(Strategy.id == model.strategy_id).first()
            
            if strategy:
                # Extract strategy rules for display
                entry_rules_display = []
                exit_rules_display = []
                
                if strategy.entry_rules:
                    entry_rules_display = [
                        r.get("description", r.get("condition", ""))
                        for r in strategy.entry_rules
                    ]
                if strategy.exit_rules:
                    exit_rules_display = [
                        r.get("description", r.get("condition", ""))
                        for r in strategy.exit_rules
                    ]
                
                if entry_rules_display or exit_rules_display:
                    strategy_rules = {
                        "entry_rules": entry_rules_display,
                        "exit_rules": exit_rules_display
                    }
                
                # Validate entry rules if ML signal is not HOLD
                if ml_result["direction"] != "HOLD" and strategy.entry_rules:
                    validation_result = self.rule_engine.evaluate_entry_rules(
                        rules=strategy.entry_rules,
                        market_data=featured_data,
                        ml_direction=ml_result["direction"]
                    )
                    
                    strategy_validation = {
                        "valid": validation_result.valid,
                        "matched_rules": validation_result.matched_rules,
                        "failed_rules": validation_result.failed_rules,
                        "message": validation_result.message,
                        "current_indicators": validation_result.current_indicators,
                    }
        
        # Step 6: Determine final direction
        final_direction = ml_result["direction"]
        should_trade = True
        
        if not strategy_validation["valid"] and ml_result["direction"] != "HOLD":
            final_direction = "HOLD"
            should_trade = False
            logger.info(
                f"ML signal {ml_result['direction']} blocked by strategy rules. "
                f"Failed: {strategy_validation['failed_rules']}"
            )
        
        # Step 7: Calculate SL/TP using strategy risk management
        stop_loss = None
        take_profit = None
        risk_reward_ratio = None
        trailing_stop_config = None
        
        if final_direction != "HOLD":
            # Check if this is a scalping model with fixed pip TP/SL
            model_config = model.config or {}
            if model_config.get("strategy_type") == "ml_scalping":
                # Use fixed pips from model config
                tp_pips = model_config.get("tp_pips", 5.0)
                sl_pips = model_config.get("sl_pips", 8.0)
                pip_value = 0.1  # XAUUSD pip = $0.10
                
                if final_direction == "BUY":
                    stop_loss = entry_price - (sl_pips * pip_value)
                    take_profit = entry_price + (tp_pips * pip_value)
                else:  # SELL
                    stop_loss = entry_price + (sl_pips * pip_value)
                    take_profit = entry_price - (tp_pips * pip_value)
                
                risk_reward_ratio = tp_pips / sl_pips
            else:
                # Standard ATR-based calculation
                risk_config = self._get_risk_config(strategy, model)
                atr = calculate_atr_from_dataframe(featured_data, period=14)
                
                stop_loss, take_profit = calculate_sl_tp(
                    entry_price=entry_price,
                    direction=final_direction,
                    config=risk_config,
                    atr=atr,
                )
                
                # Calculate risk/reward ratio
                if stop_loss and take_profit and stop_loss != entry_price:
                    risk_reward_ratio = round(
                        abs(take_profit - entry_price) / abs(entry_price - stop_loss), 2
                    )
            
            # Get trailing stop config from strategy
            trailing_stop_config = self._get_trailing_stop_config(strategy)
        
        # Step 8: Get current indicators for display
        current_indicators = strategy_validation.get("current_indicators", {})
        if not current_indicators:
            current_indicators = self.rule_engine._get_current_indicators(featured_data)
        
        # Create result
        result = PredictionResult(
            direction=final_direction,
            confidence=ml_result["confidence"],
            ml_signal=ml_result["direction"],
            strategy_validation=strategy_validation,
            should_trade=should_trade,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=risk_reward_ratio,
            current_indicators=current_indicators,
            strategy_rules=strategy_rules,
            trailing_stop=trailing_stop_config,
            generated_by=ml_result.get("generated_by", "ml_model"),
            model_type=model.model_type or "unknown",
            timestamp=datetime.utcnow().isoformat(),
        )
        
        # Step 9: Save to database
        if save_to_db:
            self._save_prediction(model.id, symbol, result)
        
        return result
    
    def _get_ml_prediction(
        self,
        model: MLModel,
        featured_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Get prediction from trained ML model with thread-safe cache."""

        # Check if model is trained
        if not model.file_path or not os.path.exists(model.file_path):
            logger.warning(f"Model {model.name} not trained or file not found")
            return {
                "direction": "HOLD",
                "confidence": 0.0,
                "generated_by": "fallback",
                "probabilities": {}
            }

        # Check if this is a scalping model (uses different loading/prediction)
        model_config = model.config or {}
        strategy_type = model_config.get("strategy_type", "")
        
        if strategy_type == "ml_scalping" or "scalping" in model.file_path.lower():
            return self._get_scalping_prediction(model, featured_data)
        
        # Standard ML model loading (with thread-safe caching)
        model_id = str(model.id)

        with self._cache_lock:
            if model_id not in self._model_cache:
                try:
                    trainer = Trainer()
                    trainer.load_model(model.file_path)
                    self._model_cache[model_id] = trainer
                    logger.info(f"Loaded ML model: {model.name}")
                except Exception as e:
                    logger.error(f"Failed to load model {model.name}: {e}")
                    return {
                        "direction": "HOLD",
                        "confidence": 0.0,
                        "generated_by": "fallback",
                        "probabilities": {}
                    }

            trainer = self._model_cache[model_id]

        # Get last row for prediction
        last_row = featured_data.iloc[[-1]]

        try:
            prediction_result = trainer.predict(last_row)

            return {
                "direction": prediction_result.get("direction", "HOLD"),
                "confidence": prediction_result.get("confidence", 0.5),
                "generated_by": "ml_model",
                "probabilities": prediction_result.get("probabilities", {})
            }
        except Exception as e:
            logger.error(f"ML prediction failed for {model.name}: {e}")
            return {
                "direction": "HOLD",
                "confidence": 0.0,
                "generated_by": "fallback",
                "probabilities": {}
            }
    
    def _get_scalping_prediction(
        self,
        model: MLModel,
        featured_data: pd.DataFrame
    ) -> Dict[str, Any]:
        """Get prediction from scalping model (LightGBM/XGBoost with custom features)."""
        import pickle
        import numpy as np
        
        try:
            # Load the scalping model (it's a dict with model, scaler, features)
            model_id = str(model.id)
            
            with self._cache_lock:
                if model_id not in self._model_cache:
                    with open(model.file_path, 'rb') as f:
                        model_data = pickle.load(f)
                    self._model_cache[model_id] = model_data
                    logger.info(f"Loaded scalping model: {model.name}")
                
                model_data = self._model_cache[model_id]
            
            # Get model components
            ml_model = model_data.get('model')
            scaler = model_data.get('scaler')
            feature_columns = model_data.get('feature_columns', [])
            
            if ml_model is None:
                return {"direction": "HOLD", "confidence": 0.0, "generated_by": "fallback"}
            
            # Create scalping-specific features
            df = self._create_scalping_features(featured_data.copy())
            
            if len(df) == 0:
                return {"direction": "HOLD", "confidence": 0.0, "generated_by": "fallback"}
            
            # Get features that exist in data
            available_features = [c for c in feature_columns if c in df.columns]
            
            if len(available_features) < len(feature_columns) * 0.5:
                logger.warning(f"Not enough scalping features: {len(available_features)}/{len(feature_columns)}")
                return {"direction": "HOLD", "confidence": 0.0, "generated_by": "missing_features"}
            
            # Get last row
            X = df[available_features].iloc[-1:].values
            
            # Scale features
            if scaler is not None:
                X = scaler.transform(X)
            
            X = np.nan_to_num(X)
            
            # Predict
            proba = ml_model.predict_proba(X)[0]
            pred_class = np.argmax(proba)
            confidence = float(proba[pred_class])
            
            # Map classes
            signal_map = {0: "HOLD", 1: "BUY", 2: "SELL"}
            direction = signal_map.get(pred_class, "HOLD")
            
            # Check confidence threshold from model config
            model_config = model.config or {}
            threshold = model_config.get("confidence_threshold", 0.55)
            
            if confidence < threshold:
                logger.debug(f"Scalping confidence {confidence:.2%} below threshold {threshold:.2%}")
                return {
                    "direction": "HOLD",
                    "confidence": confidence,
                    "generated_by": "ml_scalping",
                    "original_signal": direction,
                    "reason": "low_confidence",
                }
            
            logger.info(f"🎯 Scalping signal: {direction} @ {confidence:.1%}")
            
            return {
                "direction": direction,
                "confidence": confidence,
                "generated_by": "ml_scalping",
                "probabilities": {signal_map[i]: float(proba[i]) for i in range(len(proba))},
            }
            
        except Exception as e:
            logger.error(f"Scalping prediction failed: {e}")
            return {"direction": "HOLD", "confidence": 0.0, "generated_by": "fallback"}
    
    def _create_scalping_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create features for scalping model prediction."""
        import numpy as np
        
        # Normalize column names
        df.columns = [c.lower() for c in df.columns]
        
        # EMAs
        for p in [10, 20, 50, 100]:
            df[f'ema_{p}'] = df['close'].ewm(span=p).mean()
        
        # Trend
        df['trend_score'] = (
            (df['ema_10'] > df['ema_20']).astype(int) +
            (df['ema_20'] > df['ema_50']).astype(int) +
            (df['ema_50'] > df['ema_100']).astype(int)
        )
        df['strong_uptrend'] = (df['trend_score'] >= 2).astype(int)
        df['strong_downtrend'] = (df['trend_score'] <= 1).astype(int)
        df['dist_ema_20'] = (df['close'] - df['ema_20']) / df['ema_20']
        
        # RSI
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(14).mean()
        avg_loss = loss.rolling(14).mean()
        rs = avg_gain / (avg_loss + 1e-8)
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi_oversold'] = (df['rsi'] < 30).astype(int)
        df['rsi_overbought'] = (df['rsi'] > 70).astype(int)
        
        # MACD
        ema_12 = df['close'].ewm(span=12).mean()
        ema_26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_bull'] = (df['macd'] > df['macd_signal']).astype(int)
        
        # Stochastic
        low_min = df['low'].rolling(14).min()
        high_max = df['high'].rolling(14).max()
        df['stoch'] = 100 * (df['close'] - low_min) / (high_max - low_min + 1e-8)
        df['stoch_oversold'] = (df['stoch'] < 20).astype(int)
        df['stoch_overbought'] = (df['stoch'] > 80).astype(int)
        
        # ATR
        df['tr'] = np.maximum(
            df['high'] - df['low'],
            np.maximum(
                abs(df['high'] - df['close'].shift(1)),
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(14).mean()
        df['atr_norm'] = df['atr'] / df['close']
        df['vol_ratio'] = df['atr'] / (df['atr'].rolling(50).mean() + 1e-8)
        
        # Candles
        df['bullish'] = (df['close'] > df['open']).astype(int)
        df['body'] = abs(df['close'] - df['open']) / (df['high'] - df['low'] + 1e-8)
        
        # Returns
        df['ret_1'] = df['close'].pct_change(1)
        df['ret_3'] = df['close'].pct_change(3)
        df['ret_5'] = df['close'].pct_change(5)
        
        # Time (from timestamp or default)
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
        
        return df.dropna()
    
    def _get_risk_config(
        self,
        strategy: Optional[Strategy],
        model: MLModel
    ) -> RiskConfig:
        """Get risk configuration from strategy or default."""
        
        if strategy and strategy.risk_management:
            rm = strategy.risk_management
            return RiskConfig(
                sl_type=SLType(rm.get("stop_loss_type", "atr_based")),
                sl_value=rm.get("stop_loss_value", 2.0),
                tp_type=TPType(rm.get("take_profit_type", "risk_reward")),
                tp_value=rm.get("take_profit_value", 2.0),
                risk_per_trade_percent=rm.get("risk_per_trade_percent", 2.0),
                max_position_size=rm.get("max_position_size", 0.1),
            )
        
        # Use model config if available
        if model.config and model.config.get("risk_profile"):
            return get_risk_config(model.config["risk_profile"])
        
        # Default moderate config
        return get_risk_config("moderate")
    
    def _get_trailing_stop_config(self, strategy: Optional[Strategy]) -> Optional[Dict[str, Any]]:
        """Get trailing stop configuration from strategy."""
        
        if strategy and strategy.risk_management:
            ts = strategy.risk_management.get("trailing_stop")
            if ts:
                return {
                    "enabled": ts.get("enabled", True),
                    "activation_pips": ts.get("activation_pips", 20),
                    "trail_distance_pips": ts.get("trail_distance_pips", 15),
                    "breakeven_pips": ts.get("breakeven_pips", 15),
                }
        
        # Default trailing stop config
        return {
            "enabled": True,
            "activation_pips": 20,
            "trail_distance_pips": 15,
            "breakeven_pips": 15,
        }
    
    def _save_prediction(
        self,
        model_id,
        symbol: str,
        result: PredictionResult
    ) -> MLPrediction:
        """Save prediction to database."""
        
        prediction = MLPrediction(
            id=uuid4(),
            model_id=model_id,
            symbol=symbol,
            prediction=result.to_dict(),
            created_at=datetime.utcnow(),
        )
        
        self.db.add(prediction)
        self.db.commit()
        
        return prediction
    
    def _create_fallback_prediction(
        self,
        model: MLModel,
        symbol: str,
        error_message: str
    ) -> PredictionResult:
        """Create a fallback prediction when normal prediction fails."""
        entry_price = get_default_price(symbol)
        
        return PredictionResult(
            direction="HOLD",
            confidence=0.0,
            ml_signal="HOLD",
            strategy_validation={
                "valid": False,
                "matched_rules": [],
                "failed_rules": [],
                "message": error_message,
                "current_indicators": {}
            },
            should_trade=False,
            entry_price=entry_price,
            stop_loss=None,
            take_profit=None,
            risk_reward_ratio=None,
            current_indicators={},
            strategy_rules=None,
            trailing_stop=None,
            generated_by="fallback",
            model_type=model.model_type or "unknown",
            timestamp=datetime.utcnow().isoformat(),
        )
    
    def clear_model_cache(self):
        """Clear the ML model cache (thread-safe)."""
        with self._cache_lock:
            self._model_cache.clear()
