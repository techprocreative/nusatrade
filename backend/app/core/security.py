"""Security utilities and middleware for production."""

import hashlib
import hmac
import secrets
import time
from datetime import datetime, timedelta
from typing import Callable, Optional
from functools import wraps

from jose import jwt
from passlib.context import CryptContext
from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import get_settings


pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated="auto",
    argon2__memory_cost=65536,
    argon2__time_cost=3,
    argon2__parallelism=4,
)
settings = get_settings()


# ============================================
# Password & Token Functions
# ============================================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    expire_delta = expires_minutes or settings.access_token_expire_minutes
    expire = datetime.utcnow() + timedelta(minutes=expire_delta)
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str) -> str:
    """Create a refresh token with longer expiry."""
    expire = datetime.utcnow() + timedelta(days=7)
    to_encode = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


# ============================================
# CSRF Protection
# ============================================

def generate_csrf_token() -> str:
    """Generate a secure CSRF token."""
    return secrets.token_urlsafe(32)


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware."""

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
    CSRF_HEADER = "X-CSRF-Token"
    CSRF_COOKIE = "csrf_token"

    async def dispatch(self, request: Request, call_next):
        # Skip CSRF for safe methods and API routes with Bearer tokens
        if request.method in self.SAFE_METHODS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return await call_next(request)

        # Skip CSRF for WebSocket
        if request.url.path.startswith("/ws/"):
            return await call_next(request)

        csrf_cookie = request.cookies.get(self.CSRF_COOKIE)
        csrf_header = request.headers.get(self.CSRF_HEADER)

        if csrf_cookie and csrf_header and hmac.compare_digest(csrf_cookie, csrf_header):
            return await call_next(request)

        # For development, allow without CSRF
        if settings.environment == "development":
            return await call_next(request)

        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "CSRF token missing or invalid"},
        )


# ============================================
# Rate Limiting (In-Memory - Use Redis in production)
# ============================================

# Import rate limiter from dedicated module
from app.core.rate_limiter import get_rate_limiter


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        requests_per_hour: int = 1000,
    ):
        super().__init__(app)
        self.rpm = requests_per_minute
        self.rph = requests_per_hour

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        
        # Get rate limiter instance
        rate_limiter = get_rate_limiter()
        
        # Check per-minute limit
        allowed, remaining = rate_limiter.is_allowed(
            f"rpm:{client_ip}", self.rpm, 60
        )
        
        if not allowed:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Try again later."},
                headers={"Retry-After": "60"},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.rpm)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        
        return response


# ============================================
# Input Validation
# ============================================

def sanitize_string(value: str, max_length: int = 255) -> str:
    """Sanitize string input."""
    if not value:
        return ""
    value = value[:max_length]
    value = value.replace("\x00", "")
    return value.strip()


def validate_symbol(symbol: str) -> str:
    """Validate trading symbol."""
    allowed_chars = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._")
    symbol = symbol.upper().strip()
    
    if not symbol:
        raise ValueError("Symbol cannot be empty")
    if len(symbol) > 20:
        raise ValueError("Symbol too long")
    if not all(c in allowed_chars for c in symbol):
        raise ValueError("Invalid characters in symbol")
    
    return symbol


def validate_lot_size(lot_size: float, min_lot: float = 0.01, max_lot: float = 100.0) -> float:
    """Validate lot size."""
    if lot_size < min_lot:
        raise ValueError(f"Lot size must be at least {min_lot}")
    if lot_size > max_lot:
        raise ValueError(f"Lot size cannot exceed {max_lot}")
    return round(lot_size, 2)


def validate_price(price: float) -> float:
    """Validate price value."""
    if price < 0:
        raise ValueError("Price cannot be negative")
    if price > 1000000:
        raise ValueError("Price exceeds maximum")
    return round(price, 5)


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Validate password complexity.
    Returns (is_valid, error_message).
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if len(password) > 128:
        return False, "Password must be less than 128 characters"
    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)"
    return True, ""


class AccountLockout:
    """Account lockout manager for brute-force protection."""
    
    MAX_ATTEMPTS = 5
    LOCKOUT_DURATION_SECONDS = 900  # 15 minutes
    
    def __init__(self):
        self._attempts: dict[str, list[float]] = {}
        self._lockouts: dict[str, float] = {}
    
    def record_failed_attempt(self, email: str) -> None:
        """Record a failed login attempt."""
        import time
        now = time.time()
        
        if email not in self._attempts:
            self._attempts[email] = []
        
        # Clean old attempts (older than lockout duration)
        self._attempts[email] = [
            t for t in self._attempts[email]
            if now - t < self.LOCKOUT_DURATION_SECONDS
        ]
        
        self._attempts[email].append(now)
        
        # Check if should be locked out
        if len(self._attempts[email]) >= self.MAX_ATTEMPTS:
            self._lockouts[email] = now + self.LOCKOUT_DURATION_SECONDS
    
    def is_locked_out(self, email: str) -> tuple[bool, int]:
        """
        Check if account is locked out.
        Returns (is_locked, remaining_seconds).
        """
        import time
        
        if email not in self._lockouts:
            return False, 0
        
        now = time.time()
        lockout_until = self._lockouts[email]
        
        if now >= lockout_until:
            # Lockout expired
            del self._lockouts[email]
            if email in self._attempts:
                del self._attempts[email]
            return False, 0
        
        return True, int(lockout_until - now)
    
    def reset(self, email: str) -> None:
        """Reset attempts after successful login."""
        self._attempts.pop(email, None)
        self._lockouts.pop(email, None)
    
    def get_remaining_attempts(self, email: str) -> int:
        """Get remaining login attempts."""
        current = len(self._attempts.get(email, []))
        return max(0, self.MAX_ATTEMPTS - current)


# Global lockout manager
account_lockout = AccountLockout()


# ============================================
# Security Headers Middleware
# ============================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


# ============================================
# Settings Encryption
# ============================================

def get_encryption_key() -> bytes:
    """Get encryption key for system settings."""
    import os
    key = os.getenv("SETTINGS_ENCRYPTION_KEY")
    if not key:
        # In development, use a default key (NOT for production!)
        if settings.environment == "development":
            # Generate a consistent key for development
            import hashlib
            key = hashlib.sha256(b"dev-encryption-key").hexdigest()[:43] + "="
        else:
            raise RuntimeError(
                "SETTINGS_ENCRYPTION_KEY must be set in production. "
                "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
    return key.encode() if isinstance(key, str) else key


def encrypt_setting_value(value: str) -> str:
    """Encrypt a sensitive setting value."""
    try:
        from cryptography.fernet import Fernet
        cipher = Fernet(get_encryption_key())
        return cipher.encrypt(value.encode()).decode()
    except ImportError:
        raise RuntimeError("cryptography package required for settings encryption. Install with: pip install cryptography")


def decrypt_setting_value(encrypted: str) -> str:
    """Decrypt a sensitive setting value."""
    try:
        from cryptography.fernet import Fernet
        cipher = Fernet(get_encryption_key())
        return cipher.decrypt(encrypted.encode()).decode()
    except ImportError:
        raise RuntimeError("cryptography package required for settings encryption. Install with: pip install cryptography")

