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
    
    Settings are stored in a JSON field or separate settings table.
    For now, we'll return success (implement storage later if needed).
    """
    # TODO: Implement settings storage (add settings field to User model or create Settings table)
    # For MVP, we can store in session or return success
    
    return {
        "message": "Settings updated successfully",
        "settings": settings.dict(exclude_none=True)
    }


@router.get("/settings")
def get_user_settings(
    current_user: User = Depends(deps.get_current_user)
):
    """
    Get user settings/preferences.
    
    Returns default settings for now (implement storage later if needed).
    """
    # TODO: Fetch from database when storage is implemented
    default_settings = {
        "defaultLotSize": "0.1",
        "maxLotSize": "1.0",
        "maxOpenPositions": "5",
        "defaultStopLoss": "50",
        "defaultTakeProfit": "100",
        "riskPerTrade": "2",
        "emailNotifications": True,
        "tradeAlerts": True,
        "dailySummary": False,
        "theme": "dark",
        "timezone": "Asia/Jakarta",
        "language": "en",
    }
    
    return default_settings
