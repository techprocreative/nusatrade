"""Login Window for NusaTrade Connector."""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QCheckBox, QMessageBox,
    QFrame, QSizePolicy, QSpacerItem
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

from core.auth_service import AuthService, get_server_url, get_frontend_url


logger = logging.getLogger(__name__)


class LoginWindow(QDialog):
    """Login dialog for authentication."""

    login_successful = pyqtSignal(str)

    def __init__(self, auth_service: AuthService, parent=None):
        super().__init__(parent)
        self.auth = auth_service
        self.setWindowTitle("NusaTrade Connector - Login")
        self.setFixedSize(480, 520)
        self.setModal(True)
        
        # Set dark background
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
            }
            QLabel {
                color: #ffffff;
            }
        """)

        self._build_ui()

    def _build_ui(self):
        """Build the login UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Main container with padding
        container = QFrame()
        container.setStyleSheet("background-color: transparent;")
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(16)
        container_layout.setContentsMargins(48, 40, 48, 32)

        # Logo/Title
        title = QLabel("NusaTrade")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        title.setStyleSheet("color: #4fc3f7; margin-bottom: 0px;")
        container_layout.addWidget(title)

        subtitle = QLabel("MT5 Connector")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Segoe UI", 14))
        subtitle.setStyleSheet("color: #7f8c8d; margin-top: 0px;")
        container_layout.addWidget(subtitle)

        # Spacer
        container_layout.addSpacerItem(QSpacerItem(20, 24, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed))

        # Form container
        form_container = QFrame()
        form_container.setStyleSheet("""
            QFrame {
                background-color: #16213e;
                border-radius: 12px;
            }
        """)
        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(16)
        form_layout.setContentsMargins(28, 28, 28, 28)

        # Email field
        email_label = QLabel("Email")
        email_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        email_label.setStyleSheet("color: #b0b0b0; margin-bottom: 4px;")
        form_layout.addWidget(email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        self.email_input.setFont(QFont("Segoe UI", 13))
        self.email_input.setMinimumHeight(48)
        self.email_input.setStyleSheet(self._input_style())
        form_layout.addWidget(self.email_input)

        # Password field
        password_label = QLabel("Password")
        password_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        password_label.setStyleSheet("color: #b0b0b0; margin-bottom: 4px; margin-top: 8px;")
        form_layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setFont(QFont("Segoe UI", 13))
        self.password_input.setMinimumHeight(48)
        self.password_input.setStyleSheet(self._input_style())
        self.password_input.returnPressed.connect(self._on_login)
        form_layout.addWidget(self.password_input)

        # Remember me checkbox
        self.remember_checkbox = QCheckBox("Remember me")
        self.remember_checkbox.setChecked(True)
        self.remember_checkbox.setFont(QFont("Segoe UI", 11))
        self.remember_checkbox.setStyleSheet("""
            QCheckBox {
                color: #b0b0b0;
                margin-top: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #4a4a6a;
                border-radius: 4px;
                background-color: transparent;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #4fc3f7;
                border-radius: 4px;
                background-color: #4fc3f7;
            }
        """)
        form_layout.addWidget(self.remember_checkbox)

        container_layout.addWidget(form_container)

        # Error message
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setFont(QFont("Segoe UI", 11))
        self.error_label.setStyleSheet("color: #e74c3c; margin-top: 8px;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        container_layout.addWidget(self.error_label)

        # Login button
        self.login_btn = QPushButton("Login")
        self.login_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.login_btn.setMinimumHeight(52)
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #4fc3f7;
                color: #1a1a2e;
                border: none;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #81d4fa;
            }
            QPushButton:pressed {
                background-color: #29b6f6;
            }
            QPushButton:disabled {
                background-color: #3a3a5a;
                color: #6a6a8a;
            }
        """)
        self.login_btn.clicked.connect(self._on_login)
        container_layout.addWidget(self.login_btn)

        # Spacer
        container_layout.addStretch()

        # Server info
        server_label = QLabel(f"Server: {get_server_url()}")
        server_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        server_label.setFont(QFont("Segoe UI", 9))
        server_label.setStyleSheet("color: #4a4a6a;")
        container_layout.addWidget(server_label)

        # Register link
        register_label = QLabel(f"Don't have an account? <a href='{get_frontend_url()}/register' style='color: #4fc3f7;'>Register here</a>")
        register_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        register_label.setFont(QFont("Segoe UI", 10))
        register_label.setStyleSheet("color: #7f8c8d;")
        register_label.setOpenExternalLinks(True)
        container_layout.addWidget(register_label)

        layout.addWidget(container)

    def _input_style(self) -> str:
        return """
            QLineEdit {
                background-color: #1a1a2e;
                border: 2px solid #3a3a5a;
                border-radius: 8px;
                padding: 10px 16px;
                color: #ffffff;
                selection-background-color: #4fc3f7;
            }
            QLineEdit:focus {
                border-color: #4fc3f7;
            }
            QLineEdit::placeholder {
                color: #5a5a7a;
            }
        """

    def _on_login(self):
        """Handle login button click."""
        email = self.email_input.text().strip()
        password = self.password_input.text()

        if not email:
            self._show_error("Please enter your email")
            return
        if not password:
            self._show_error("Please enter your password")
            return

        # Disable UI during login
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Connecting...")
        self.error_label.hide()

        # Attempt login
        success, message = self.auth.login(
            email=email,
            password=password,
            remember=self.remember_checkbox.isChecked()
        )

        self.login_btn.setEnabled(True)
        self.login_btn.setText("Login")

        if success:
            logger.info(f"Login successful for {email}")
            self.login_successful.emit(email)
            self.accept()
        else:
            self._show_error(message)

    def _show_error(self, message: str):
        """Show error message."""
        self.error_label.setText(message)
        self.error_label.show()


class AutoLoginChecker:
    """Check for saved credentials and auto-login."""

    def __init__(self, auth_service: AuthService):
        self.auth = auth_service

    def try_auto_login(self) -> bool:
        """Try to login with saved credentials."""
        return self.auth.load_saved_token()
