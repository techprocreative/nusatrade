"""
ML Auto Trading Service - Integrates profitable ML strategy with MT5 execution.

This service:
1. Loads the profitable ML strategy
2. Generates predictions using the ML model
3. Validates predictions against strategy rules
4. Executes trades via MT5 connector

This ensures the auto-trading system uses the proven profitable configuration.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID, uuid4

import pandas as pd
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.ml import MLModel
from app.models.strategy import Strategy
from app.models.broker import BrokerConnection
from app.services.optimized_predictor import OptimizedTradingPredictor
from app.strategies.ml_profitable_strategy import MLProfitableStrategy, get_default_strategy_config

logger = get_logger(__name__)


class MLAutoTradingService:
    """
    Auto-trading service that uses the profitable ML strategy.

    Integrates:
    - ML model predictions (XGBoost)
    - Strategy validation (entry/exit rules)
    - MT5 execution
    - Risk management
    """

    def __init__(self):
        """Initialize auto-trading service."""
        self.predictor: Optional[OptimizedTradingPredictor] = None
        self.strategy_config = get_default_strategy_config()

    async def initialize_predictor(self):
        """Initialize the ML predictor with optimal configuration."""
        if self.predictor is not None:
            return  # Already initialized

        try:
            self.predictor = OptimizedTradingPredictor(
                model_path=self.strategy_config["model_path"],
                confidence_threshold=self.strategy_config["confidence_threshold"],
                tp_sl_ratio=2.0,  # Not used (model has built-in 0.8:1.2)
                use_session_filter=self.strategy_config["use_session_filter"],
                use_volatility_filter=self.strategy_config["use_volatility_filter"],
                use_trend_filter=self.strategy_config["use_trend_filter"],
            )

            logger.info("✅ ML Auto Trading Service initialized with profitable configuration")
        except Exception as e:
            logger.error(f"Failed to initialize predictor: {e}")

    async def process_trading_signal(
        self,
        db: Session,
        user_id: UUID,
        symbol: str = "XAUUSD",
    ) -> Dict[str, Any]:
        """
        Process a trading signal for auto-trading.

        Steps:
        1. Validate symbol compatibility
        2. Load recent market data
        3. Generate ML prediction
        4. Validate against strategy rules
        5. Execute trade if all checks pass

        Args:
            db: Database session
            user_id: User ID
            symbol: Trading symbol (must be XAUUSD for current model)

        Returns:
            Result with prediction and execution status
        """
        result = {
            "timestamp": datetime.utcnow().isoformat(),
            "symbol": symbol,
            "prediction_generated": False,
            "trade_executed": False,
            "signal": "HOLD",
            "reason": None,
        }

        # Validate symbol before proceeding
        from app.strategies.ml_profitable_strategy import MLProfitableStrategy

        if not MLProfitableStrategy.is_symbol_supported(symbol):
            supported = MLProfitableStrategy.get_supported_symbols()
            result["reason"] = (
                f"Symbol '{symbol}' is not supported by this ML model. "
                f"Supported symbols: {supported}. "
                f"The current model is trained exclusively on XAUUSD data."
            )
            logger.warning(result["reason"])
            return result

        # Initialize predictor
        await self.initialize_predictor()

        if self.predictor is None:
            result["reason"] = "Predictor not initialized"
            return result

        try:
            # Load recent market data
            df = await self._load_market_data(symbol)

            if df is None or len(df) < 100:
                result["reason"] = "Insufficient market data"
                return result

            # Generate prediction
            prediction = self.predictor.predict(df)
            result["prediction_generated"] = True
            result["signal"] = prediction["signal"]
            result["confidence"] = prediction.get("confidence", 0.0)

            # Check if signal is HOLD
            if prediction["signal"] == "HOLD":
                result["reason"] = prediction.get("reason", "No trade signal")
                return result

            # Signal is BUY or SELL - proceed with execution
            logger.info(f"Trading signal: {prediction['signal']} with {prediction['confidence']:.1%} confidence")

            # Execute trade via MT5
            trade_executed = await self._execute_trade_mt5(
                db=db,
                user_id=user_id,
                symbol=symbol,
                prediction=prediction,
            )

            result["trade_executed"] = trade_executed

            if trade_executed:
                result["reason"] = f"Trade executed: {prediction['signal']}"
                result["entry_price"] = prediction.get("entry_price")
                result["stop_loss"] = prediction.get("sl_price")
                result["take_profit"] = prediction.get("tp_price")
            else:
                result["reason"] = "Trade execution failed"

        except Exception as e:
            logger.error(f"Error processing trading signal: {e}")
            result["reason"] = f"Error: {str(e)}"

        return result

    async def _load_market_data(self, symbol: str) -> Optional[pd.DataFrame]:
        """
        Load recent market data for prediction.

        Args:
            symbol: Trading symbol

        Returns:
            DataFrame with OHLCV data or None
        """
        try:
            # Load from CSV (in production, this would fetch from MT5 or database)
            data_path = f"ohlcv/{symbol.lower()}/{symbol.lower()}_1h_clean.csv"

            import os
            if not os.path.exists(data_path):
                logger.warning(f"Data file not found: {data_path}")
                return None

            df = pd.read_csv(data_path)
            df['timestamp'] = pd.to_datetime(df['timestamp'])

            # Get last 100 candles for feature calculation
            df = df.tail(100)

            logger.info(f"Loaded {len(df)} candles for {symbol}")
            return df

        except Exception as e:
            logger.error(f"Failed to load market data: {e}")
            return None

    async def _execute_trade_mt5(
        self,
        db: Session,
        user_id: UUID,
        symbol: str,
        prediction: Dict[str, Any],
    ) -> bool:
        """
        Execute trade via MT5 connector.

        Args:
            db: Database session
            user_id: User ID
            symbol: Trading symbol
            prediction: Prediction dict with signal, prices, etc.

        Returns:
            True if trade executed successfully
        """
        try:
            from app.services import trading_service

            # Get active broker connection
            connection = db.query(BrokerConnection).filter(
                BrokerConnection.user_id == user_id,
                BrokerConnection.is_active == True,
            ).first()

            if not connection:
                logger.warning(f"No active broker connection for user {user_id}")
                return False

            connection_id = str(connection.id)

            # Get lot size from strategy config
            lot_size = self.strategy_config.get("default_lot_size", 0.01)

            # Open trade
            trade, mt5_result = await trading_service.open_order_with_mt5(
                db=db,
                user_id=user_id,
                symbol=symbol,
                order_type=prediction["signal"],
                lot_size=lot_size,
                price=prediction["entry_price"],
                stop_loss=prediction["sl_price"],
                take_profit=prediction["tp_price"],
                connection_id=connection_id,
            )

            # Mark trade as auto-trading source
            if trade:
                trade.source = "ml_auto_trading"
                trade.strategy_id = await self._get_or_create_ml_strategy(db, user_id)
                db.commit()

            if mt5_result.get("success"):
                logger.info(f"✅ Trade executed via MT5: {prediction['signal']} {symbol} @ {prediction['entry_price']:.2f}")
                return True
            else:
                logger.warning(f"MT5 execution failed: {mt5_result.get('error', 'Unknown error')}")
                return False

        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            return False

    async def _get_or_create_ml_strategy(self, db: Session, user_id: UUID) -> Optional[UUID]:
        """
        Get or create the default ML strategy for a user.

        Args:
            db: Database session
            user_id: User ID

        Returns:
            Strategy ID or None
        """
        try:
            # Check if user already has ML strategy
            strategy = db.query(Strategy).filter(
                Strategy.user_id == user_id,
                Strategy.name == MLProfitableStrategy.NAME,
            ).first()

            if strategy:
                return strategy.id

            # Create new ML strategy
            from app.strategies.ml_profitable_strategy import create_default_ml_strategy

            strategy_data = create_default_ml_strategy(str(user_id))

            strategy = Strategy(
                id=uuid4(),
                **strategy_data,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )

            db.add(strategy)
            db.commit()
            db.refresh(strategy)

            logger.info(f"Created ML strategy for user {user_id}")
            return strategy.id

        except Exception as e:
            logger.error(f"Failed to get/create ML strategy: {e}")
            return None

    async def run_auto_trading_cycle(
        self,
        db: Session,
        symbol: str = "XAUUSD",
    ) -> Dict[str, Any]:
        """
        Run one auto-trading cycle for all active users.

        This should be called periodically (e.g., every hour) by the scheduler.

        Args:
            db: Database session
            symbol: Trading symbol

        Returns:
            Summary of cycle execution
        """
        logger.info("Starting ML auto-trading cycle...")

        results = {
            "started_at": datetime.utcnow().isoformat(),
            "users_processed": 0,
            "signals_generated": 0,
            "trades_executed": 0,
            "errors": [],
        }

        try:
            # Get all users with active ML models
            active_models = db.query(MLModel).filter(
                MLModel.is_active == True,
                MLModel.file_path == self.strategy_config["model_path"],
            ).all()

            for model in active_models:
                try:
                    result = await self.process_trading_signal(
                        db=db,
                        user_id=model.user_id,
                        symbol=symbol,
                    )

                    results["users_processed"] += 1

                    if result["prediction_generated"]:
                        results["signals_generated"] += 1

                    if result["trade_executed"]:
                        results["trades_executed"] += 1

                except Exception as e:
                    error_msg = f"Error processing user {model.user_id}: {str(e)}"
                    logger.error(error_msg)
                    results["errors"].append(error_msg)

            results["completed_at"] = datetime.utcnow().isoformat()
            logger.info(f"ML auto-trading cycle completed: {results}")

        except Exception as e:
            logger.error(f"Auto-trading cycle failed: {e}")
            results["errors"].append(str(e))

        return results


# Global service instance
ml_auto_trading_service = MLAutoTradingService()


# Function for scheduler
async def run_ml_auto_trading(db: Session, symbol: str = "XAUUSD") -> Dict[str, Any]:
    """
    Function called by scheduler to run auto-trading cycle.

    Args:
        db: Database session
        symbol: Trading symbol

    Returns:
        Cycle execution results
    """
    return await ml_auto_trading_service.run_auto_trading_cycle(db, symbol)
