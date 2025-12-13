"""Pydantic schemas for ML models."""
from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime


class ModelInfo(BaseModel):
    """Information about a single model file."""
    model_config = ConfigDict(protected_namespaces=())  # Allow model_ prefix

    model_id: str
    model_path: str
    symbol: str
    file_size: int
    created_at: str
    metadata: Dict[str, Any]


class DefaultModelResponse(BaseModel):
    """Response for default model information."""
    model_config = ConfigDict(protected_namespaces=())  # Allow model_ prefix

    model_path: str
    model_id: str
    symbol: str
    is_user_override: bool
    win_rate: Optional[float] = None
    profit_factor: Optional[float] = None
    accuracy: Optional[float] = None
    total_trades: Optional[int] = None


class SetDefaultModelRequest(BaseModel):
    """Request to set a default model."""
    model_config = ConfigDict(protected_namespaces=())  # Allow model_ prefix

    model_path: str
    model_id: str


class SymbolModelsResponse(BaseModel):
    """Response with all models for a symbol."""
    symbol: str
    models: List[ModelInfo]
    system_default: Optional[DefaultModelResponse]
    user_default: Optional[DefaultModelResponse]
