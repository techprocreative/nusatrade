"""Login Window for NusaTrade Connector."""

import logging
from typing import Optional
import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QCheckBox, QMessageBox,
    QFrame, QSizePolicy, QSpacerItem, QGraphicsDropShadowEffect
)
from PyQt6.QtCore import Qt, pyqtSignal, QFile, QTextStream
from PyQt6.QtGui import QFont, QColor

from core.auth_service import AuthService, get_server_url, get_frontend_url


logger = logging.getLogger(__name__)


class LoginWindow(QDialog):
    """Login dialog for authentication."""

    login_successful = pyqtSignal(str)

    def __init__(self, auth_service: AuthService, parent=None):
        super().__init__(parent)
        self.auth = auth_service
        self.setWindowTitle("NusaTrade Connector - Login")
        self.setFixedSize(480, 560)  # Increased height to prevent overlap
        self.setModal(True)
        
        # Load stylesheet
        self._load_stylesheet()

        self._build_ui()

    def _load_stylesheet(self):
        """Load external stylesheet."""
        style_path = os.path.join(os.path.dirname(__file__), "styles", "dark_theme.qss")
        if os.path.exists(style_path):
            with open(style_path, "r") as f:
                self.setStyleSheet(f.read())

    def _build_ui(self):
        """Build the login UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        # Main container with padding
        container = QFrame()
        container.setObjectName("MainContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setSpacing(20)
        container_layout.setContentsMargins(40, 40, 40, 30)

        # Logo/Title
        title_container = QFrame()
        title_layout = QVBoxLayout(title_container)
        title_layout.setSpacing(4)
        title_layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel("NusaTrade")
        title.setObjectName("LoginTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 32, QFont.Weight.Bold))
        title_layout.addWidget(title)

        subtitle = QLabel("MT5 Connector")
        subtitle.setObjectName("LoginSubtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Segoe UI", 14))
        title_layout.addWidget(subtitle)
        
        container_layout.addWidget(title_container)

        # Form container
        form_container = QFrame()
        form_container.setObjectName("LoginContainer")
        
        # Add shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        form_container.setGraphicsEffect(shadow)

        form_layout = QVBoxLayout(form_container)
        form_layout.setSpacing(16)
        form_layout.setContentsMargins(24, 24, 24, 24)

        # Email field
        email_group = QFrame()
        email_layout = QVBoxLayout(email_group)
        email_layout.setSpacing(6)
        email_layout.setContentsMargins(0, 0, 0, 0)
        
        email_label = QLabel("Email")
        email_label.setObjectName("InputLabel")
        email_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        email_layout.addWidget(email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Enter your email")
        self.email_input.setFont(QFont("Segoe UI", 13))
        self.email_input.setMinimumHeight(44)
        email_layout.addWidget(self.email_input)
        form_layout.addWidget(email_group)

        # Password field
        pass_group = QFrame()
        pass_layout = QVBoxLayout(pass_group)
        pass_layout.setSpacing(6)
        pass_layout.setContentsMargins(0, 0, 0, 0)

        password_label = QLabel("Password")
        password_label.setObjectName("InputLabel")
        password_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        pass_layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter your password")
        self.password_input.setFont(QFont("Segoe UI", 13))
        self.password_input.setMinimumHeight(44)
        self.password_input.returnPressed.connect(self._on_login)
        pass_layout.addWidget(self.password_input)
        form_layout.addWidget(pass_group)

        # Remember me checkbox
        self.remember_checkbox = QCheckBox("Remember me")
        self.remember_checkbox.setChecked(True)
        self.remember_checkbox.setFont(QFont("Segoe UI", 11))
        form_layout.addWidget(self.remember_checkbox)

        container_layout.addWidget(form_container)

        # Error message
        self.error_label = QLabel("")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setFont(QFont("Segoe UI", 11))
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        container_layout.addWidget(self.error_label)

        # Login button
        self.login_btn = QPushButton("Login")
        self.login_btn.setProperty("class", "login")  # For QSS styling
        self.login_btn.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.login_btn.setMinimumHeight(50)
        self.login_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.login_btn.clicked.connect(self._on_login)
        container_layout.addWidget(self.login_btn)

        # Spacer
        container_layout.addStretch()

        # Footer
        footer_layout = QVBoxLayout()
        footer_layout.setSpacing(4)
        
        # Server info
        server_label = QLabel(f"Server: {get_server_url()}")
        server_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        server_label.setFont(QFont("Segoe UI", 9))
        server_label.setStyleSheet("color: #4a4a6a;")
        footer_layout.addWidget(server_label)

        # Register link
        register_label = QLabel(f"Don't have an account? <a href='{get_frontend_url()}/register' style='color: #4fc3f7; text-decoration: none;'>Register here</a>")
        register_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        register_label.setFont(QFont("Segoe UI", 10))
        register_label.setStyleSheet("color: #7f8c8d;")
        register_label.setOpenExternalLinks(True)
        footer_layout.addWidget(register_label)
        
        container_layout.addLayout(footer_layout)

        layout.addWidget(container)

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
