"""Authentication service for connector."""

import json
import logging
from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import os

import requests
from requests.exceptions import RequestException


logger = logging.getLogger(__name__)


# ============================================
# SERVER CONFIGURATION
# ============================================
PRODUCTION_SERVER = "https://nusatrade.onrender.com"
DEVELOPMENT_SERVER = "http://localhost:8000"
FRONTEND_URL = "https://nusatrade-beta.vercel.app"

# Production mode by default
USE_PRODUCTION = True
# ============================================


def get_server_url() -> str:
    """Get the server URL based on environment."""
    # Environment variable takes priority
    env_server = os.environ.get("NUSATRADE_SERVER")
    if env_server:
        return env_server
    
    if USE_PRODUCTION:
        return PRODUCTION_SERVER
    return DEVELOPMENT_SERVER


def get_frontend_url() -> str:
    """Get the frontend URL for registration."""
    return FRONTEND_URL


@dataclass
class AuthToken:
    """Authentication token data."""
    access_token: str
    refresh_token: str
    user_id: str
    email: str


class AuthService:
    """Handle authentication with the backend server."""

    TOKEN_FILE = "auth_token.json"

    def __init__(self):
        self.server_url = get_server_url()
        self.token: Optional[AuthToken] = None
        self._token_path = self._get_token_path()

    def _get_token_path(self) -> Path:
        """Get path to token storage file."""
        if os.name == "nt":
            config_dir = Path(os.environ.get("APPDATA", ".")) / "NusaTradeConnector"
        else:
            config_dir = Path.home() / ".config" / "nusatrade-connector"
        
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir / self.TOKEN_FILE

    def login(self, email: str, password: str, remember: bool = True) -> tuple[bool, str]:
        """
        Login with email and password.
        
        Returns:
            (success, message)
        """
        try:
            response = requests.post(
                f"{self.server_url}/api/v1/auth/login",
                json={"email": email, "password": password},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                self.token = AuthToken(
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token", ""),
                    user_id=data.get("user_id", ""),
                    email=email,
                )
                
                if remember:
                    self._save_token()
                
                logger.info(f"Login successful for {email}")
                return True, "Login successful"

            elif response.status_code == 401:
                return False, "Invalid email or password"
            elif response.status_code == 404:
                return False, "Account not found"
            else:
                return False, f"Server error: {response.status_code}"

        except RequestException as e:
            logger.error(f"Login request failed: {e}")
            return False, f"Connection failed: {str(e)}"
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False, f"Error: {str(e)}"

    def logout(self):
        """Logout and clear saved token."""
        self.token = None
        self._delete_token()
        logger.info("Logged out")

    def refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token."""
        if not self.token or not self.token.refresh_token:
            return False

        try:
            response = requests.post(
                f"{self.server_url}/api/v1/auth/refresh",
                json={"refresh_token": self.token.refresh_token},
                timeout=10,
            )

            if response.status_code == 200:
                data = response.json()
                self.token.access_token = data["access_token"]
                if data.get("refresh_token"):
                    self.token.refresh_token = data["refresh_token"]
                self._save_token()
                logger.info("Token refreshed")
                return True

        except Exception as e:
            logger.error(f"Token refresh failed: {e}")

        return False

    def load_saved_token(self) -> bool:
        """Load previously saved token."""
        if not self._token_path.exists():
            return False

        try:
            with open(self._token_path, "r") as f:
                data = json.load(f)
            
            self.token = AuthToken(
                access_token=data["access_token"],
                refresh_token=data.get("refresh_token", ""),
                user_id=data.get("user_id", ""),
                email=data.get("email", ""),
            )
            
            # Verify token is still valid
            if self._verify_token():
                logger.info(f"Loaded saved token for {self.token.email}")
                return True
            else:
                # Try refresh
                if self.refresh_access_token():
                    return True
                    
                self.token = None
                return False

        except Exception as e:
            logger.error(f"Failed to load saved token: {e}")
            return False

    def _verify_token(self) -> bool:
        """Verify the current token is valid."""
        if not self.token:
            return False

        try:
            response = requests.get(
                f"{self.server_url}/api/v1/auth/me",
                headers={"Authorization": f"Bearer {self.token.access_token}"},
                timeout=5,
            )
            return response.status_code == 200
        except:
            return False

    def _save_token(self):
        """Save token to file."""
        if not self.token:
            return

        try:
            data = {
                "access_token": self.token.access_token,
                "refresh_token": self.token.refresh_token,
                "user_id": self.token.user_id,
                "email": self.token.email,
            }
            with open(self._token_path, "w") as f:
                json.dump(data, f)
            
            # Secure file permissions on Unix
            if os.name != "nt":
                os.chmod(self._token_path, 0o600)
                
        except Exception as e:
            logger.error(f"Failed to save token: {e}")

    def _delete_token(self):
        """Delete saved token file."""
        try:
            if self._token_path.exists():
                self._token_path.unlink()
        except Exception as e:
            logger.error(f"Failed to delete token: {e}")

    def is_authenticated(self) -> bool:
        """Check if user is authenticated."""
        return self.token is not None

    def get_access_token(self) -> Optional[str]:
        """Get current access token."""
        return self.token.access_token if self.token else None

    def get_ws_url(self) -> str:
        """Get WebSocket URL with proper protocol."""
        if self.server_url.startswith("https://"):
            ws_base = self.server_url.replace("https://", "wss://")
        else:
            ws_base = self.server_url.replace("http://", "ws://")
        return f"{ws_base}/connector/ws"

    def get_user_email(self) -> str:
        """Get current user email."""
        return self.token.email if self.token else ""
