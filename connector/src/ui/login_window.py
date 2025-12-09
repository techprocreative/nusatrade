"""Login Window for ForexAI Connector."""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QCheckBox, QMessageBox,
    QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QPixmap

from core.auth_service import AuthService, get_server_url


logger = logging.getLogger(__name__)


class LoginWindow(QDialog):
    """Login dialog for authentication."""

    login_successful = pyqtSignal(str)  # Emits user email on success

    def __init__(self, auth_service: AuthService, parent=None):
        super().__init__(parent)
        self.auth = auth_service
        self.setWindowTitle("NusaTrade Connector - Login")
        self.setFixedSize(500, 550)
        self.setModal(True)

        self._build_ui()

    def _build_ui(self):
        """Build the login UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(50, 40, 50, 40)

        # Logo/Title
        title = QLabel("NusaTrade")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Arial", 32, QFont.Weight.Bold))
        title.setStyleSheet("color: #2196F3;")
        layout.addWidget(title)

        subtitle = QLabel("MT5 Connector")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Arial", 16))
        subtitle.setStyleSheet("color: #888888;")
        layout.addWidget(subtitle)

        layout.addSpacing(30)

        # Login form
        form_frame = QFrame()
        form_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-radius: 10px;
                padding: 25px;
            }
        """)
        form_layout = QVBoxLayout(form_frame)
        form_layout.setSpacing(15)

        # Email
        email_label = QLabel("Email")
        email_label.setStyleSheet("color: #aaaaaa; font-size: 14px; font-weight: bold;")
        form_layout.addWidget(email_label)

        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("trader@example.com")
        self.email_input.setMinimumHeight(50)
        self.email_input.setFont(QFont("Arial", 14))
        self.email_input.setStyleSheet(self._input_style())
        form_layout.addWidget(self.email_input)

        # Password
        password_label = QLabel("Password")
        password_label.setStyleSheet("color: #aaaaaa; font-size: 14px; font-weight: bold;")
        form_layout.addWidget(password_label)

        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("••••••••")
        self.password_input.setMinimumHeight(50)
        self.password_input.setFont(QFont("Arial", 14))
        self.password_input.setStyleSheet(self._input_style())
        self.password_input.returnPressed.connect(self._on_login)
        form_layout.addWidget(self.password_input)

        # Remember me
        self.remember_checkbox = QCheckBox("Remember me")
        self.remember_checkbox.setChecked(True)
        self.remember_checkbox.setStyleSheet("color: #aaaaaa; font-size: 13px;")
        form_layout.addWidget(self.remember_checkbox)

        layout.addWidget(form_frame)

        # Error message
        self.error_label = QLabel("")
        self.error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.error_label.setStyleSheet("color: #f44336; font-size: 13px;")
        self.error_label.setWordWrap(True)
        self.error_label.hide()
        layout.addWidget(self.error_label)

        # Login button
        self.login_btn = QPushButton("Login")
        self.login_btn.setMinimumHeight(50)
        self.login_btn.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 15px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #1565C0;
            }
            QPushButton:disabled {
                background-color: #555555;
            }
        """)
        self.login_btn.clicked.connect(self._on_login)
        layout.addWidget(self.login_btn)

        layout.addStretch()

        # Server info
        server_info = QLabel(f"Server: {get_server_url()}")
        server_info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        server_info.setStyleSheet("color: #555555; font-size: 11px;")
        layout.addWidget(server_info)

        # Footer
        footer = QLabel("Don't have an account? Register at nusatrade.com")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet("color: #666666; font-size: 12px;")
        layout.addWidget(footer)

    def _input_style(self) -> str:
        return """
            QLineEdit {
                background-color: #3a3a3a;
                border: 2px solid #555555;
                border-radius: 6px;
                padding: 12px 15px;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #2196F3;
            }
            QLineEdit::placeholder {
                color: #777777;
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
        self.login_btn.setText("Logging in...")
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
        """
        Try to login with saved credentials.
        Returns True if successful.
        """
        return self.auth.load_saved_token()
