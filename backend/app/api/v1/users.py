"""User management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.api import deps
from app.models.user import User
from app.schemas.user import UserOut


router = APIRouter()


class UserSettings(BaseModel):
    """User settings schema."""
    defaultLotSize: str | None = None
    maxLotSize: str | None = None
    maxOpenPositions: str | None = None
    defaultStopLoss: str | None = None
    defaultTakeProfit: str | None = None
    riskPerTrade: str | None = None
    emailNotifications: bool | None = None
    tradeAlerts: bool | None = None
    dailySummary: bool | None = None
    theme: str | None = None
    timezone: str | None = None
    language: str | None = None


@router.get("/me", response_model=UserOut)
def get_current_user(current_user: User = Depends(deps.get_current_user)):
    """Get current user information."""
    return current_user


@router.put("/me")
def update_current_user(
    full_name: str | None = None,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
):
    """Update current user profile."""
    if full_name:
        current_user.full_name = full_name
    
    db.commit()
    db.refresh(current_user)
    
    return {"message": "Profile updated successfully", "user": current_user}


@router.put("/settings")
def update_user_settings(
    settings: UserSettings,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
):
    """
    Update user settings/preferences.
    Settings are stored in a JSON field on the User model.
    """
    # Get current settings or empty dict
    current_settings = current_user.settings or {}
    
    # Merge new settings (only non-None values)
    new_settings = settings.model_dump(exclude_none=True)
    updated_settings = {**current_settings, **new_settings}
    
    # Save to database
    current_user.settings = updated_settings
    db.commit()
    db.refresh(current_user)
    
    return {
        "message": "Settings updated successfully",
        "settings": current_user.get_settings()
    }


@router.get("/settings")
def get_user_settings(
    current_user: User = Depends(deps.get_current_user)
):
    """
    Get user settings/preferences.
    Returns user's saved settings merged with defaults.
    """
    return current_user.get_settings()
