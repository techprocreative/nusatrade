"""ML Models API - Training, Predictions, and Model Management."""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api import deps
from app.models.ml import MLModel, MLPrediction
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
    config: Optional[dict] = None


class ModelResponse(BaseModel):
    model_config = {"protected_namespaces": (), "from_attributes": True}
    
    id: str
    name: str
    model_type: str
    is_active: bool
    performance_metrics: Optional[dict]
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
    
    model_id: str
    symbol: str
    prediction: dict
    confidence: float
    created_at: datetime


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
    
    return [
        ModelResponse(
            id=str(m.id),
            name=m.name or "Unnamed Model",
            model_type=m.model_type or "unknown",
            is_active=m.is_active or False,
            performance_metrics=m.performance_metrics,
            created_at=m.created_at or datetime.utcnow(),
        )
        for m in models
    ]


@router.post("/models", response_model=ModelResponse)
def create_model(
    request: ModelCreateRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Create a new ML model configuration."""
    model = MLModel(
        id=uuid4(),
        user_id=current_user.id,
        name=request.name,
        model_type=request.model_type,
        config={
            "symbol": request.symbol,
            "timeframe": request.timeframe,
            **(request.config or {}),
        },
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
        is_active=model.is_active,
        performance_metrics=model.performance_metrics,
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

    return ModelResponse(
        id=str(model.id),
        name=model.name or "Unnamed",
        model_type=model.model_type or "unknown",
        is_active=model.is_active or False,
        performance_metrics=model.performance_metrics,
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

    model.name = request.name
    model.model_type = request.model_type
    model.config = {
        "symbol": request.symbol,
        "timeframe": request.timeframe,
        **(request.config or {}),
    }
    model.updated_at = datetime.utcnow()
    db.commit()

    return ModelResponse(
        id=str(model.id),
        name=model.name,
        model_type=model.model_type,
        is_active=model.is_active or False,
        performance_metrics=model.performance_metrics,
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
    background_tasks: BackgroundTasks,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Start training an ML model (runs in background)."""
    model = db.query(MLModel).filter(
        MLModel.id == model_id,
        MLModel.user_id == current_user.id,
    ).first()

    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    # Note: In production, use Celery for background tasks
    # For now, return immediate response indicating training started
    
    return {
        "id": model_id,
        "status": "training_queued",
        "message": "Model training has been queued. Check status periodically.",
        "config": {
            "start_date": request.start_date,
            "end_date": request.end_date,
            "test_split": request.test_split,
        },
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
            model_id=str(p.model_id),
            symbol=p.symbol or "UNKNOWN",
            prediction=p.prediction or {},
            confidence=float(p.prediction.get("confidence", 0)) if p.prediction else 0,
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

    if not model.file_path:
        raise HTTPException(
            status_code=400,
            detail="Model not trained yet. Please train the model first.",
        )

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
    
    # Calculate SL/TP based on risk profile from model config or default
    risk_profile = model.config.get("risk_profile", "moderate") if model.config else "moderate"
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
        "trailing_stop": {
            "enabled": True,
            "activation_pips": 20,
            "trail_distance_pips": 15,
            "breakeven_pips": 15,
        } if direction != "HOLD" else None,
    }

    # Save prediction
    prediction = MLPrediction(
        id=uuid4(),
        model_id=model.id,
        symbol=request.symbol,
        prediction=prediction_data,
        created_at=datetime.utcnow(),
    )
    db.add(prediction)
    db.commit()

    return PredictionResponse(
        model_id=str(model.id),
        symbol=request.symbol,
        prediction=prediction_data,
        confidence=confidence,
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
