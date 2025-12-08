from fastapi import APIRouter

from app.api.v1 import auth, users, brokers, trading, backtest, ml, ai, totp


api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(totp.router, prefix="/totp", tags=["2FA"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(brokers.router, prefix="/brokers", tags=["brokers"])
api_router.include_router(trading.router, prefix="/trading", tags=["trading"])
api_router.include_router(backtest.router, prefix="/backtest", tags=["backtest"])
api_router.include_router(ml.router, prefix="/ml", tags=["ml"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
