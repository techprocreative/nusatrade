"""Auto-Trading Service - Background scheduler for ML bot auto-trading.

This service handles:
1. Loading trained ML models
2. Fetching real market data
3. Generating predictions using actual models
4. Executing trades via MT5 connector
"""

import asyncio
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from uuid import uuid4

import pandas as pd
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.database import SessionLocal
from app.models.ml import MLModel, MLPrediction
from app.models.strategy import Strategy
from app.models.trade import Trade
from app.models.broker import BrokerConnection
from app.ml.training import Trainer
from app.ml.features import FeatureEngineer
from app.services.market_data import MarketDataFetcher, get_default_price

logger = get_logger(__name__)


class AutoTradingConfig:
    """Configuration for auto-trading."""
    
    # Default settings
    DEFAULT_CONFIDENCE_THRESHOLD = 0.65  # 65%
    DEFAULT_MAX_TRADES_PER_DAY = 5
    DEFAULT_COOLDOWN_MINUTES = 30
    DEFAULT_LOT_SIZE = 0.01
    
    def __init__(self):
        self.confidence_threshold = self.DEFAULT_CONFIDENCE_THRESHOLD
        self.max_trades_per_day = self.DEFAULT_MAX_TRADES_PER_DAY
        self.cooldown_minutes = self.DEFAULT_COOLDOWN_MINUTES
        self.lot_size = self.DEFAULT_LOT_SIZE
    
    @classmethod
    def from_model_config(cls, config: Optional[dict]) -> "AutoTradingConfig":
        """Create config from model's config field."""
        instance = cls()
        if config:
            instance.confidence_threshold = config.get("confidence_threshold", cls.DEFAULT_CONFIDENCE_THRESHOLD)
            instance.max_trades_per_day = config.get("max_trades_per_day", cls.DEFAULT_MAX_TRADES_PER_DAY)
            instance.cooldown_minutes = config.get("cooldown_minutes", cls.DEFAULT_COOLDOWN_MINUTES)
            instance.lot_size = config.get("lot_size", cls.DEFAULT_LOT_SIZE)
        return instance


class AutoTradingService:
    """Service for automated trading based on ML predictions."""
    
    def __init__(self):
        self._is_running = False
        self._last_run: Optional[datetime] = None
        self._loaded_models: Dict[str, Trainer] = {}  # Cache for loaded models
    
    async def run_auto_trading_cycle(self) -> Dict[str, Any]:
        """
        Main auto-trading cycle. Called by scheduler.
        Checks all active models and executes trades if conditions are met.
        """
        if self._is_running:
            logger.warning("Auto-trading cycle already running, skipping...")
            return {"status": "skipped", "reason": "already_running"}
        
        self._is_running = True
        self._last_run = datetime.utcnow()
        
        results = {
            "started_at": self._last_run.isoformat(),
            "models_checked": 0,
            "predictions_generated": 0,
            "trades_executed": 0,
            "errors": [],
        }
        
        db: Session = SessionLocal()
        
        try:
            # Get all active models with trained file_path
            active_models = db.query(MLModel).filter(
                MLModel.is_active == True,
                MLModel.file_path != None,
            ).all()
            
            results["models_checked"] = len(active_models)
            logger.info(f"Auto-trading: Checking {len(active_models)} active models")
            
            for model in active_models:
                try:
                    trade_result = await self._process_model(db, model)
                    if trade_result.get("prediction_generated"):
                        results["predictions_generated"] += 1
                    if trade_result.get("trade_executed"):
                        results["trades_executed"] += 1
                except Exception as e:
                    error_msg = f"Error processing model {model.id}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            results["completed_at"] = datetime.utcnow().isoformat()
            logger.info(f"Auto-trading cycle completed: {results}")
            
        except Exception as e:
            logger.error(f"Auto-trading cycle failed: {e}")
            results["errors"].append(str(e))
        finally:
            db.close()
            self._is_running = False
        
        return results
    
    def _load_model(self, model: MLModel) -> Optional[Trainer]:
        """Load a trained ML model."""
        model_id = str(model.id)
        
        # Check cache
        if model_id in self._loaded_models:
            return self._loaded_models[model_id]
        
        if not model.file_path:
            logger.warning(f"Model {model_id} has no trained file")
            return None
        
        try:
            import os
            if not os.path.exists(model.file_path):
                logger.warning(f"Model file not found: {model.file_path}")
                return None
            
            trainer = Trainer()
            trainer.load_model(model.file_path)
            
            # Cache for future use
            self._loaded_models[model_id] = trainer
            logger.info(f"Loaded model: {model.name} from {model.file_path}")
            
            return trainer
            
        except Exception as e:
            logger.error(f"Failed to load model {model_id}: {e}")
            return None
    
    async def _process_model(self, db: Session, model: MLModel) -> Dict[str, Any]:
        """Process a single model for auto-trading."""
        result = {
            "model_id": str(model.id),
            "model_name": model.name,
            "prediction_generated": False,
            "trade_executed": False,
            "reason": None,
        }
        
        config = AutoTradingConfig.from_model_config(model.config)
        
        # Check cooldown
        last_prediction = db.query(MLPrediction).filter(
            MLPrediction.model_id == model.id
        ).order_by(MLPrediction.created_at.desc()).first()
        
        if last_prediction:
            cooldown_until = last_prediction.created_at + timedelta(minutes=config.cooldown_minutes)
            if datetime.utcnow() < cooldown_until:
                result["reason"] = f"Cooldown until {cooldown_until.isoformat()}"
                logger.debug(f"Model {model.name} in cooldown")
                return result
        
        # Check daily trade limit
        today = date.today()
        today_predictions = db.query(MLPrediction).filter(
            MLPrediction.model_id == model.id,
            MLPrediction.created_at >= datetime.combine(today, datetime.min.time()),
        ).count()
        
        if today_predictions >= config.max_trades_per_day:
            result["reason"] = f"Max trades per day ({config.max_trades_per_day}) reached"
            logger.debug(f"Model {model.name} reached daily limit")
            return result
        
        # Generate prediction using real model
        prediction_data = await self._generate_real_prediction(db, model, config)
        
        if prediction_data is None:
            result["reason"] = "Failed to generate prediction"
            return result
        
        result["prediction_generated"] = True
        
        # Check if we should execute
        direction = prediction_data.get("direction", "HOLD")
        confidence = prediction_data.get("confidence", 0)
        
        if direction == "HOLD":
            result["reason"] = "Prediction is HOLD, no trade"
            return result
        
        if confidence < config.confidence_threshold:
            result["reason"] = f"Confidence {confidence:.2%} below threshold {config.confidence_threshold:.2%}"
            logger.info(f"Model {model.name}: {result['reason']}")
            return result
        
        # Execute trade!
        logger.info(f"Model {model.name}: Executing {direction} trade with {confidence:.2%} confidence")
        
        trade_executed = await self._execute_real_trade(db, model, prediction_data, config)
        result["trade_executed"] = trade_executed
        
        if trade_executed:
            result["reason"] = f"Trade executed: {direction} with {confidence:.2%} confidence"
        else:
            result["reason"] = "Trade execution failed"
        
        return result
    
    async def _generate_real_prediction(
        self, db: Session, model: MLModel, config: AutoTradingConfig
    ) -> Optional[Dict[str, Any]]:
        """
        Generate a prediction using trained ML model with strategy validation.
        
        Uses PredictionService for unified ML + Strategy rule evaluation.
        Only returns actionable predictions if both ML and strategy rules agree.
        """
        from app.services.prediction_service import PredictionService
        
        symbol = model.symbol or "EURUSD"
        
        try:
            # Use PredictionService for unified ML + Strategy prediction
            prediction_service = PredictionService(db)
            result = prediction_service.generate_prediction(
                model=model,
                symbol=symbol,
                use_strategy_rules=True,
                save_to_db=True,
            )
            
            # Log strategy validation result
            strategy_valid = result.strategy_validation.get("valid", True)
            if not strategy_valid and result.ml_signal != "HOLD":
                logger.info(
                    f"Model {model.name}: ML signal {result.ml_signal} blocked by strategy. "
                    f"Matched: {result.strategy_validation.get('matched_rules', [])}, "
                    f"Failed: {result.strategy_validation.get('failed_rules', [])}"
                )
            
            logger.info(
                f"Generated prediction for {model.name}: "
                f"ML={result.ml_signal}, Final={result.direction}, "
                f"Confidence={result.confidence:.2%}, Strategy Valid={strategy_valid}"
            )
            
            # Convert PredictionResult to dict for compatibility
            prediction_data = {
                "direction": result.direction,
                "confidence": result.confidence,
                "entry_price": result.entry_price,
                "stop_loss": result.stop_loss,
                "take_profit": result.take_profit,
                "ml_signal": result.ml_signal,
                "strategy_validation": result.strategy_validation,
                "should_trade": result.should_trade,
                "generated_by": result.generated_by,
                "model_type": result.model_type,
                "timestamp": result.timestamp,
            }
            
            return prediction_data
            
        except Exception as e:
            logger.error(f"Prediction failed for model {model.name}: {e}")
            return await self._generate_fallback_prediction(db, model, config)
    
    async def _generate_fallback_prediction(
        self, db: Session, model: MLModel, config: AutoTradingConfig
    ) -> Dict[str, Any]:
        """Fallback prediction when model cannot be loaded."""
        from app.services.risk_management import calculate_sl_tp, get_risk_config
        import random
        
        symbol = model.symbol or "EURUSD"
        
        # Get current price
        entry_price = MarketDataFetcher.get_current_price(symbol)
        if entry_price is None:
            entry_price = get_default_price(symbol)
        
        # Conservative prediction for fallback
        direction = "HOLD"  # Don't trade if model fails
        confidence = 0.0
        
        prediction_data = {
            "direction": direction,
            "confidence": confidence,
            "entry_price": entry_price,
            "stop_loss": None,
            "take_profit": None,
            "generated_by": "fallback",
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Save prediction
        prediction = MLPrediction(
            id=uuid4(),
            model_id=model.id,
            symbol=symbol,
            prediction=prediction_data,
            created_at=datetime.utcnow(),
        )
        db.add(prediction)
        db.commit()
        
        return prediction_data
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> float:
        """Calculate Average True Range."""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean().iloc[-1]
        
        return float(atr) if not pd.isna(atr) else 0.001
    
    async def _execute_real_trade(
        self,
        db: Session,
        model: MLModel,
        prediction_data: Dict[str, Any],
        config: AutoTradingConfig,
    ) -> bool:
        """Execute a real trade via MT5 connector."""
        from app.services import trading_service
        
        try:
            symbol = model.symbol or "EURUSD"
            direction = prediction_data["direction"]
            entry_price = prediction_data["entry_price"]
            stop_loss = prediction_data.get("stop_loss")
            take_profit = prediction_data.get("take_profit")
            
            # Find an active broker connection for this user
            connection = db.query(BrokerConnection).filter(
                BrokerConnection.user_id == model.user_id,
                BrokerConnection.is_active == True,
            ).first()
            
            connection_id = str(connection.id) if connection else None
            
            # Open trade using trading service
            trade, mt5_result = await trading_service.open_order_with_mt5(
                db,
                model.user_id,
                symbol=symbol,
                order_type=direction,
                lot_size=config.lot_size,
                price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                connection_id=connection_id,
            )
            
            # Update trade with source and model reference
            trade.source = "auto_trading"
            trade.ml_model_id = model.id
            db.commit()
            
            if mt5_result.get("success"):
                logger.info(f"Trade executed via MT5: {direction} {symbol} @ {entry_price}")
            else:
                logger.warning(f"Trade saved but MT5 execution failed: {mt5_result.get('error', 'Unknown')}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            db.rollback()
            return False


# Global service instance
auto_trading_service = AutoTradingService()


async def run_auto_trading():
    """Function called by scheduler."""
    return await auto_trading_service.run_auto_trading_cycle()
