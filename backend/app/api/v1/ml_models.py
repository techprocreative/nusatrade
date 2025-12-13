"""API endpoints for ML model management."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.api import deps
from app.models.user import User
from app.services.default_model_service import get_default_model_service
from app.services.model_registry import get_model_registry
from app.schemas.ml import (
    ModelInfo,
    DefaultModelResponse,
    SetDefaultModelRequest,
    SymbolModelsResponse
)

router = APIRouter()


@router.get("/models", response_model=Dict[str, List[ModelInfo]])
def list_all_models(
    current_user: User = Depends(deps.get_current_user)
):
    """
    List all available ML models grouped by symbol.

    Returns:
        {
            "XAUUSD": [...models...],
            "EURUSD": [...models...],
            "BTCUSD": [...models...]
        }
    """
    registry = get_model_registry()
    return registry.get_all_symbols_models()


@router.get("/models/{symbol}", response_model=SymbolModelsResponse)
def list_models_for_symbol(
    symbol: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    List all models for a specific symbol with default info.

    Shows:
    - All available models
    - Which one is system default
    - Which one is user's default (if overridden)
    """
    service = get_default_model_service()
    registry = get_model_registry()

    # Get all models for symbol
    models = registry.list_models_by_symbol(symbol)

    # Get default models
    system_default = service.get_default_model_for_symbol(db, symbol, user_id=None)
    user_default = service.get_default_model_for_symbol(db, symbol, user_id=current_user.id)

    return {
        "symbol": symbol,
        "models": models,
        "system_default": system_default,
        "user_default": user_default
    }


@router.get("/defaults", response_model=Dict[str, DefaultModelResponse])
def get_all_defaults(
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Get default models for all symbols.

    Returns user overrides if set, otherwise system defaults.
    """
    service = get_default_model_service()
    symbols = ["XAUUSD", "EURUSD", "BTCUSD"]

    result = {}
    for symbol in symbols:
        default = service.get_default_model_for_symbol(
            db, symbol, user_id=current_user.id
        )
        if default:
            result[symbol] = default

    return result


@router.get("/defaults/{symbol}", response_model=DefaultModelResponse)
def get_default_for_symbol(
    symbol: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """Get default model for a specific symbol."""
    service = get_default_model_service()

    default = service.get_default_model_for_symbol(
        db, symbol, user_id=current_user.id
    )

    if not default:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No default model configured for symbol: {symbol}"
        )

    return default


@router.post("/defaults/{symbol}", response_model=DefaultModelResponse)
def set_user_default(
    symbol: str,
    request: SetDefaultModelRequest,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Set user-specific default model for a symbol.

    This overrides the system default.
    """
    service = get_default_model_service()

    # Validate model exists
    registry = get_model_registry()
    model_info = registry.get_model_info(request.model_path)
    if not model_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model not found: {request.model_path}"
        )

    # Set user default
    service.set_user_default_model(
        db,
        user_id=current_user.id,
        symbol=symbol,
        model_path=request.model_path,
        model_id=request.model_id
    )

    # Return new default
    return service.get_default_model_for_symbol(
        db, symbol, user_id=current_user.id
    )


@router.delete("/defaults/{symbol}")
def reset_user_default(
    symbol: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Reset user override to use system default.
    """
    service = get_default_model_service()

    success = service.reset_user_default(db, current_user.id, symbol)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No user override found for symbol: {symbol}"
        )

    return {
        "status": "success",
        "message": f"Reset to system default for {symbol}"
    }
