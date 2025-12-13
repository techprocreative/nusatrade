"""Service for managing default ML models per symbol."""
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.ml import DefaultMLModel, UserDefaultModel
from app.services.model_registry import get_model_registry
from app.core.logging import get_logger

logger = get_logger(__name__)


class DefaultModelService:
    """Manage default ML models per symbol."""

    def get_default_model_for_symbol(
        self,
        db: Session,
        symbol: str,
        user_id: Optional[UUID] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get default model for a symbol.

        Priority:
        1. User-specific override (if user_id provided)
        2. System default

        Returns:
            Model info dict with path, id, and performance metrics
        """
        # Check user override first
        if user_id:
            user_model = db.query(UserDefaultModel).filter(
                UserDefaultModel.user_id == user_id,
                UserDefaultModel.symbol == symbol
            ).first()

            if user_model:
                return {
                    "model_path": user_model.model_path,
                    "model_id": user_model.model_id,
                    "symbol": symbol,
                    "is_user_override": True,
                }

        # Fall back to system default
        system_model = db.query(DefaultMLModel).filter(
            DefaultMLModel.symbol == symbol,
            DefaultMLModel.is_system_default == True
        ).first()

        if system_model:
            return {
                "model_path": system_model.model_path,
                "model_id": system_model.model_id,
                "symbol": symbol,
                "win_rate": system_model.win_rate,
                "profit_factor": system_model.profit_factor,
                "accuracy": system_model.accuracy,
                "total_trades": system_model.total_trades,
                "is_user_override": False,
            }

        logger.warning(f"No default model found for symbol: {symbol}")
        return None

    def set_user_default_model(
        self,
        db: Session,
        user_id: UUID,
        symbol: str,
        model_path: str,
        model_id: str
    ) -> UserDefaultModel:
        """Set user-specific default model for a symbol."""
        # Check if already exists
        existing = db.query(UserDefaultModel).filter(
            UserDefaultModel.user_id == user_id,
            UserDefaultModel.symbol == symbol
        ).first()

        if existing:
            existing.model_path = model_path
            existing.model_id = model_id
            existing.updated_at = datetime.utcnow()
            model = existing
        else:
            model = UserDefaultModel(
                user_id=user_id,
                symbol=symbol,
                model_path=model_path,
                model_id=model_id
            )
            db.add(model)

        db.commit()
        db.refresh(model)

        logger.info(f"Set default model for user {user_id}, symbol {symbol}: {model_id}")
        return model

    def reset_user_default(
        self,
        db: Session,
        user_id: UUID,
        symbol: str
    ) -> bool:
        """Reset user override to use system default."""
        deleted = db.query(UserDefaultModel).filter(
            UserDefaultModel.user_id == user_id,
            UserDefaultModel.symbol == symbol
        ).delete()

        db.commit()
        logger.info(f"Reset user {user_id} default for {symbol} (deleted: {deleted})")
        return deleted > 0

    def list_available_models_for_symbol(
        self,
        symbol: str
    ) -> List[Dict[str, Any]]:
        """List all available models for a symbol from registry."""
        registry = get_model_registry()
        return registry.list_models_by_symbol(symbol)


# Global instance
_service: Optional[DefaultModelService] = None


def get_default_model_service() -> DefaultModelService:
    """Get or create the global default model service instance."""
    global _service
    if _service is None:
        _service = DefaultModelService()
    return _service
