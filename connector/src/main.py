"""Main entry point for ForexAI Connector."""

import sys
import os
import traceback
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


def handle_exception(exc_type, exc_value, exc_traceback):
    """Handle uncaught exceptions."""
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logger = logging.getLogger(__name__)
    logger.critical("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    
    # Show error dialog
    error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    try:
        app = QApplication.instance()
        if not app:
            app = QApplication(sys.argv)
        
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setText("An unexpected error occurred")
        msg.setInformativeText(str(exc_value))
        msg.setDetailedText(error_msg)
        msg.setWindowTitle("Error")
        msg.exec()
    except:
        # If Qt fails, write to file on Desktop
        try:
            desktop = Path(os.environ.get("USERPROFILE", "")) / "Desktop"
            with open(desktop / "forexai_crash.txt", "w") as f:
                f.write(error_msg)
        except:
            pass
    
    # Keep console open
    print("\nCRITICAL ERROR OCCURRED!")
    # Keep console open
    print("\nCRITICAL ERROR OCCURRED!")
    print(error_msg)
    input("\nPress Enter to exit...")
    sys.exit(1)

def main():
    """Main application entry point."""
    # Setup global exception handler
    sys.excepthook = handle_exception

    try:
        # ... (rest of the code) ...
        
    except Exception as e:
        # Catch errors during startup
        handle_exception(type(e), e, e.__traceback__)
        sys.exit(1)


if __name__ == "__main__":
    main()
