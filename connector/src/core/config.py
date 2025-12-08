"""Configuration management for connector."""

import os
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class MT5Config:
    """MetaTrader 5 connection configuration."""
    login: int = 0
    password: str = ""
    server: str = ""
    path: str = r"C:\Program Files\MetaTrader 5\terminal64.exe"
    timeout: int = 10000


@dataclass
class ServerConfig:
    """Backend server configuration."""
    host: str = "localhost"
    port: int = 8000
    use_ssl: bool = False
    token: str = ""

    @property
    def ws_url(self) -> str:
        protocol = "wss" if self.use_ssl else "ws"
        return f"{protocol}://{self.host}:{self.port}/ws/connector"

    @property
    def api_url(self) -> str:
        protocol = "https" if self.use_ssl else "http"
        return f"{protocol}://{self.host}:{self.port}/api/v1"


@dataclass
class AppConfig:
    """Application configuration."""
    mt5: MT5Config = field(default_factory=MT5Config)
    server: ServerConfig = field(default_factory=ServerConfig)
    auto_connect: bool = False
    heartbeat_interval: int = 30
    reconnect_interval: int = 5
    max_reconnect_attempts: int = 10
    log_level: str = "INFO"


class ConfigManager:
    """Manage application configuration with persistence."""

    CONFIG_FILE = "config.json"
    
    def __init__(self, config_dir: Optional[Path] = None):
        if config_dir is None:
            # Use AppData on Windows, ~/.config on Linux
            if os.name == "nt":
                config_dir = Path(os.environ.get("APPDATA", ".")) / "ForexAIConnector"
            else:
                config_dir = Path.home() / ".config" / "forexai-connector"
        
        self.config_dir = config_dir
        self.config_path = config_dir / self.CONFIG_FILE
        self.config = AppConfig()

    def load(self) -> AppConfig:
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    data = json.load(f)
                
                # Parse nested configs
                mt5_data = data.pop("mt5", {})
                server_data = data.pop("server", {})
                
                self.config = AppConfig(
                    mt5=MT5Config(**mt5_data),
                    server=ServerConfig(**server_data),
                    **data
                )
            except Exception as e:
                print(f"Error loading config: {e}")
                self.config = AppConfig()
        
        return self.config

    def save(self):
        """Save configuration to file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        data = {
            "mt5": asdict(self.config.mt5),
            "server": asdict(self.config.server),
            "auto_connect": self.config.auto_connect,
            "heartbeat_interval": self.config.heartbeat_interval,
            "reconnect_interval": self.config.reconnect_interval,
            "max_reconnect_attempts": self.config.max_reconnect_attempts,
            "log_level": self.config.log_level,
        }
        
        # Don't save sensitive data
        data["mt5"]["password"] = ""
        data["server"]["token"] = ""
        
        with open(self.config_path, "w") as f:
            json.dump(data, f, indent=2)

    def update_mt5(self, **kwargs):
        """Update MT5 configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config.mt5, key):
                setattr(self.config.mt5, key, value)

    def update_server(self, **kwargs):
        """Update server configuration."""
        for key, value in kwargs.items():
            if hasattr(self.config.server, key):
                setattr(self.config.server, key, value)
