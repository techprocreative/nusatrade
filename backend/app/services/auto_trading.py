"""Auto-Trading Service - Background scheduler for ML bot auto-trading."""

import asyncio
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from uuid import uuid4

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.database import SessionLocal
from app.models.ml import MLModel, MLPrediction
from app.models.strategy import Strategy

logger = get_logger(__name__)


class AutoTradingConfig:
    """Configuration for auto-trading."""
    
    # Default settings
    DEFAULT_CONFIDENCE_THRESHOLD = 0.70  # 70%
    DEFAULT_MAX_TRADES_PER_DAY = 5
    DEFAULT_COOLDOWN_MINUTES = 30
    DEFAULT_LOT_SIZE = 0.01
    
    @classmethod
    def from_model_config(cls, config: Optional[dict]) -> "AutoTradingConfig":
        """Create config from model's config field."""
        instance = cls()
        if config:
            instance.confidence_threshold = config.get("confidence_threshold", cls.DEFAULT_CONFIDENCE_THRESHOLD)
            instance.max_trades_per_day = config.get("max_trades_per_day", cls.DEFAULT_MAX_TRADES_PER_DAY)
            instance.cooldown_minutes = config.get("cooldown_minutes", cls.DEFAULT_COOLDOWN_MINUTES)
            instance.lot_size = config.get("lot_size", cls.DEFAULT_LOT_SIZE)
        else:
            instance.confidence_threshold = cls.DEFAULT_CONFIDENCE_THRESHOLD
            instance.max_trades_per_day = cls.DEFAULT_MAX_TRADES_PER_DAY
            instance.cooldown_minutes = cls.DEFAULT_COOLDOWN_MINUTES
            instance.lot_size = cls.DEFAULT_LOT_SIZE
        return instance


class AutoTradingService:
    """Service for automated trading based on ML predictions."""
    
    def __init__(self):
        self._is_running = False
        self._last_run: Optional[datetime] = None
    
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
            # Get all active models
            active_models = db.query(MLModel).filter(
                MLModel.is_active == True,
                MLModel.file_path != None,  # Must be trained
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
    
    async def _process_model(self, db: Session, model: MLModel) -> Dict[str, Any]:
        """Process a single model for auto-trading."""
        result = {
            "model_id": str(model.id),
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
                logger.debug(f"Model {model.id} in cooldown")
                return result
        
        # Check daily trade limit
        today = date.today()
        today_predictions = db.query(MLPrediction).filter(
            MLPrediction.model_id == model.id,
            MLPrediction.created_at >= datetime.combine(today, datetime.min.time()),
        ).count()
        
        if today_predictions >= config.max_trades_per_day:
            result["reason"] = f"Max trades per day ({config.max_trades_per_day}) reached"
            logger.debug(f"Model {model.id} reached daily limit")
            return result
        
        # Generate prediction
        prediction_data = await self._generate_prediction(db, model, config)
        result["prediction_generated"] = True
        
        # Check if we should execute
        direction = prediction_data.get("direction", "HOLD")
        confidence = prediction_data.get("confidence", 0)
        
        if direction == "HOLD":
            result["reason"] = "Prediction is HOLD, no trade"
            return result
        
        if confidence < config.confidence_threshold:
            result["reason"] = f"Confidence {confidence:.2%} below threshold {config.confidence_threshold:.2%}"
            logger.info(f"Model {model.id}: {result['reason']}")
            return result
        
        # Execute trade!
        logger.info(f"Model {model.id}: Executing {direction} trade with {confidence:.2%} confidence")
        
        trade_executed = await self._execute_trade(db, model, prediction_data, config)
        result["trade_executed"] = trade_executed
        
        if trade_executed:
            result["reason"] = f"Trade executed: {direction} with {confidence:.2%} confidence"
        else:
            result["reason"] = "Trade execution failed"
        
        return result
    
    async def _generate_prediction(
        self, db: Session, model: MLModel, config: AutoTradingConfig
    ) -> Dict[str, Any]:
        """Generate a prediction for the model."""
        from app.services.risk_management import (
            calculate_sl_tp,
            get_risk_config,
            RiskConfig,
            SLType,
            TPType,
        )
        import random
        
        symbol = model.symbol or "EURUSD"
        
        # Load strategy if linked
        strategy = None
        if model.strategy_id:
            strategy = db.query(Strategy).filter(Strategy.id == model.strategy_id).first()
        
        # Generate prediction using ML model
        # In production, this would load the actual trained model
        # For now, using simulated prediction
        direction = random.choice(["BUY", "SELL", "HOLD"])
        confidence = round(random.uniform(0.55, 0.95), 2)
        
        # Generate entry price based on symbol
        entry_prices = {
            "EURUSD": 1.0850,
            "GBPUSD": 1.2650,
            "USDJPY": 149.50,
            "AUDUSD": 0.6550,
            "USDCAD": 1.3650,
            "XAUUSD": 2050.00,
        }
        entry_price = entry_prices.get(symbol.upper(), 1.0000)
        entry_price = round(entry_price * (1 + random.uniform(-0.001, 0.001)), 5)
        
        # Get risk config
        if strategy and strategy.risk_management:
            rm = strategy.risk_management
            risk_config = RiskConfig(
                sl_type=SLType(rm.get("stop_loss_type", "atr_based")),
                sl_value=rm.get("stop_loss_value", 2.0),
                tp_type=TPType(rm.get("take_profit_type", "risk_reward")),
                tp_value=rm.get("take_profit_value", 2.0),
                risk_per_trade_percent=rm.get("risk_per_trade_percent", 2.0),
                max_position_size=rm.get("max_position_size", 0.1),
            )
        else:
            risk_config = get_risk_config("moderate")
        
        # Calculate SL/TP
        estimated_atr = {
            "EURUSD": 0.0008,
            "GBPUSD": 0.0012,
            "USDJPY": 0.80,
            "AUDUSD": 0.0007,
            "USDCAD": 0.0009,
            "XAUUSD": 15.0,
        }.get(symbol.upper(), 0.0010)
        
        stop_loss = None
        take_profit = None
        
        if direction != "HOLD":
            stop_loss, take_profit = calculate_sl_tp(
                entry_price=entry_price,
                direction=direction,
                config=risk_config,
                atr=estimated_atr,
            )
        
        prediction_data = {
            "direction": direction,
            "confidence": confidence,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "generated_by": "auto_trading",
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # Save prediction to database
        prediction = MLPrediction(
            id=uuid4(),
            model_id=model.id,
            symbol=symbol,
            prediction=prediction_data,
            created_at=datetime.utcnow(),
        )
        db.add(prediction)
        db.commit()
        
        logger.info(f"Generated prediction for {model.name}: {direction} @ {entry_price}")
        
        return prediction_data
    
    async def _execute_trade(
        self,
        db: Session,
        model: MLModel,
        prediction_data: Dict[str, Any],
        config: AutoTradingConfig,
    ) -> bool:
        """Execute a trade based on prediction."""
        from app.models.trade import Trade
        
        try:
            # For now, create a simulated trade record
            # In production, this would connect to MT5 or broker API
            
            trade = Trade(
                id=uuid4(),
                user_id=model.user_id,
                symbol=model.symbol or "EURUSD",
                trade_type=prediction_data["direction"],
                open_price=prediction_data["entry_price"],
                lot_size=config.lot_size,
                stop_loss=prediction_data.get("stop_loss"),
                take_profit=prediction_data.get("take_profit"),
                status="open",
                profit=0,
                source="auto_trading",
                ml_model_id=model.id,
                created_at=datetime.utcnow(),
            )
            db.add(trade)
            db.commit()
            
            logger.info(f"Trade executed: {trade.trade_type} {trade.symbol} @ {trade.open_price}")
            
            # TODO: In production, send to MT5 connector via WebSocket
            # await self._send_to_mt5(trade)
            
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
