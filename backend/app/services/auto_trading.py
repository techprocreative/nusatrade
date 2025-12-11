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


class MarketDataFetcher:
    """Fetches real market data for prediction."""
    
    # Map forex symbols to yfinance tickers
    SYMBOL_MAP = {
        "EURUSD": "EURUSD=X",
        "GBPUSD": "GBPUSD=X",
        "USDJPY": "USDJPY=X",
        "AUDUSD": "AUDUSD=X",
        "USDCAD": "USDCAD=X",
        "XAUUSD": "GC=F",  # Gold futures
        "BTCUSD": "BTC-USD",
    }
    
    TIMEFRAME_MAP = {
        "M1": "1m",
        "M5": "5m",
        "M15": "15m",
        "M30": "30m",
        "H1": "1h",
        "H4": "4h",
        "D1": "1d",
    }
    
    @classmethod
    def fetch_data(cls, symbol: str, timeframe: str = "H1", bars: int = 200) -> Optional[pd.DataFrame]:
        """Fetch OHLCV data from yfinance."""
        import yfinance as yf
        
        ticker = cls.SYMBOL_MAP.get(symbol.upper(), f"{symbol}=X")
        interval = cls.TIMEFRAME_MAP.get(timeframe.upper(), "1h")
        
        # Determine period based on interval
        if interval in ["1m", "5m", "15m", "30m"]:
            period = "7d"
        elif interval in ["1h", "4h"]:
            period = "60d"
        else:
            period = "2y"
        
        try:
            data = yf.download(
                ticker,
                period=period,
                interval=interval,
                progress=False,
                auto_adjust=True,
            )
            
            if data.empty:
                logger.warning(f"No data returned for {ticker}")
                return None
            
            # Rename columns to lowercase
            data.columns = [c.lower() for c in data.columns]
            data = data.reset_index()
            
            # Handle timezone-aware datetime
            if 'datetime' in data.columns:
                data = data.rename(columns={'datetime': 'timestamp'})
            elif 'date' in data.columns:
                data = data.rename(columns={'date': 'timestamp'})
            
            # Only return last N bars
            data = data.tail(bars).reset_index(drop=True)
            
            logger.info(f"Fetched {len(data)} bars for {symbol} ({timeframe})")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch data for {symbol}: {e}")
            return None
    
    @classmethod
    def get_current_price(cls, symbol: str) -> Optional[float]:
        """Get current market price."""
        import yfinance as yf
        
        ticker = cls.SYMBOL_MAP.get(symbol.upper(), f"{symbol}=X")
        
        try:
            data = yf.download(ticker, period="1d", interval="1m", progress=False)
            if not data.empty:
                return float(data['Close'].iloc[-1])
        except Exception as e:
            logger.error(f"Failed to get current price for {symbol}: {e}")
        
        return None


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
        """Generate a prediction using the actual trained ML model."""
        from app.services.risk_management import (
            calculate_sl_tp,
            get_risk_config,
            RiskConfig,
            SLType,
            TPType,
        )
        
        symbol = model.symbol or "EURUSD"
        timeframe = model.timeframe or "H1"
        
        # Load the trained model
        trainer = self._load_model(model)
        if trainer is None:
            logger.warning(f"Could not load model for {model.name}, using fallback")
            # Fallback: still generate a prediction but mark it
            return await self._generate_fallback_prediction(db, model, config)
        
        # Fetch real market data
        market_data = MarketDataFetcher.fetch_data(symbol, timeframe, bars=200)
        
        if market_data is None or len(market_data) < 50:
            logger.error(f"Insufficient market data for {symbol}")
            return None
        
        # Build features
        feature_engineer = FeatureEngineer()
        featured_data = feature_engineer.build_features(market_data)
        
        # Get the last row for prediction (most recent data)
        last_row = featured_data.iloc[[-1]]
        
        try:
            # Make prediction using trained model
            prediction_result = trainer.predict(last_row)
            
            direction = prediction_result.get("direction", "HOLD")
            confidence = prediction_result.get("confidence", 0.5)
            
            # Get current price
            entry_price = MarketDataFetcher.get_current_price(symbol)
            if entry_price is None:
                entry_price = float(market_data["close"].iloc[-1])
            
        except Exception as e:
            logger.error(f"Model prediction failed: {e}")
            return await self._generate_fallback_prediction(db, model, config)
        
        # Load linked strategy for risk management
        strategy = None
        if model.strategy_id:
            strategy = db.query(Strategy).filter(Strategy.id == model.strategy_id).first()
        
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
        
        # Calculate ATR for SL/TP
        atr = self._calculate_atr(market_data)
        
        stop_loss = None
        take_profit = None
        
        if direction != "HOLD":
            stop_loss, take_profit = calculate_sl_tp(
                entry_price=entry_price,
                direction=direction,
                config=risk_config,
                atr=atr,
            )
        
        prediction_data = {
            "direction": direction,
            "confidence": confidence,
            "entry_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "probabilities": prediction_result.get("probabilities", {}),
            "generated_by": "ml_model",
            "model_type": model.model_type,
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
        
        logger.info(f"Generated REAL prediction for {model.name}: {direction} @ {entry_price} (confidence: {confidence:.2%})")
        
        return prediction_data
    
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
            # Use default prices
            default_prices = {
                "EURUSD": 1.0850, "GBPUSD": 1.2650, "USDJPY": 149.50,
                "AUDUSD": 0.6550, "USDCAD": 1.3650, "XAUUSD": 2050.00,
            }
            entry_price = default_prices.get(symbol.upper(), 1.0)
        
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
