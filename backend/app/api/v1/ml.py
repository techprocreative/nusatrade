"""ML Models API - Training, Predictions, and Model Management."""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import deps
from app.models.ml import MLModel, MLPrediction
from app.models.strategy import Strategy
from app.ml.features import FeatureEngineer
from app.ml.training import Trainer


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


@router.post("/models", response_model=ModelResponse)
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
    model = db.query(MLModel).filter(
        MLModel.id == model_id,
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
    model = db.query(MLModel).filter(
        MLModel.id == model_id,
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
    model.symbol = request.symbol
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
    model = db.query(MLModel).filter(
        MLModel.id == model_id,
        MLModel.user_id == current_user.id,
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Delete predictions first
    db.query(MLPrediction).filter(MLPrediction.model_id == model_id).delete()
    db.delete(model)
    db.commit()

    return {"deleted": model_id}


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
    model = db.query(MLModel).filter(
        MLModel.id == model_id,
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
        # Train the model
        trainer = Trainer()
        result = trainer.train(
            model_type=model.model_type or "random_forest",
            test_split=request.test_split,
            config={
                "start_date": request.start_date,
                "end_date": request.end_date,
            },
        )

        if result.get("success"):
            # Update model with results
            model.file_path = result.get("model_path")
            model.performance_metrics = result.get("metrics", {})
            model.training_status = "completed"
            model.training_completed_at = datetime.utcnow()
        else:
            model.training_status = "failed"
            model.training_error = result.get("error", "Unknown training error")
        
        db.commit()

        return {
            "id": model_id,
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
    model = db.query(MLModel).filter(
        MLModel.id == model_id,
        MLModel.user_id == current_user.id,
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    return {
        "id": model_id,
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
    model = db.query(MLModel).filter(
        MLModel.id == model_id,
        MLModel.user_id == current_user.id,
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    predictions = db.query(MLPrediction).filter(
        MLPrediction.model_id == model_id
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
    """Generate a prediction using a trained model with SL/TP recommendations."""
    from app.services.risk_management import (
        calculate_sl_tp,
        get_risk_config,
        RiskConfig,
        SLType,
        TPType,
    )
    
    model = db.query(MLModel).filter(
        MLModel.id == model_id,
        MLModel.user_id == current_user.id,
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Load linked strategy if exists
    strategy = None
    strategy_rules = None
    if model.strategy_id:
        strategy = db.query(Strategy).filter(Strategy.id == model.strategy_id).first()
        if strategy:
            # Extract strategy rules for response
            entry_rules = []
            exit_rules = []
            if strategy.entry_rules:
                entry_rules = [r.get("description", r.get("condition", "")) for r in strategy.entry_rules]
            if strategy.exit_rules:
                exit_rules = [r.get("description", r.get("condition", "")) for r in strategy.exit_rules]
            if entry_rules or exit_rules:
                strategy_rules = {"entry_rules": entry_rules, "exit_rules": exit_rules}

    # Generate prediction (simplified - in production, load actual model)
    import random
    direction = random.choice(["BUY", "SELL", "HOLD"])
    confidence = round(random.uniform(0.5, 0.95), 2)
    
    # Generate a realistic entry price based on symbol
    # In production, this would come from live market data
    entry_prices = {
        "EURUSD": 1.0850,
        "GBPUSD": 1.2650,
        "USDJPY": 149.50,
        "AUDUSD": 0.6550,
        "USDCAD": 1.3650,
        "XAUUSD": 2050.00,
    }
    entry_price = entry_prices.get(request.symbol.upper(), 1.0000)
    # Add small random variation
    entry_price = round(entry_price * (1 + random.uniform(-0.001, 0.001)), 5)
    
    # Use Strategy's risk_management settings if available, otherwise use default
    risk_profile = "moderate"
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
        risk_profile = "from_strategy"
    elif model.config and model.config.get("risk_profile"):
        risk_profile = model.config.get("risk_profile", "moderate")
        risk_config = get_risk_config(risk_profile)
    else:
        risk_config = get_risk_config(risk_profile)
    
    # For simplicity, use estimated ATR based on symbol volatility
    estimated_atr = {
        "EURUSD": 0.0008,
        "GBPUSD": 0.0012,
        "USDJPY": 0.80,
        "AUDUSD": 0.0007,
        "USDCAD": 0.0009,
        "XAUUSD": 15.0,
    }.get(request.symbol.upper(), 0.0010)
    
    stop_loss = None
    take_profit = None
    
    if direction != "HOLD":
        stop_loss, take_profit = calculate_sl_tp(
            entry_price=entry_price,
            direction=direction,
            config=risk_config,
            atr=estimated_atr,
        )

    # Build trailing stop config from strategy if available
    trailing_stop_config = None
    if direction != "HOLD":
        if strategy and strategy.risk_management and strategy.risk_management.get("trailing_stop"):
            ts = strategy.risk_management["trailing_stop"]
            trailing_stop_config = {
                "enabled": ts.get("enabled", True),
                "activation_pips": ts.get("activation_pips", 20),
                "trail_distance_pips": ts.get("trail_distance_pips", 15),
                "breakeven_pips": ts.get("breakeven_pips", 15),
            }
        else:
            trailing_stop_config = {
                "enabled": True,
                "activation_pips": 20,
                "trail_distance_pips": 15,
                "breakeven_pips": 15,
            }

    prediction_data = {
        "direction": direction,
        "confidence": confidence,
        "entry_price": entry_price,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "risk_profile": risk_profile,
        "sl_type": risk_config.sl_type.value,
        "tp_type": risk_config.tp_type.value,
        "risk_reward_ratio": round(abs(take_profit - entry_price) / abs(entry_price - stop_loss), 2) if stop_loss and take_profit and stop_loss != entry_price else None,
        "trailing_stop": trailing_stop_config,
        "strategy_rules": strategy_rules,
    }

    # Save prediction
    prediction_id = uuid4()
    prediction = MLPrediction(
        id=prediction_id,
        model_id=model.id,
        symbol=request.symbol,
        prediction=prediction_data,
        created_at=datetime.utcnow(),
    )
    db.add(prediction)
    db.commit()

    return PredictionResponse(
        id=str(prediction_id),
        model_id=str(model.id),
        symbol=request.symbol,
        prediction=prediction_data,
        confidence=confidence,
        strategy_rules=strategy_rules,
        created_at=prediction.created_at,
    )


@router.post("/models/{model_id}/activate")
def activate_model(
    model_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Activate a model for live trading signals."""
    model = db.query(MLModel).filter(
        MLModel.id == model_id,
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

    return {"id": model_id, "status": "active", "message": "Model activated for live trading"}


@router.post("/models/{model_id}/deactivate")
def deactivate_model(
    model_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Deactivate a model from live trading."""
    model = db.query(MLModel).filter(
        MLModel.id == model_id,
        MLModel.user_id == current_user.id,
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    model.is_active = False
    db.commit()

    return {"id": model_id, "status": "inactive"}


@router.post("/models/{model_id}/execute")
async def execute_prediction(
    model_id: str,
    request: ExecuteRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Execute a trade based on ML prediction."""
    from app.services import trading_service
    
    # Verify model ownership
    model = db.query(MLModel).filter(
        MLModel.id == model_id,
        MLModel.user_id == current_user.id,
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Get the prediction
    prediction = db.query(MLPrediction).filter(
        MLPrediction.id == request.prediction_id,
        MLPrediction.model_id == model_id,
    ).first()

    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")

    pred_data = prediction.prediction or {}
    direction = pred_data.get("direction")
    
    if direction == "HOLD":
        raise HTTPException(status_code=400, detail="Cannot execute HOLD signal")

    # Execute trade using trading service
    try:
        trade, mt5_result = await trading_service.open_order_with_mt5(
            db,
            current_user.id,
            symbol=prediction.symbol,
            order_type=direction,
            lot_size=request.lot_size,
            price=pred_data.get("entry_price", 0),
            stop_loss=pred_data.get("stop_loss"),
            take_profit=pred_data.get("take_profit"),
            connection_id=request.connection_id,
        )

        return {
            "success": True,
            "trade_id": str(trade.id),
            "prediction_id": request.prediction_id,
            "direction": direction,
            "entry_price": pred_data.get("entry_price"),
            "stop_loss": pred_data.get("stop_loss"),
            "take_profit": pred_data.get("take_profit"),
            "lot_size": request.lot_size,
            "mt5_execution": mt5_result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to execute trade: {str(e)}")
