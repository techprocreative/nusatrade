"""Two-Factor Authentication (TOTP) service."""

import io
import base64
import pyotp
import qrcode
from typing import Tuple


class TOTPService:
    """Service for managing TOTP (Time-based One-Time Password) 2FA."""
    
    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret key."""
        return pyotp.random_base32()
    
    @staticmethod
    def get_totp_uri(secret: str, email: str, issuer: str = "Forex AI Platform") -> str:
        """Generate TOTP provisioning URI for QR code."""
        totp = pyotp.TOTP(secret)
        return totp.provisioning_uri(name=email, issuer_name=issuer)
    
    @staticmethod
    def generate_qr_code(uri: str) -> str:
        """Generate QR code image as base64 string."""
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_base64}"
    
    @staticmethod
    def verify_totp(secret: str, token: str) -> bool:
        """Verify a TOTP token."""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)  # Allow 1 step tolerance
    
    @staticmethod
    def setup_totp(email: str) -> Tuple[str, str, str]:
        """
        Setup TOTP for a user.
        
        Returns:
            Tuple of (secret, uri, qr_code_base64)
        """
        secret = TOTPService.generate_secret()
        uri = TOTPService.get_totp_uri(secret, email)
        qr_code = TOTPService.generate_qr_code(uri)
        
        return secret, uri, qr_code


# Singleton instance
totp_service = TOTPService()
