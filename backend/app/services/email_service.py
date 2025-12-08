"""Email service for sending password reset and notifications."""

import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from enum import Enum

from sqlalchemy.orm import Session

from app.models.user import User
from app.core.logging import get_logger
from app.config import get_settings


logger = get_logger(__name__)
settings = get_settings()


class EmailProvider(str, Enum):
    """Supported email providers."""
    SENDGRID = "sendgrid"
    AWS_SES = "aws_ses"
    CONSOLE = "console"  # For development/testing


# In-memory storage for reset tokens (use Redis in production)
_reset_tokens = {}


def generate_reset_token(user_id: UUID) -> str:
    """Generate a password reset token."""
    token = secrets.token_urlsafe(32)
    expiry = datetime.utcnow() + timedelta(hours=1)
    _reset_tokens[token] = {
        "user_id": str(user_id),
        "expiry": expiry
    }
    return token


def validate_reset_token(token: str) -> Optional[str]:
    """Validate reset token and return user_id if valid."""
    if token not in _reset_tokens:
        return None
    
    token_data = _reset_tokens[token]
    if datetime.utcnow() > token_data["expiry"]:
        del _reset_tokens[token]
        return None
    
    return token_data["user_id"]


def invalidate_reset_token(token: str):
    """Invalidate a reset token after use."""
    if token in _reset_tokens:
        del _reset_tokens[token]


def _get_email_provider() -> EmailProvider:
    """Get configured email provider."""
    provider = getattr(settings, "email_provider", "console").lower()
    try:
        return EmailProvider(provider)
    except ValueError:
        logger.warning(f"Unknown email provider '{provider}', falling back to console")
        return EmailProvider.CONSOLE


def _send_with_sendgrid(to_email: str, subject: str, html_content: str, text_content: str | None = None) -> bool:
    """Send email using SendGrid."""
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail
        
        api_key = getattr(settings, "sendgrid_api_key", None)
        from_email = getattr(settings, "email_from", "noreply@forexai.com")
        
        if not api_key:
            logger.error("SendGrid API key not configured")
            return False
        
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
            plain_text_content=text_content or html_content
        )
        
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        
        if response.status_code in [200, 201, 202]:
            logger.info(f"Email sent successfully to {to_email} via SendGrid")
            return True
        else:
            logger.error(f"SendGrid returned status {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Failed to send email via SendGrid: {e}")
        return False


def _send_with_aws_ses(to_email: str, subject: str, html_content: str, text_content: str | None = None) -> bool:
    """Send email using AWS SES."""
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        from_email = getattr(settings, "email_from", "noreply@forexai.com")
        region = getattr(settings, "aws_region", "us-east-1")
        
        client = boto3.client('ses', region_name=region)
        
        body = {"Html": {"Data": html_content}}
        if text_content:
            body["Text"] = {"Data": text_content}
        
        response = client.send_email(
            Source=from_email,
            Destination={"ToAddresses": [to_email]},
            Message={
                "Subject": {"Data": subject},
                "Body": body
            }
        )
        
        logger.info(f"Email sent successfully to {to_email} via AWS SES (MessageId: {response['MessageId']})")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send email via AWS SES: {e}")
        return False


def _send_email(to_email: str, subject: str, html_content: str, text_content: str | None = None) -> bool:
    """Send email using configured provider."""
    provider = _get_email_provider()
    
    if provider == EmailProvider.CONSOLE:
        # Development mode - just log
        logger.info(f"[EMAIL] To: {to_email}")
        logger.info(f"[EMAIL] Subject: {subject}")
        logger.info(f"[EMAIL] Content: {html_content[:200]}...")
        return True
    
    elif provider == EmailProvider.SENDGRID:
        return _send_with_sendgrid(to_email, subject, html_content, text_content)
    
    elif provider == EmailProvider.AWS_SES:
        return _send_with_aws_ses(to_email, subject, html_content, text_content)
    
    return False


def send_password_reset_email(user: User, reset_url: str) -> bool:
    """Send password reset email to user."""
    subject = "Reset Your Password - Forex AI Platform"
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>Password Reset Request</h2>
            <p>Hello {user.full_name or user.email},</p>
            <p>We received a request to reset your password. Click the link below to reset it:</p>
            <p><a href="{reset_url}" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
            <p>Or copy and paste this URL into your browser:</p>
            <p>{reset_url}</p>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request this, please ignore this email.</p>
            <hr>
            <p style="color: #666; font-size: 12px;">Forex AI Platform - AI-Powered Trading</p>
        </body>
    </html>
    """
    
    text_content = f"""
    Password Reset Request
    
    Hello {user.full_name or user.email},
    
    We received a request to reset your password. Click the link below to reset it:
    {reset_url}
    
    This link will expire in 1 hour.
    
    If you didn't request this, please ignore this email.
    
    ---
    Forex AI Platform - AI-Powered Trading
    """
    
    return _send_email(user.email, subject, html_content, text_content)


def send_welcome_email(user: User) -> bool:
    """Send welcome email to new user."""
    subject = "Welcome to Forex AI Platform!"
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>Welcome to Forex AI Platform! 🎉</h2>
            <p>Hello {user.full_name or user.email},</p>
            <p>Thank you for joining Forex AI Platform - your intelligent trading companion.</p>
            <h3>What's Next?</h3>
            <ul>
                <li>Connect your MT5 broker account</li>
                <li>Setup your first ML trading bot</li>
                <li>Backtest strategies with historical data</li>
                <li>Chat with AI Supervisor for trading insights</li>
            </ul>
            <p><a href="{getattr(settings, 'frontend_url', 'https://app.forexai.com')}/dashboard" style="background: #28a745; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Go to Dashboard</a></p>
            <p>Need help? Contact our support team anytime.</p>
            <hr>
            <p style="color: #666; font-size: 12px;">Forex AI Platform - AI-Powered Trading</p>
        </body>
    </html>
    """
    
    return _send_email(user.email, subject, html_content)


def send_trade_notification(user: User, trade_info: dict) -> bool:
    """Send trade notification email."""
    subject = f"Trade Alert: {trade_info.get('type', 'UNKNOWN')} {trade_info.get('symbol', '')}"
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>Trade Notification</h2>
            <p>Hello {user.full_name or user.email},</p>
            <p><strong>Trade Details:</strong></p>
            <ul>
                <li><strong>Symbol:</strong> {trade_info.get('symbol', 'N/A')}</li>
                <li><strong>Type:</strong> {trade_info.get('type', 'N/A')}</li>
                <li><strong>Lot Size:</strong> {trade_info.get('lot_size', 'N/A')}</li>
                <li><strong>Entry Price:</strong> {trade_info.get('entry_price', 'N/A')}</li>
                <li><strong>Profit/Loss:</strong> {trade_info.get('profit', 'N/A')}</li>
            </ul>
            <p><a href="{getattr(settings, 'frontend_url', 'https://app.forexai.com')}/trading" style="background: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">View Trade</a></p>
            <hr>
            <p style="color: #666; font-size: 12px;">Forex AI Platform - AI-Powered Trading</p>
        </body>
    </html>
    """
    
    return _send_email(user.email, subject, html_content)


def send_2fa_enabled_email(user: User) -> bool:
    """Send notification that 2FA was enabled."""
    subject = "Two-Factor Authentication Enabled"
    
    html_content = f"""
    <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2>2FA Enabled Successfully ✅</h2>
            <p>Hello {user.full_name or user.email},</p>
            <p>Two-factor authentication has been successfully enabled for your account.</p>
            <p>Your account is now more secure. You'll need to provide a code from your authenticator app when logging in.</p>
            <p><strong>Important:</strong> Make sure to keep your backup codes in a safe place.</p>
            <p>If you didn't enable 2FA, please contact support immediately.</p>
            <hr>
            <p style="color: #666; font-size: 12px;">Forex AI Platform - AI-Powered Trading</p>
        </body>
    </html>
    """
    
    return _send_email(user.email, subject, html_content)
