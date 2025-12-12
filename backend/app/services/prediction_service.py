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
        """Get prediction from trained ML model."""
        
        # Check if model is trained
        if not model.file_path or not os.path.exists(model.file_path):
            logger.warning(f"Model {model.name} not trained or file not found")
            return {
                "direction": "HOLD",
                "confidence": 0.0,
                "generated_by": "fallback",
                "probabilities": {}
            }
        
        # Load model (with caching)
        model_id = str(model.id)
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
        """Clear the ML model cache."""
        self._model_cache.clear()
