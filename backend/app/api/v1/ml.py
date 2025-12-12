"""ML Models API - Training, Predictions, and Model Management."""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import deps
from app.models.ml import MLModel, MLPrediction
from app.models.strategy import Strategy
from app.ml.features import FeatureEngineer
from app.ml.training import Trainer
from app.core.validators import validate_uuid, validate_symbol, validate_date_range


router = APIRouter()


# Request/Response Models
class ModelCreateRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    name: str
    model_type: str = "random_forest"  # random_forest, xgboost, lstm
    symbol: str = "EURUSD"
    timeframe: str = "H1"
    strategy_id: Optional[str] = None
    config: Optional[dict] = None


class ModelResponse(BaseModel):
    model_config = {"protected_namespaces": (), "from_attributes": True}
    
    id: str
    name: str
    model_type: str
    symbol: str
    timeframe: str
    strategy_id: Optional[str] = None
    strategy_name: Optional[str] = None
    is_active: bool
    performance_metrics: Optional[dict]
    training_status: str = "idle"
    training_error: Optional[str] = None
    training_started_at: Optional[datetime] = None
    training_completed_at: Optional[datetime] = None
    created_at: datetime


class TrainRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    test_split: float = 0.2


class PredictionRequest(BaseModel):
    symbol: str
    features: Optional[dict] = None


class PredictionResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    
    id: str
    model_id: str
    symbol: str
    prediction: dict
    confidence: float
    strategy_rules: Optional[dict] = None
    created_at: datetime


class ExecuteRequest(BaseModel):
    prediction_id: str
    lot_size: float = 0.1
    connection_id: Optional[str] = None


@router.get("/models", response_model=List[ModelResponse])
def list_models(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
    skip: int = 0,
    limit: int = 20,
):
    """List all ML models for the current user."""
    models = db.query(MLModel).filter(
        MLModel.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    
    result = []
    for m in models:
        strategy_name = None
        if m.strategy_id:
            strategy = db.query(Strategy).filter(Strategy.id == m.strategy_id).first()
            strategy_name = strategy.name if strategy else None
        
        result.append(ModelResponse(
            id=str(m.id),
            name=m.name or "Unnamed Model",
            model_type=m.model_type or "unknown",
            symbol=m.symbol or "EURUSD",
            timeframe=m.timeframe or "H1",
            strategy_id=str(m.strategy_id) if m.strategy_id else None,
            strategy_name=strategy_name,
            is_active=m.is_active or False,
            performance_metrics=m.performance_metrics,
            training_status=m.training_status or "idle",
            training_error=m.training_error,
            training_started_at=m.training_started_at,
            training_completed_at=m.training_completed_at,
            created_at=m.created_at or datetime.utcnow(),
        ))
    
    return result


@router.post("/models", response_model=ModelResponse, status_code=status.HTTP_201_CREATED)
def create_model(
    request: ModelCreateRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Create a new ML model configuration."""
    # Validate strategy_id if provided
    strategy = None
    strategy_name = None
    if request.strategy_id:
        strategy = db.query(Strategy).filter(
            Strategy.id == request.strategy_id,
            (Strategy.user_id == current_user.id) | (Strategy.is_public == True),
        ).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        strategy_name = strategy.name
    
    model = MLModel(
        id=uuid4(),
        user_id=current_user.id,
        strategy_id=strategy.id if strategy else None,
        name=request.name,
        model_type=request.model_type,
        symbol=request.symbol,
        timeframe=request.timeframe,
        config=request.config or {},
        is_active=False,
        created_at=datetime.utcnow(),
    )
    db.add(model)
    db.commit()
    db.refresh(model)

    return ModelResponse(
        id=str(model.id),
        name=model.name,
        model_type=model.model_type,
        symbol=model.symbol,
        timeframe=model.timeframe,
        strategy_id=str(model.strategy_id) if model.strategy_id else None,
        strategy_name=strategy_name,
        is_active=model.is_active,
        performance_metrics=model.performance_metrics,
        training_status=model.training_status or "idle",
        training_error=model.training_error,
        training_started_at=model.training_started_at,
        training_completed_at=model.training_completed_at,
        created_at=model.created_at,
    )


@router.get("/models/{model_id}", response_model=ModelResponse)
def get_model(
    model_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Get a specific ML model."""
    # Validate UUID format to prevent injection
    model_uuid = validate_uuid(model_id, "model_id")

    model = db.query(MLModel).filter(
        MLModel.id == model_uuid,
        MLModel.user_id == current_user.id,
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    strategy_name = None
    if model.strategy_id:
        strategy = db.query(Strategy).filter(Strategy.id == model.strategy_id).first()
        strategy_name = strategy.name if strategy else None

    return ModelResponse(
        id=str(model.id),
        name=model.name or "Unnamed",
        model_type=model.model_type or "unknown",
        symbol=model.symbol or "EURUSD",
        timeframe=model.timeframe or "H1",
        strategy_id=str(model.strategy_id) if model.strategy_id else None,
        strategy_name=strategy_name,
        is_active=model.is_active or False,
        performance_metrics=model.performance_metrics,
        training_status=model.training_status or "idle",
        training_error=model.training_error,
        training_started_at=model.training_started_at,
        training_completed_at=model.training_completed_at,
        created_at=model.created_at or datetime.utcnow(),
    )


@router.put("/models/{model_id}", response_model=ModelResponse)
def update_model(
    model_id: str,
    request: ModelCreateRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Update an ML model configuration."""
    # Validate UUID format
    model_uuid = validate_uuid(model_id, "model_id")

    # Validate symbol format
    validated_symbol = validate_symbol(request.symbol)

    model = db.query(MLModel).filter(
        MLModel.id == model_uuid,
        MLModel.user_id == current_user.id,
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Validate strategy_id if provided
    strategy = None
    strategy_name = None
    if request.strategy_id:
        strategy = db.query(Strategy).filter(
            Strategy.id == request.strategy_id,
            (Strategy.user_id == current_user.id) | (Strategy.is_public == True),
        ).first()
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
        strategy_name = strategy.name

    model.name = request.name
    model.model_type = request.model_type
    model.symbol = validated_symbol  # Use validated symbol
    model.timeframe = request.timeframe
    model.strategy_id = strategy.id if strategy else None
    model.config = request.config or {}
    model.updated_at = datetime.utcnow()
    db.commit()

    return ModelResponse(
        id=str(model.id),
        name=model.name,
        model_type=model.model_type,
        symbol=model.symbol,
        timeframe=model.timeframe,
        strategy_id=str(model.strategy_id) if model.strategy_id else None,
        strategy_name=strategy_name,
        is_active=model.is_active or False,
        performance_metrics=model.performance_metrics,
        training_status=model.training_status or "idle",
        training_error=model.training_error,
        training_started_at=model.training_started_at,
        training_completed_at=model.training_completed_at,
        created_at=model.created_at or datetime.utcnow(),
    )


@router.delete("/models/{model_id}")
def delete_model(
    model_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Delete an ML model."""
    # Validate UUID format
    model_uuid = validate_uuid(model_id, "model_id")

    model = db.query(MLModel).filter(
        MLModel.id == model_uuid,
        MLModel.user_id == current_user.id,
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Delete predictions first
    db.query(MLPrediction).filter(MLPrediction.model_id == model_uuid).delete()
    db.delete(model)
    db.commit()

    return {"deleted": str(model_uuid)}


def _train_model_task(model_id: str, config: dict, db_url: str):
    """Background task for model training."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    try:
        model = db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model:
            return
        
        # Train the model
        trainer = Trainer()
        result = trainer.train(config)
        
        # Update model with results
        model.file_path = result.get("model_path")
        model.performance_metrics = result.get("metrics", {})
        model.updated_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


@router.post("/models/{model_id}/train")
def train_model(
    model_id: str,
    request: TrainRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Train an ML model synchronously."""
    # Validate UUID format to prevent path traversal via model_id
    model_uuid = validate_uuid(model_id, "model_id")

    # Validate date range if provided
    if request.start_date and request.end_date:
        request.start_date, request.end_date = validate_date_range(
            request.start_date, request.end_date
        )

    model = db.query(MLModel).filter(
        MLModel.id == model_uuid,
        MLModel.user_id == current_user.id,
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Check if already training
    if model.training_status == "training":
        raise HTTPException(status_code=400, detail="Model is already being trained")

    # Update status to training
    model.training_status = "training"
    model.training_error = None
    model.training_started_at = datetime.utcnow()
    model.training_completed_at = None
    db.commit()

    try:
        # Train the model with safe model_id
        trainer = Trainer()
        result = trainer.train(
            model_id=str(model_uuid),  # Pass validated UUID for safe path construction
            model_type=model.model_type or "random_forest",
            test_split=request.test_split,
            config={
                "start_date": request.start_date,
                "end_date": request.end_date,
            },
        )

        if result.get("success"):
            # Update model with results (path is already sanitized by Trainer)
            model.file_path = result.get("model_path")
            model.performance_metrics = result.get("metrics", {})
            model.training_status = "completed"
            model.training_completed_at = datetime.utcnow()
        else:
            model.training_status = "failed"
            model.training_error = result.get("error", "Unknown training error")
        
        db.commit()

        return {
            "id": str(model_uuid),
            "status": model.training_status,
            "message": "Training completed" if model.training_status == "completed" else model.training_error,
            "metrics": model.performance_metrics,
            "training_completed_at": model.training_completed_at.isoformat() if model.training_completed_at else None,
        }

    except Exception as e:
        model.training_status = "failed"
        model.training_error = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail=f"Training failed: {str(e)}")


@router.get("/models/{model_id}/status")
def get_training_status(
    model_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Get training status of a model."""
    # Validate UUID format
    model_uuid = validate_uuid(model_id, "model_id")

    model = db.query(MLModel).filter(
        MLModel.id == model_uuid,
        MLModel.user_id == current_user.id,
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    return {
        "id": str(model_uuid),
        "training_status": model.training_status or "idle",
        "training_error": model.training_error,
        "training_started_at": model.training_started_at.isoformat() if model.training_started_at else None,
        "training_completed_at": model.training_completed_at.isoformat() if model.training_completed_at else None,
        "performance_metrics": model.performance_metrics,
        "file_path": model.file_path,
    }


@router.get("/models/{model_id}/predictions", response_model=List[PredictionResponse])
def get_model_predictions(
    model_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
    limit: int = 50,
):
    """Get recent predictions from a model."""
    # Validate UUID format
    model_uuid = validate_uuid(model_id, "model_id")

    model = db.query(MLModel).filter(
        MLModel.id == model_uuid,
        MLModel.user_id == current_user.id,
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    predictions = db.query(MLPrediction).filter(
        MLPrediction.model_id == model_uuid
    ).order_by(MLPrediction.created_at.desc()).limit(limit).all()

    return [
        PredictionResponse(
            id=str(p.id),
            model_id=str(p.model_id),
            symbol=p.symbol or "UNKNOWN",
            prediction=p.prediction or {},
            confidence=float(p.prediction.get("confidence", 0)) if p.prediction else 0,
            strategy_rules=p.prediction.get("strategy_rules") if p.prediction else None,
            created_at=p.created_at or datetime.utcnow(),
        )
        for p in predictions
    ]


@router.post("/models/{model_id}/predict", response_model=PredictionResponse)
def make_prediction(
    model_id: str,
    request: PredictionRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """
    Generate a prediction using trained ML model with strategy validation.

    This endpoint:
    1. Loads the trained ML model
    2. Fetches real market data
    3. Generates ML prediction (BUY/SELL/HOLD)
    4. Validates against linked strategy rules
    5. Returns prediction only if ML + Strategy agree
    """
    from app.services.prediction_service import PredictionService
    from app.core.logging import get_logger

    logger = get_logger(__name__)

    # Validate UUID format and symbol
    model_uuid = validate_uuid(model_id, "model_id")
    validated_symbol = validate_symbol(request.symbol)

    model = db.query(MLModel).filter(
        MLModel.id == model_uuid,
        MLModel.user_id == current_user.id,
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Check if model is trained
    if not model.file_path:
        raise HTTPException(
            status_code=400, 
            detail="Model not trained. Please train the model first."
        )

    try:
        # Use PredictionService for unified ML + Strategy prediction
        prediction_service = PredictionService(db)
        result = prediction_service.generate_prediction(
            model=model,
            symbol=validated_symbol,  # Use validated symbol
            use_strategy_rules=True,
            save_to_db=True,
        )
        
        # Build prediction_data for response
        prediction_data = {
            "direction": result.direction,
            "confidence": result.confidence,
            "entry_price": result.entry_price,
            "stop_loss": result.stop_loss,
            "take_profit": result.take_profit,
            "risk_reward_ratio": result.risk_reward_ratio,
            "trailing_stop": result.trailing_stop,
            "strategy_rules": result.strategy_rules,
            "ml_signal": result.ml_signal,
            "strategy_validation": result.strategy_validation,
            "should_trade": result.should_trade,
            "current_indicators": result.current_indicators,
            "generated_by": result.generated_by,
        }
        
        # Get latest saved prediction ID
        latest_prediction = db.query(MLPrediction).filter(
            MLPrediction.model_id == model.id
        ).order_by(MLPrediction.created_at.desc()).first()
        
        prediction_id = str(latest_prediction.id) if latest_prediction else str(uuid4())
        
        logger.info(
            f"Prediction generated for {model.name}: "
            f"ML={result.ml_signal}, Final={result.direction}, "
            f"Confidence={result.confidence:.2f}, "
            f"Strategy Valid={result.strategy_validation.get('valid', True)}"
        )
        
        return PredictionResponse(
            id=prediction_id,
            model_id=str(model.id),
            symbol=validated_symbol,
            prediction=prediction_data,
            confidence=result.confidence,
            strategy_rules=result.strategy_rules,
            created_at=datetime.utcnow(),
        )
        
    except Exception as e:
        logger.error(f"Prediction failed for model {model_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.post("/models/{model_id}/activate")
def activate_model(
    model_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Activate a model for live trading signals."""
    # Validate UUID format
    model_uuid = validate_uuid(model_id, "model_id")

    model = db.query(MLModel).filter(
        MLModel.id == model_uuid,
        MLModel.user_id == current_user.id,
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    if not model.file_path:
        raise HTTPException(
            status_code=400,
            detail="Cannot activate untrained model",
        )

    # Deactivate other models first
    db.query(MLModel).filter(
        MLModel.user_id == current_user.id,
        MLModel.is_active == True,
    ).update({"is_active": False})

    model.is_active = True
    db.commit()

    return {"id": str(model_uuid), "status": "active", "message": "Model activated for live trading"}


@router.post("/models/{model_id}/deactivate")
def deactivate_model(
    model_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Deactivate a model from live trading."""
    # Validate UUID format
    model_uuid = validate_uuid(model_id, "model_id")

    model = db.query(MLModel).filter(
        MLModel.id == model_uuid,
        MLModel.user_id == current_user.id,
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    model.is_active = False
    db.commit()

    return {"id": str(model_uuid), "status": "inactive"}


@router.post("/models/{model_id}/execute")
async def execute_prediction(
    model_id: str,
    request: ExecuteRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Execute a trade based on ML prediction."""
    from app.services import trading_service
    from app.models.broker import BrokerConnection
    from app.core.validators import validate_lot_size
    from app.core.logging import get_logger

    logger = get_logger(__name__)

    # Validate UUID formats
    model_uuid = validate_uuid(model_id, "model_id")
    prediction_uuid = validate_uuid(request.prediction_id, "prediction_id")

    # Validate lot size
    validated_lot_size = validate_lot_size(request.lot_size)

    # Verify model ownership
    model = db.query(MLModel).filter(
        MLModel.id == model_uuid,
        MLModel.user_id == current_user.id,
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Get the prediction
    prediction = db.query(MLPrediction).filter(
        MLPrediction.id == prediction_uuid,
        MLPrediction.model_id == model_uuid,
    ).first()

    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")

    pred_data = prediction.prediction or {}
    direction = pred_data.get("direction")
    
    if direction == "HOLD":
        raise HTTPException(status_code=400, detail="Cannot execute HOLD signal")

    # Auto-detect connection_id if not provided
    connection_id = request.connection_id
    if not connection_id:
        # Find an active broker connection for this user
        active_connection = db.query(BrokerConnection).filter(
            BrokerConnection.user_id == current_user.id,
            BrokerConnection.is_active == True,
        ).first()
        if active_connection:
            connection_id = str(active_connection.id)
            logger.info(f"Auto-detected connection: {connection_id}")

    # Execute trade using trading service
    try:
        trade, mt5_result = await trading_service.open_order_with_mt5(
            db,
            current_user.id,
            symbol=prediction.symbol,
            order_type=direction,
            lot_size=validated_lot_size,  # Use validated lot size
            price=pred_data.get("entry_price", 0),
            stop_loss=pred_data.get("stop_loss"),
            take_profit=pred_data.get("take_profit"),
            connection_id=connection_id,
        )

        return {
            "success": True,
            "trade_id": str(trade.id),
            "prediction_id": str(prediction_uuid),
            "direction": direction,
            "entry_price": pred_data.get("entry_price"),
            "stop_loss": pred_data.get("stop_loss"),
            "take_profit": pred_data.get("take_profit"),
            "lot_size": validated_lot_size,
            "mt5_execution": mt5_result,
            "connection_id": connection_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute trade: {str(e)}")


@router.get("/dashboard/active-bots")
def get_active_bots_stats(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Get active bots summary for dashboard display."""
    from datetime import date
    
    # Get all active bots for this user
    active_bots = db.query(MLModel).filter(
        MLModel.user_id == current_user.id,
        MLModel.is_active == True,
    ).all()
    
    if not active_bots:
        return {
            "active_count": 0,
            "bots": [],
            "total_signals_today": 0,
        }
    
    today = date.today()
    total_signals_today = 0
    bots_data = []
    
    for bot in active_bots:
        # Get today's predictions count
        today_predictions = db.query(MLPrediction).filter(
            MLPrediction.model_id == bot.id,
            MLPrediction.created_at >= datetime.combine(today, datetime.min.time()),
        ).count()
        
        total_signals_today += today_predictions
        
        # Get last prediction
        last_prediction = db.query(MLPrediction).filter(
            MLPrediction.model_id == bot.id,
        ).order_by(MLPrediction.created_at.desc()).first()
        
        last_pred_data = None
        if last_prediction and last_prediction.prediction:
            pred = last_prediction.prediction
            last_pred_data = {
                "direction": pred.get("direction", "HOLD"),
                "confidence": pred.get("confidence", 0),
                "entry_price": pred.get("entry_price"),
                "created_at": last_prediction.created_at.isoformat() if last_prediction.created_at else None,
            }
        
        # Get strategy name if linked
        strategy_name = None
        if bot.strategy_id:
            strategy = db.query(Strategy).filter(Strategy.id == bot.strategy_id).first()
            strategy_name = strategy.name if strategy else None
        
        bots_data.append({
            "id": str(bot.id),
            "name": bot.name or "Unnamed Bot",
            "model_type": bot.model_type or "unknown",
            "symbol": bot.symbol or "EURUSD",
            "timeframe": bot.timeframe or "H1",
            "strategy_name": strategy_name,
            "accuracy": (bot.performance_metrics or {}).get("accuracy", 0),
            "last_prediction": last_pred_data,
            "today_signals": today_predictions,
            "is_active": True,
        })
    
    return {
        "active_count": len(active_bots),
        "bots": bots_data,
        "total_signals_today": total_signals_today,
    }


@router.post("/auto-trading/trigger")
async def trigger_auto_trading(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Manually trigger auto-trading cycle for testing."""
    from app.services.auto_trading import auto_trading_service
    
    # Check if user has any active models
    active_count = db.query(MLModel).filter(
        MLModel.user_id == current_user.id,
        MLModel.is_active == True,
    ).count()
    
    if active_count == 0:
        raise HTTPException(
            status_code=400,
            detail="No active models found. Activate a trained model first."
        )
    
    # Run auto-trading cycle
    result = await auto_trading_service.run_auto_trading_cycle()
    
    return {
        "status": "completed",
        "result": result,
    }


@router.get("/auto-trading/status")
def get_auto_trading_status(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Get auto-trading status and configuration."""
    from app.services.auto_trading import auto_trading_service
    
    # Get active models count
    active_models = db.query(MLModel).filter(
        MLModel.user_id == current_user.id,
        MLModel.is_active == True,
        MLModel.file_path != None,
    ).count()
    
    # Get today's auto trades
    from datetime import date
    today = date.today()
    today_trades = db.query(MLPrediction).join(MLModel).filter(
        MLModel.user_id == current_user.id,
        MLPrediction.created_at >= datetime.combine(today, datetime.min.time()),
    ).count()
    
    return {
        "scheduler_running": True,  # Will be True when app is running
        "interval_minutes": 15,
        "active_models": active_models,
        "predictions_today": today_trades,
        "last_run": auto_trading_service._last_run.isoformat() if auto_trading_service._last_run else None,
        "config": {
            "default_confidence_threshold": 0.70,
            "default_max_trades_per_day": 5,
            "default_cooldown_minutes": 30,
        }
    }


@router.get("/auto-trading/health")
def get_auto_trading_health():
    """
    Health check endpoint for auto-trading service.
    
    Returns detailed status of the auto-trading scheduler and services.
    """
    from app.services.auto_trading import auto_trading_service
    from datetime import timedelta
    
    last_run = auto_trading_service._last_run
    is_running = auto_trading_service._is_running
    
    # Check if last run was within expected interval (15 min + buffer)
    expected_interval = timedelta(minutes=20)
    is_stale = False
    if last_run:
        time_since_last_run = datetime.utcnow() - last_run
        is_stale = time_since_last_run > expected_interval
    
    # Count loaded models in cache
    loaded_models_count = len(auto_trading_service._loaded_models)
    
    return {
        "status": "healthy" if not is_stale else "stale",
        "is_running": is_running,
        "last_run": last_run.isoformat() if last_run else None,
        "loaded_models_in_cache": loaded_models_count,
        "is_stale": is_stale,
        "checks": {
            "scheduler_initialized": True,
            "last_run_recent": not is_stale,
            "not_stuck": not is_running or (datetime.utcnow() - last_run).seconds < 300 if last_run else True,
        },
        "timestamp": datetime.utcnow().isoformat(),
    }
