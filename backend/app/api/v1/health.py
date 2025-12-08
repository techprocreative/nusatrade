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
