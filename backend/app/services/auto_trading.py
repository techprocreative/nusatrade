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

    # Default settings - Synced with frontend
    DEFAULT_CONFIDENCE_THRESHOLD = 0.70  # 70% (synced with frontend)
    DEFAULT_MAX_TRADES_PER_DAY = 5
    DEFAULT_COOLDOWN_MINUTES = 30
    DEFAULT_LOT_SIZE = 0.01
    DEFAULT_CHECK_INTERVAL_MINUTES = 15  # NEW: Default check interval
    
    def __init__(self):
        self.confidence_threshold = self.DEFAULT_CONFIDENCE_THRESHOLD
        self.max_trades_per_day = self.DEFAULT_MAX_TRADES_PER_DAY
        self.cooldown_minutes = self.DEFAULT_COOLDOWN_MINUTES
        self.lot_size = self.DEFAULT_LOT_SIZE
        self.check_interval_minutes = self.DEFAULT_CHECK_INTERVAL_MINUTES
    
    @classmethod
    def from_model_config(cls, config: Optional[dict]) -> "AutoTradingConfig":
        """Create config from model's config field."""
        instance = cls()
        if config:
            instance.confidence_threshold = config.get("confidence_threshold", cls.DEFAULT_CONFIDENCE_THRESHOLD)
            instance.max_trades_per_day = config.get("max_trades_per_day", cls.DEFAULT_MAX_TRADES_PER_DAY)
            instance.cooldown_minutes = config.get("cooldown_minutes", cls.DEFAULT_COOLDOWN_MINUTES)
            instance.lot_size = config.get("lot_size", cls.DEFAULT_LOT_SIZE)
            instance.check_interval_minutes = config.get("check_interval_minutes", cls.DEFAULT_CHECK_INTERVAL_MINUTES)
        return instance


class AutoTradingService:
    """Service for automated trading based on ML predictions."""
    
    def __init__(self):
        self._is_running = False
        self._last_run: Optional[datetime] = None
        self._loaded_models: Dict[str, Trainer] = {}  # Cache for loaded models
        self._last_check_per_model: Dict[str, datetime] = {}  # Track last check time per model
    
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
        
        logger.info("=" * 60)
        logger.info("🤖 AUTO-TRADING CYCLE STARTING")
        logger.info(f"   Time: {self._last_run.isoformat()}")
        logger.info("=" * 60)
        
        results = {
            "started_at": self._last_run.isoformat(),
            "models_checked": 0,
            "predictions_generated": 0,
            "trades_executed": 0,
            "errors": [],
        }

        db: Session = SessionLocal()

        try:
            # Step 1: Query ALL active trained models (we'll filter by strategy later)
            all_active_models = db.query(MLModel).filter(
                MLModel.is_active == True,
                MLModel.file_path != None,
            ).all()
            
            logger.info(f"📊 Total active trained models: {len(all_active_models)}")
            
            # Step 2: Filter models that have either:
            # - A linked strategy_id, OR
            # - A built-in strategy (ml_scalping, ml_profitable in config)
            active_models = []
            models_without_strategy = []
            
            for model in all_active_models:
                model_config = model.config or {}
                strategy_type = model_config.get("strategy_type", "")
                has_builtin = strategy_type in ["ml_scalping", "ml_profitable"]
                
                if model.strategy_id or has_builtin:
                    active_models.append(model)
                    if has_builtin:
                        logger.info(f"   ✅ Model '{model.name}' has built-in strategy: {strategy_type}")
                    else:
                        logger.info(f"   ✅ Model '{model.name}' has linked strategy_id")
                else:
                    models_without_strategy.append(model)
                    logger.debug(f"   ⏭️  Model '{model.name}' skipped: no strategy")

            results["models_checked"] = len(active_models)
            logger.info(f"📈 Models ready for auto-trading: {len(active_models)}")

            if models_without_strategy:
                logger.warning(
                    f"⚠️  {len(models_without_strategy)} active model(s) skipped: no strategy linked. "
                    f"Models: {[m.name for m in models_without_strategy]}"
                )

            # Also log untrained active models
            untrained_models = db.query(MLModel).filter(
                MLModel.is_active == True,
                MLModel.file_path == None,
            ).all()
            
            if untrained_models:
                logger.warning(
                    f"⚠️  {len(untrained_models)} active model(s) skipped: not trained. "
                    f"Models: {[m.name for m in untrained_models]}"
                )

            for model in active_models:
                model_id = str(model.id)
                config = AutoTradingConfig.from_model_config(model.config)
                now = datetime.utcnow()
                
                # Check if model's interval has elapsed
                last_check = self._last_check_per_model.get(model_id)
                if last_check:
                    elapsed_minutes = (now - last_check).total_seconds() / 60
                    if elapsed_minutes < config.check_interval_minutes:
                        logger.debug(f"⏭️  Skipping {model.name}: interval {config.check_interval_minutes}min, elapsed {elapsed_minutes:.1f}min")
                        continue
                
                try:
                    logger.info(f"📈 Processing model: {model.name} ({model.symbol}) [interval: {config.check_interval_minutes}min]")
                    
                    # Update last check time BEFORE processing
                    self._last_check_per_model[model_id] = now
                    
                    trade_result = await self._process_model(db, model)
                    if trade_result.get("prediction_generated"):
                        results["predictions_generated"] += 1
                    if trade_result.get("trade_executed"):
                        results["trades_executed"] += 1
                    logger.info(f"   Result: {trade_result.get('reason', 'OK')}")
                except Exception as e:
                    error_msg = f"Error processing model {model.id}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)
            
            results["completed_at"] = datetime.utcnow().isoformat()
            
            logger.info("=" * 60)
            logger.info("📊 AUTO-TRADING CYCLE SUMMARY")
            logger.info(f"   Models checked: {results['models_checked']}")
            logger.info(f"   Predictions generated: {results['predictions_generated']}")
            logger.info(f"   Trades executed: {results['trades_executed']}")
            if results['errors']:
                logger.warning(f"   Errors: {len(results['errors'])}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ Auto-trading cycle failed: {e}")
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
        logger.debug(f"   Config: threshold={config.confidence_threshold:.0%}, max_trades={config.max_trades_per_day}, cooldown={config.cooldown_minutes}min")
        
        # Check cooldown
        last_prediction = db.query(MLPrediction).filter(
            MLPrediction.model_id == model.id
        ).order_by(MLPrediction.created_at.desc()).first()
        
        if last_prediction:
            cooldown_until = last_prediction.created_at + timedelta(minutes=config.cooldown_minutes)
            now = datetime.utcnow()
            if now < cooldown_until:
                remaining = (cooldown_until - now).total_seconds() / 60
                result["reason"] = f"Cooldown: {remaining:.1f} min remaining"
                logger.info(f"   ⏳ Model in cooldown until {cooldown_until.strftime('%H:%M:%S')} ({remaining:.1f} min left)")
                return result
            logger.debug(f"   ✅ Cooldown passed (last prediction: {last_prediction.created_at.strftime('%H:%M:%S')})")
        else:
            logger.debug(f"   ✅ No previous predictions, no cooldown")
        
        # Check daily trade limit
        today = date.today()
        today_predictions = db.query(MLPrediction).filter(
            MLPrediction.model_id == model.id,
            MLPrediction.created_at >= datetime.combine(today, datetime.min.time()),
        ).count()
        
        logger.debug(f"   📊 Today's predictions: {today_predictions}/{config.max_trades_per_day}")
        
        if today_predictions >= config.max_trades_per_day:
            result["reason"] = f"Max trades per day ({config.max_trades_per_day}) reached"
            logger.info(f"   🚫 Daily limit reached: {today_predictions}/{config.max_trades_per_day}")
            return result
        
        # Generate prediction using real model
        logger.info(f"   🔮 Generating prediction for {model.name}...")
        prediction_data = await self._generate_real_prediction(db, model, config)
        
        if prediction_data is None:
            result["reason"] = "Failed to generate prediction"
            logger.warning(f"   ❌ Prediction generation failed")
            return result
        
        result["prediction_generated"] = True
        
        # Check if we should execute
        direction = prediction_data.get("direction", "HOLD")
        confidence = prediction_data.get("confidence", 0)
        generated_by = prediction_data.get("generated_by", "unknown")
        
        logger.info(f"   📈 Prediction: {direction} @ {confidence:.1%} (by {generated_by})")
        
        if direction == "HOLD":
            result["reason"] = f"Prediction is HOLD (confidence: {confidence:.1%})"
            logger.info(f"   ⏸️  No trade: {result['reason']}")
            return result
        
        if confidence < config.confidence_threshold:
            result["reason"] = f"Confidence {confidence:.1%} below threshold {config.confidence_threshold:.0%}"
            logger.info(f"   🔻 No trade: {result['reason']}")
            return result
        
        # Execute trade!
        logger.info(f"   🚀 EXECUTING TRADE: {direction} with {confidence:.1%} confidence")
        logger.info(f"      Entry: {prediction_data.get('entry_price')}, SL: {prediction_data.get('stop_loss')}, TP: {prediction_data.get('take_profit')}")
        
        trade_executed = await self._execute_real_trade(db, model, prediction_data, config)
        result["trade_executed"] = trade_executed
        
        if trade_executed:
            result["reason"] = f"✅ Trade executed: {direction} @ {confidence:.1%}"
            logger.info(f"   ✅ Trade execution successful!")
        else:
            result["reason"] = "Trade execution failed"
            logger.warning(f"   ❌ Trade execution failed")
        
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
        """Execute a real trade via MT5 connector with validation."""
        from app.services import trading_service
        from app.models.trade import Trade, Position
        from app.models.user import User
        from datetime import date, timedelta

        try:
            symbol = model.symbol or "EURUSD"
            direction = prediction_data["direction"]
            entry_price = prediction_data["entry_price"]
            stop_loss = prediction_data.get("stop_loss")
            take_profit = prediction_data.get("take_profit")

            # Get user and their risk settings
            user = db.query(User).filter(User.id == model.user_id).first()
            user_settings = user.settings or {}
            risk_settings = user_settings.get("risk_management", {})

            # Get risk limits from user settings (with defaults)
            max_daily_loss = risk_settings.get("max_daily_loss", -500.0)
            max_positions = risk_settings.get("max_positions", 10)
            max_lot_size = risk_settings.get("max_lot_size", 0.5)
            risk_enabled = risk_settings.get("enabled", True)

            # === CRITICAL VALIDATION CHECKS ===

            if not risk_enabled:
                logger.warning(f"Risk management disabled for user {model.user_id}")

            # 1. Check daily loss limit
            today = date.today()
            today_start = datetime.combine(today, datetime.min.time())

            daily_trades = db.query(Trade).filter(
                Trade.user_id == model.user_id,
                Trade.created_at >= today_start,
                Trade.status == "closed"
            ).all()

            daily_pnl = sum(t.profit or 0 for t in daily_trades)

            if daily_pnl < max_daily_loss:
                logger.warning(
                    f"Daily loss limit reached for user {model.user_id}: "
                    f"${daily_pnl:.2f} < ${max_daily_loss:.2f}"
                )
                return False

            # 2. Check max concurrent positions
            open_positions = db.query(Position).filter(
                Position.user_id == model.user_id,
                Position.status == "open"
            ).count()

            if open_positions >= max_positions:
                logger.warning(
                    f"Max positions limit reached for user {model.user_id}: "
                    f"{open_positions} >= {max_positions}"
                )
                return False

            # 3. Verify symbol/timeframe match
            if model.symbol and model.symbol != symbol:
                logger.error(
                    f"Symbol mismatch: Model={model.symbol}, Trade={symbol}"
                )
                return False

            # 4. Validate lot size
            if config.lot_size > max_lot_size:
                logger.warning(
                    f"Lot size {config.lot_size} exceeds max {max_lot_size}, "
                    f"using {max_lot_size} instead"
                )
                config.lot_size = max_lot_size

            # 5. Find an active broker connection
            connection = db.query(BrokerConnection).filter(
                BrokerConnection.user_id == model.user_id,
                BrokerConnection.is_active == True,
            ).first()

            if not connection:
                logger.error(f"No active MT5 connection for user {model.user_id}")
                return False

            connection_id = str(connection.id)

            # === EXECUTE TRADE ===

            logger.info(
                f"Executing trade: {direction} {config.lot_size} lots {symbol} "
                f"@ {entry_price} (SL: {stop_loss}, TP: {take_profit})"
            )
            logger.info(
                f"Risk check: Daily P/L: ${daily_pnl:.2f}/{max_daily_loss:.2f}, "
                f"Positions: {open_positions}/{max_positions}"
            )

            # Open trade using trading service WITH RETRY
            trade, mt5_result = await trading_service.open_order_with_mt5_retry(
                db,
                model.user_id,
                symbol=symbol,
                order_type=direction,
                lot_size=config.lot_size,
                price=entry_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                connection_id=connection_id,
                max_retries=3,  # 3 attempts with exponential backoff
            )

            # Update trade with source and model reference
            trade.source = "auto_trading"
            trade.ml_model_id = model.id
            db.commit()

            if mt5_result.get("success"):
                logger.info(
                    f"✅ Trade executed via MT5: {direction} {symbol} @ {entry_price}, "
                    f"Ticket: {mt5_result.get('ticket', 'N/A')}"
                )
                
                # Send notifications (async, non-blocking)
                try:
                    await self._send_trade_notification(
                        user=user,
                        trade_data={
                            "type": direction,
                            "symbol": symbol,
                            "lot_size": config.lot_size,
                            "entry_price": entry_price,
                            "stop_loss": stop_loss,
                            "take_profit": take_profit,
                            "ticket": mt5_result.get("ticket", "N/A"),
                        },
                        action="executed",
                    )
                except Exception as notify_error:
                    logger.warning(f"Failed to send trade notification: {notify_error}")
                
                return True
            else:
                logger.warning(
                    f"⚠️ Trade saved but MT5 execution failed: "
                    f"{mt5_result.get('error', 'Unknown')}"
                )
                return False

        except Exception as e:
            logger.error(f"❌ Failed to execute trade: {e}", exc_info=True)
            db.rollback()
            return False
    
    async def _send_trade_notification(
        self,
        user,
        trade_data: Dict[str, Any],
        action: str = "executed",
    ):
        """Send trade notification via Telegram and Email."""
        from app.services.telegram_service import send_trade_notification as send_telegram
        from app.services.email_service import send_trade_notification as send_email
        
        user_settings = user.get_settings() if user else {}
        
        # Send via Telegram if enabled
        if user_settings.get("telegramEnabled") and user_settings.get("telegramBotToken"):
            await send_telegram(user_settings, trade_data, action)
        
        # Send via Email if enabled
        if user_settings.get("emailNotifications") and user_settings.get("tradeAlerts"):
            send_email(user, trade_data)


# Global service instance
auto_trading_service = AutoTradingService()


async def run_auto_trading():
    """Function called by scheduler."""
    return await auto_trading_service.run_auto_trading_cycle()
