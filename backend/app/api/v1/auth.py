from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api import deps
from app.core import security
from app.core.security import validate_password_strength, account_lockout
from app.core.rate_limit_decorators import rate_limit_auth
from app.models.user import User
from app.schemas.user import UserCreate, UserLogin, UserOut
from app.schemas.auth import Token, TokenWithRefresh
from app.schemas.totp import LoginWith2FARequest
from app.services.totp_service import totp_service


router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
@rate_limit_auth  # SECURITY: Limit registration attempts to prevent abuse
def register(user_in: UserCreate, db: Session = Depends(deps.get_db)):
    # Validate password strength
    is_valid, error_msg = validate_password_strength(user_in.password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    
    exists = db.query(User).filter(User.email == user_in.email).first()
    if exists:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    hashed_password = security.get_password_hash(user_in.password)
    user = User(email=user_in.email, full_name=user_in.full_name, password_hash=hashed_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenWithRefresh)
@rate_limit_auth  # SECURITY: Limit login attempts to prevent brute force
def login(user_in: UserLogin, db: Session = Depends(deps.get_db)):
    """Login endpoint (for users without 2FA or legacy clients)."""
    # Check lockout
    is_locked, remaining = account_lockout.is_locked_out(user_in.email)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account locked due to too many failed attempts. Try again in {remaining} seconds.",
            headers={"Retry-After": str(remaining)}
        )
    
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not security.verify_password(user_in.password, user.password_hash or ""):
        # Record failed attempt
        account_lockout.record_failed_attempt(user_in.email)
        remaining_attempts = account_lockout.get_remaining_attempts(user_in.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=f"Incorrect email or password. {remaining_attempts} attempts remaining."
        )
    
    # Reset lockout on successful login
    account_lockout.reset(user_in.email)
    
    # Check if 2FA is enabled
    if user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="2FA is enabled. Please use /auth/login-2fa endpoint with TOTP code."
        )
    
    access_token = security.create_access_token(subject=user.email)
    refresh_token = security.create_refresh_token(subject=user.email)
    return TokenWithRefresh(access_token=access_token, refresh_token=refresh_token)


@router.post("/login-2fa", response_model=TokenWithRefresh)
@rate_limit_auth  # SECURITY: Limit 2FA attempts to prevent code guessing
def login_with_2fa(request: LoginWith2FARequest, db: Session = Depends(deps.get_db)):
    """Login endpoint for users with 2FA enabled."""
    # Check lockout
    is_locked, remaining = account_lockout.is_locked_out(request.email)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Account locked due to too many failed attempts. Try again in {remaining} seconds.",
            headers={"Retry-After": str(remaining)}
        )
    
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not security.verify_password(request.password, user.password_hash or ""):
        account_lockout.record_failed_attempt(request.email)
        remaining_attempts = account_lockout.get_remaining_attempts(request.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail=f"Incorrect email or password. {remaining_attempts} attempts remaining."
        )
    
    # Check if 2FA is enabled
    if not user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled for this account. Use /auth/login endpoint."
        )
    
    # Verify TOTP token
    if not request.totp_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="TOTP token is required"
        )
    
    if not totp_service.verify_totp(user.totp_secret or "", request.totp_token):
        account_lockout.record_failed_attempt(request.email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid TOTP code"
        )
    
    # Reset lockout on successful login
    account_lockout.reset(request.email)
    
    # Generate tokens
    access_token = security.create_access_token(subject=user.email)
    refresh_token = security.create_refresh_token(subject=user.email)
    return TokenWithRefresh(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout")
def logout():
    return {"status": "logged_out"}


@router.post("/refresh", response_model=TokenWithRefresh)
def refresh(refresh_token: str, db: Session = Depends(deps.get_db)):
    """Refresh access token using refresh token."""
    from jose import jwt, JWTError
    from app.config import get_settings
    
    settings = get_settings()
    
    try:
        payload = jwt.decode(
            refresh_token, 
            settings.jwt_secret, 
            algorithms=[settings.jwt_algorithm]
        )
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if email is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Verify user exists
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Generate new tokens
    new_access_token = security.create_access_token(subject=user.email)
    new_refresh_token = security.create_refresh_token(subject=user.email)
    return TokenWithRefresh(access_token=new_access_token, refresh_token=new_refresh_token)


@router.post("/forgot-password")
@rate_limit_auth  # SECURITY: Prevent password reset flooding
def forgot_password(email: str, db: Session = Depends(deps.get_db)):
    """Request password reset email."""
    from app.services import email_service
    
    user = db.query(User).filter(User.email == email).first()
    
    # Always return success even if user doesn't exist (security best practice)
    if not user:
        return {"status": "email_sent", "message": "If the email exists, a reset link will be sent"}
    
    # Generate reset token
    reset_token = email_service.generate_reset_token(user.id)
    
    # In production, this should be the frontend URL
    reset_url = f"https://app.forexai.com/reset-password?token={reset_token}"
    
    # Send email
    email_service.send_password_reset_email(user, reset_url)
    
    return {
        "status": "email_sent",
        "message": "If the email exists, a reset link will be sent",
        "dev_token": reset_token if deps.get_db == "development" else None  # Only in dev
    }


@router.post("/reset-password")
@rate_limit_auth  # SECURITY: Prevent password reset abuse
def reset_password(token: str, new_password: str, db: Session = Depends(deps.get_db)):
    """Reset password with token."""
    from app.services import email_service
    
    # Validate token
    user_id = email_service.validate_reset_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )
    
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Validate password strength
    is_valid, error_msg = validate_password_strength(new_password)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)
    
    # Update password
    user.password_hash = security.get_password_hash(new_password)
    db.commit()
    
    # Invalidate token
    email_service.invalidate_reset_token(token)
    
    return {"status": "success", "message": "Password has been reset"}
