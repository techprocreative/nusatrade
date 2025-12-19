"""Health check and monitoring endpoints."""

import asyncio
import time
from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api import deps
from app.config import get_settings


router = APIRouter()
settings = get_settings()

# Track application start time
_start_time = time.time()


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }


@router.get("/health/detailed")
async def detailed_health_check(db: Session = Depends(deps.get_db)):
    """Detailed health check with component status."""
    checks: Dict[str, Any] = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": int(time.time() - _start_time),
        "components": {},
    }

    # Database check
    try:
        start = time.time()
        db.execute(text("SELECT 1"))
        db_latency = (time.time() - start) * 1000
        checks["components"]["database"] = {
            "status": "healthy",
            "latency_ms": round(db_latency, 2),
        }
    except Exception as e:
        checks["components"]["database"] = {
            "status": "unhealthy",
            "error": str(e),
        }
        checks["status"] = "degraded"

    # Check if critical services are configured
    checks["components"]["config"] = {
        "status": "healthy",
        "jwt_configured": bool(settings.jwt_secret and settings.jwt_secret != "your-secret-key"),
        "database_configured": bool(settings.database_url),
        "openai_configured": bool(settings.openai_api_key),
    }

    if not checks["components"]["config"]["jwt_configured"]:
        checks["status"] = "warning"
        checks["components"]["config"]["warning"] = "Using default JWT secret"

    return checks


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(deps.get_db)):
    """Readiness probe for Kubernetes/container orchestration."""
    try:
        db.execute(text("SELECT 1"))
        return {"ready": True}
    except Exception:
        return {"ready": False}, 503


@router.get("/health/live")
async def liveness_check():
    """Liveness probe for Kubernetes/container orchestration."""
    return {"alive": True}


@router.get("/metrics")
async def prometheus_metrics(db: Session = Depends(deps.get_db)):
    """Basic metrics endpoint (expand with prometheus_client for production)."""
    from app.models.trade import Trade
    from app.models.user import User
    from app.models.signal import Signal

    try:
        # Get basic counts
        user_count = db.query(User).count()
        trade_count = db.query(Trade).count()
        signal_count = db.query(Signal).count()

        metrics = {
            "uptime_seconds": int(time.time() - _start_time),
            "users_total": user_count,
            "trades_total": trade_count,
            "signals_total": signal_count,
        }

        return metrics
    except Exception as e:
        return {"error": str(e)}


@router.get("/info")
async def app_info():
    """Application information."""
    return {
        "name": "ForexAI Trading Platform",
        "version": "1.0.0",
        "environment": settings.environment,
        "api_version": "v1",
        "docs_url": "/docs",
    }


@router.get("/auto-trading/status")
async def auto_trading_status(db: Session = Depends(deps.get_db)):
    """
    Get auto-trading scheduler status and statistics.
    
    Returns current state of the auto-trading system including:
    - Scheduler status (enabled/running)
    - Active model count
    - Today's predictions count
    - Last run time
    """
    from app.services.auto_trading import auto_trading_service
    from app.models.ml import MLModel, MLPrediction
    
    try:
        # Get active models count (with strategy linked and trained)
        active_models_with_strategy = db.query(MLModel).filter(
            MLModel.is_active == True,
            MLModel.file_path != None,
            MLModel.strategy_id != None,
        ).count()
        
        # Get active but missing requirements
        active_without_strategy = db.query(MLModel).filter(
            MLModel.is_active == True,
            MLModel.file_path != None,
            MLModel.strategy_id == None,
        ).count()
        
        active_not_trained = db.query(MLModel).filter(
            MLModel.is_active == True,
            MLModel.file_path == None,
        ).count()
        
        # Get today's predictions
        today = datetime.utcnow().date()
        today_predictions = db.query(MLPrediction).filter(
            MLPrediction.created_at >= datetime.combine(today, datetime.min.time())
        ).count()
        
        # Calculate next scheduled run
        last_run = auto_trading_service._last_run
        if last_run:
            from datetime import timedelta
            next_run = last_run + timedelta(minutes=15)
        else:
            next_run = None
        
        return {
            "status": "ok",
            "scheduler": {
                "enabled": True,
                "interval_minutes": 15,
                "is_running": auto_trading_service._is_running,
                "last_run": last_run.isoformat() if last_run else None,
                "next_scheduled_run": next_run.isoformat() if next_run else "pending first run",
            },
            "models": {
                "active_and_ready": active_models_with_strategy,
                "active_missing_strategy": active_without_strategy,
                "active_not_trained": active_not_trained,
            },
            "predictions": {
                "today_count": today_predictions,
            },
            "health_tips": [] if active_models_with_strategy > 0 else [
                "No active models ready for auto-trading.",
                "Ensure you have a model that is: (1) activated, (2) trained, (3) linked to a strategy."
            ],
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }

