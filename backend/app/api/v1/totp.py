"""Two-Factor Authentication endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.models.user import User
from app.schemas.totp import (
    TOTPSetupResponse,
    TOTPVerifyRequest,
    TOTPStatusResponse,
    TOTPDisableRequest
)
from app.services.totp_service import totp_service
from app.core import security


router = APIRouter()


@router.get("/status", response_model=TOTPStatusResponse)
def get_totp_status(current_user: User = Depends(deps.get_current_user)):
    """Check if 2FA is enabled for current user."""
    return TOTPStatusResponse(enabled=current_user.totp_enabled or False)


@router.post("/setup", response_model=TOTPSetupResponse)
def setup_totp(
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
):
    """
    Initiate TOTP setup for the current user.
    Returns QR code and secret to be scanned by authenticator app.
    """
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled. Disable it first to re-setup."
        )
    
    # Generate new secret and QR code
    secret, uri, qr_code = totp_service.setup_totp(current_user.email)
    
    # Save secret (but don't enable yet - wait for verification)
    current_user.totp_secret = secret
    current_user.totp_enabled = False
    db.commit()
    
    return TOTPSetupResponse(
        secret=secret,
        qr_code=qr_code,
        uri=uri
    )


@router.post("/verify", response_model=TOTPStatusResponse)
def verify_and_enable_totp(
    request: TOTPVerifyRequest,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
):
    """
    Verify TOTP token and enable 2FA.
    User must provide correct token from their authenticator app.
    """
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please setup 2FA first using /totp/setup endpoint"
        )
    
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled"
        )
    
    # Verify token
    if not totp_service.verify_totp(current_user.totp_secret, request.token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code. Please try again."
        )
    
    # Enable 2FA
    current_user.totp_enabled = True
    db.commit()
    
    return TOTPStatusResponse(enabled=True)


@router.post("/disable", response_model=TOTPStatusResponse)
def disable_totp(
    request: TOTPDisableRequest,
    current_user: User = Depends(deps.get_current_user),
    db: Session = Depends(deps.get_db)
):
    """
    Disable 2FA for the current user.
    Requires password and current TOTP token for security.
    """
    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled"
        )
    
    # Verify password
    if not security.verify_password(request.password, current_user.password_hash or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )
    
    # Verify TOTP token
    if not totp_service.verify_totp(current_user.totp_secret or "", request.token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code"
        )
    
    # Disable 2FA
    current_user.totp_enabled = False
    current_user.totp_secret = None
    db.commit()
    
    return TOTPStatusResponse(enabled=False)
