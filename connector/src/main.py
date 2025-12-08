"""Main entry point for ForexAI Connector."""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QIcon

from core.config import ConfigManager
from core.auth_service import AuthService, get_server_url
from ui.login_window import LoginWindow, AutoLoginChecker
from ui.main_window import MainWindow


def setup_logging(level: str = "INFO"):
    """Configure application logging."""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Log file path
    if sys.platform == "win32":
        import os
        log_dir = Path(os.environ.get("APPDATA", ".")) / "ForexAIConnector"
    else:
        log_dir = Path.home() / ".config" / "forexai-connector"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "connector.log"
    
    logging.basicConfig(
        level=getattr(logging, level),
        format=log_format,
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(str(log_file), encoding="utf-8"),
        ]
    )


def setup_dark_theme(app: QApplication):
    """Apply dark theme to application."""
    from PyQt6.QtGui import QPalette, QColor
    from PyQt6.QtCore import Qt
    
    app.setStyle("Fusion")
    
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Base, QColor(35, 35, 35))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(25, 25, 25))
    palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
    palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
    palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(35, 35, 35))
    app.setPalette(palette)


def main():
    """Main application entry point."""
    # Load config
    config_manager = ConfigManager()
    config = config_manager.load()
    
    # Setup logging
    setup_logging(config.log_level)
    logger = logging.getLogger(__name__)
    logger.info("Starting ForexAI Connector...")
    logger.info(f"Server: {get_server_url()}")

    # Create Qt application
    app = QApplication(sys.argv)
    app.setApplicationName("ForexAI Connector")
    app.setOrganizationName("ForexAI")
    
    # Apply dark theme
    setup_dark_theme(app)

    # Load icon if exists
    icon_path = Path(__file__).parent.parent / "resources" / "icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # Initialize auth service
    auth_service = AuthService()

    # Try auto-login with saved credentials
    auto_login = AutoLoginChecker(auth_service)
    logged_in = auto_login.try_auto_login()

    if not logged_in:
        # Show login window
        login_window = LoginWindow(auth_service)
        result = login_window.exec()
        
        if result != LoginWindow.DialogCode.Accepted:
            # User cancelled login
            logger.info("Login cancelled by user")
            sys.exit(0)

    logger.info(f"Logged in as: {auth_service.get_user_email()}")

    # Create and show main window with auth
    window = MainWindow(auth_service=auth_service)
    window.show()

    logger.info("Application started")

    # Run event loop
    exit_code = app.exec()
    
    logger.info("Application closed")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
