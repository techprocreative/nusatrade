from fastapi import APIRouter

from app.api.v1 import auth, users, health, trading, brokers, backtest, ml, ai, totp, admin_settings, strategies, ml_models

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(trading.router, prefix="/trading", tags=["trading"])
api_router.include_router(strategies.router, prefix="/strategies", tags=["strategies"])
api_router.include_router(brokers.router, prefix="/brokers", tags=["brokers"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
api_router.include_router(ml.router, prefix="/ml", tags=["ml"])
api_router.include_router(ml_models.router, prefix="/ml-models", tags=["ml-models"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
api_router.include_router(totp.router, prefix="/totp", tags=["totp"])
api_router.include_router(admin_settings.router, prefix="/admin", tags=["admin"])
