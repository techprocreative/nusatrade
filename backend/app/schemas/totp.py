"""TOTP/2FA schemas."""

from pydantic import BaseModel, Field


class TOTPSetupResponse(BaseModel):
    """Response for TOTP setup initiation."""
    secret: str = Field(..., description="TOTP secret key (store securely)")
    qr_code: str = Field(..., description="QR code as base64 data URI")
    uri: str = Field(..., description="TOTP provisioning URI")


class TOTPVerifyRequest(BaseModel):
    """Request to verify and enable TOTP."""
    token: str = Field(..., min_length=6, max_length=6, description="6-digit TOTP code")


class TOTPStatusResponse(BaseModel):
    """Response for TOTP status check."""
    enabled: bool = Field(..., description="Whether 2FA is enabled")


class LoginWith2FARequest(BaseModel):
    """Login request with 2FA token."""
    email: str
    password: str
    totp_token: str | None = Field(None, min_length=6, max_length=6)


class TOTPDisableRequest(BaseModel):
    """Request to disable TOTP."""
    password: str = Field(..., description="User password for verification")
    totp_token: str = Field(..., min_length=6, max_length=6, description="Current TOTP code")
