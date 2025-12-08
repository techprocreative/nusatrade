"""Main Window for ForexAI Connector."""

import logging
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit, QSpinBox,
    QGroupBox, QFormLayout, QTabWidget, QStatusBar,
    QMessageBox, QCheckBox, QComboBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QPalette, QFont

from core.mt5_service import MT5Service
from core.ws_service import WebSocketService, ConnectionState, MessageHandler
from core.config import ConfigManager


logger = logging.getLogger(__name__)


class SignalBridge(QObject):
    """Bridge for thread-safe signal emission."""
    state_changed = pyqtSignal(str)
    message_received = pyqtSignal(str)
    log_message = pyqtSignal(str, str)  # message, level


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, auth_service=None):
        super().__init__()
        self.auth = auth_service
        self.setWindowTitle("ForexAI Connector")
        self.setMinimumSize(800, 600)

        # Show user email in title if authenticated
        if self.auth and self.auth.is_authenticated():
            self.setWindowTitle(f"ForexAI Connector - {self.auth.get_user_email()}")

        # Services
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load()
        self.mt5 = MT5Service()
        self.ws: Optional[WebSocketService] = None
        self.message_handler: Optional[MessageHandler] = None

        # Signal bridge for thread-safe updates
        self.signals = SignalBridge()
        self.signals.state_changed.connect(self._on_state_changed)
        self.signals.message_received.connect(self._on_message_received)
        self.signals.log_message.connect(self._log)

        self._build_ui()
        self._setup_timers()

        # Auto connect if configured
        if self.config.auto_connect:
            QTimer.singleShot(1000, self._connect)

    def _build_ui(self):
        """Build the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)

        # Header with status
        header = self._create_header()
        main_layout.addLayout(header)

        # Tab widget
        tabs = QTabWidget()
        tabs.addTab(self._create_connection_tab(), "Connection")
        tabs.addTab(self._create_trading_tab(), "Trading")
        tabs.addTab(self._create_settings_tab(), "Settings")
        tabs.addTab(self._create_logs_tab(), "Logs")
        main_layout.addWidget(tabs)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _create_header(self) -> QHBoxLayout:
        """Create header with connection status."""
        layout = QHBoxLayout()

        # Connection status indicators
        self.mt5_status = QLabel("MT5: ⚫ Disconnected")
        self.ws_status = QLabel("Server: ⚫ Disconnected")
        
        self.mt5_status.setStyleSheet("font-weight: bold; padding: 5px;")
        self.ws_status.setStyleSheet("font-weight: bold; padding: 5px;")

        layout.addWidget(self.mt5_status)
        layout.addWidget(self.ws_status)
        layout.addStretch()

        # Quick connect button
        self.connect_btn = QPushButton("Connect All")
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.connect_btn.clicked.connect(self._connect)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        self.disconnect_btn.clicked.connect(self._disconnect)
        self.disconnect_btn.setEnabled(False)

        layout.addWidget(self.connect_btn)
        layout.addWidget(self.disconnect_btn)

        return layout

    def _create_connection_tab(self) -> QWidget:
        """Create connection configuration tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # MT5 Configuration
        mt5_group = QGroupBox("MetaTrader 5 Configuration")
        mt5_layout = QFormLayout()

        self.mt5_login = QSpinBox()
        self.mt5_login.setMaximum(999999999)
        self.mt5_login.setValue(self.config.mt5.login)

        self.mt5_password = QLineEdit()
        self.mt5_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.mt5_password.setText(self.config.mt5.password)

        self.mt5_server = QLineEdit()
        self.mt5_server.setText(self.config.mt5.server)
        self.mt5_server.setPlaceholderText("e.g., ICMarketsSC-Demo")

        mt5_layout.addRow("Login:", self.mt5_login)
        mt5_layout.addRow("Password:", self.mt5_password)
        mt5_layout.addRow("Server:", self.mt5_server)
        mt5_group.setLayout(mt5_layout)

        # Server Configuration
        server_group = QGroupBox("Backend Server Configuration")
        server_layout = QFormLayout()

        self.server_host = QLineEdit()
        self.server_host.setText(self.config.server.host)

        self.server_port = QSpinBox()
        self.server_port.setMaximum(65535)
        self.server_port.setValue(self.config.server.port)

        self.server_ssl = QCheckBox("Use SSL")
        self.server_ssl.setChecked(self.config.server.use_ssl)

        self.server_token = QLineEdit()
        self.server_token.setEchoMode(QLineEdit.EchoMode.Password)
        self.server_token.setText(self.config.server.token)
        self.server_token.setPlaceholderText("JWT Token from dashboard")

        server_layout.addRow("Host:", self.server_host)
        server_layout.addRow("Port:", self.server_port)
        server_layout.addRow("", self.server_ssl)
        server_layout.addRow("Auth Token:", self.server_token)
        server_group.setLayout(server_layout)

        # Account info display
        account_group = QGroupBox("Account Information")
        account_layout = QFormLayout()

        self.account_balance = QLabel("—")
        self.account_equity = QLabel("—")
        self.account_margin = QLabel("—")
        self.account_profit = QLabel("—")

        account_layout.addRow("Balance:", self.account_balance)
        account_layout.addRow("Equity:", self.account_equity)
        account_layout.addRow("Free Margin:", self.account_margin)
        account_layout.addRow("Profit:", self.account_profit)
        account_group.setLayout(account_layout)

        layout.addWidget(mt5_group)
        layout.addWidget(server_group)
        layout.addWidget(account_group)
        layout.addStretch()

        return widget

    def _create_trading_tab(self) -> QWidget:
        """Create trading/positions tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Open positions
        positions_group = QGroupBox("Open Positions")
        positions_layout = QVBoxLayout()

        self.positions_text = QTextEdit()
        self.positions_text.setReadOnly(True)
        self.positions_text.setPlaceholderText("No open positions")

        refresh_btn = QPushButton("Refresh Positions")
        refresh_btn.clicked.connect(self._refresh_positions)

        positions_layout.addWidget(self.positions_text)
        positions_layout.addWidget(refresh_btn)
        positions_group.setLayout(positions_layout)

        layout.addWidget(positions_group)

        return widget

    def _create_settings_tab(self) -> QWidget:
        """Create settings tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        settings_group = QGroupBox("Application Settings")
        settings_layout = QFormLayout()

        self.auto_connect = QCheckBox("Auto-connect on startup")
        self.auto_connect.setChecked(self.config.auto_connect)

        self.heartbeat_interval = QSpinBox()
        self.heartbeat_interval.setRange(10, 120)
        self.heartbeat_interval.setValue(self.config.heartbeat_interval)
        self.heartbeat_interval.setSuffix(" seconds")

        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level.setCurrentText(self.config.log_level)

        settings_layout.addRow("", self.auto_connect)
        settings_layout.addRow("Heartbeat Interval:", self.heartbeat_interval)
        settings_layout.addRow("Log Level:", self.log_level)
        settings_group.setLayout(settings_layout)

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save_settings)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px;
                border-radius: 4px;
            }
        """)

        layout.addWidget(settings_group)
        layout.addWidget(save_btn)
        layout.addStretch()

        return widget

    def _create_logs_tab(self) -> QWidget:
        """Create logs tab."""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Consolas", 10))

        clear_btn = QPushButton("Clear Logs")
        clear_btn.clicked.connect(self.log_view.clear)

        layout.addWidget(self.log_view)
        layout.addWidget(clear_btn)

        return widget

    def _setup_timers(self):
        """Setup periodic timers."""
        # Account info update timer
        self.account_timer = QTimer()
        self.account_timer.timeout.connect(self._update_account_info)
        self.account_timer.setInterval(5000)  # 5 seconds

    def _connect(self):
        """Connect to MT5 and server."""
        self._log("Connecting...", "INFO")

        # Update config from UI
        self.config.mt5.login = self.mt5_login.value()
        self.config.mt5.password = self.mt5_password.text()
        self.config.mt5.server = self.mt5_server.text()
        self.config.server.host = self.server_host.text()
        self.config.server.port = self.server_port.value()
        self.config.server.use_ssl = self.server_ssl.isChecked()
        self.config.server.token = self.server_token.text()

        # Connect to MT5
        try:
            mt5_connected = self.mt5.connect(
                login=self.config.mt5.login,
                password=self.config.mt5.password,
                server=self.config.mt5.server,
            )

            if mt5_connected:
                self.mt5_status.setText("MT5: 🟢 Connected")
                self._log("MT5 connected successfully", "INFO")
                self._update_account_info()
                self.account_timer.start()
            else:
                self.mt5_status.setText("MT5: 🔴 Failed")
                self._log("MT5 connection failed", "ERROR")

        except Exception as e:
            self._log(f"MT5 error: {e}", "ERROR")
            self.mt5_status.setText("MT5: 🔴 Error")

        # Connect to WebSocket server
        try:
            # Use auth service if available (auto connection)
            if self.auth and self.auth.is_authenticated():
                ws_url = self.auth.get_ws_url()
                ws_token = self.auth.get_access_token()
                self._log(f"Using authenticated connection", "INFO")
            else:
                ws_url = self.config.server.ws_url
                ws_token = self.config.server.token

            self.ws = WebSocketService(
                url=ws_url,
                token=ws_token,
                heartbeat_interval=self.config.heartbeat_interval,
            )

            self.message_handler = MessageHandler(self.mt5)

            def on_state_change(state: ConnectionState):
                self.signals.state_changed.emit(state.value)

            def on_message(msg: dict):
                response = self.message_handler.handle(msg)
                if response:
                    self.ws.send_sync(response)
                self.signals.message_received.emit(str(msg.get("type", "Unknown")))

            self.ws.on_state_change(on_state_change)
            self.ws.on_message(on_message)
            self.ws.start()

        except Exception as e:
            self._log(f"WebSocket error: {e}", "ERROR")

        self.connect_btn.setEnabled(False)
        self.disconnect_btn.setEnabled(True)

    def _disconnect(self):
        """Disconnect from all services."""
        if self.ws:
            self.ws.stop()
            self.ws = None

        self.mt5.shutdown()

        self.account_timer.stop()

        self.mt5_status.setText("MT5: ⚫ Disconnected")
        self.ws_status.setText("Server: ⚫ Disconnected")

        self.connect_btn.setEnabled(True)
        self.disconnect_btn.setEnabled(False)

        self._log("Disconnected", "INFO")

    def _on_state_changed(self, state: str):
        """Handle WebSocket state change."""
        icons = {
            "connected": "🟢",
            "connecting": "🟡",
            "reconnecting": "🟡",
            "disconnected": "⚫",
            "error": "🔴",
        }
        icon = icons.get(state, "⚫")
        self.ws_status.setText(f"Server: {icon} {state.capitalize()}")
        self._log(f"WebSocket: {state}", "INFO")

    def _on_message_received(self, msg_type: str):
        """Handle received message notification."""
        self.status_bar.showMessage(f"Received: {msg_type}", 3000)

    def _update_account_info(self):
        """Update account information display."""
        account = self.mt5.get_account_info()
        if account:
            self.account_balance.setText(f"${account.balance:,.2f}")
            self.account_equity.setText(f"${account.equity:,.2f}")
            self.account_margin.setText(f"${account.free_margin:,.2f}")
            
            profit_color = "green" if account.profit >= 0 else "red"
            self.account_profit.setText(f"${account.profit:,.2f}")
            self.account_profit.setStyleSheet(f"color: {profit_color};")

    def _refresh_positions(self):
        """Refresh open positions display."""
        positions = self.mt5.get_positions()
        if positions:
            text = ""
            for p in positions:
                text += f"#{p.ticket} | {p.symbol} | {p.type} | {p.volume} lots | P/L: ${p.profit:,.2f}\n"
            self.positions_text.setText(text)
        else:
            self.positions_text.setText("No open positions")

    def _save_settings(self):
        """Save settings to config file."""
        self.config.auto_connect = self.auto_connect.isChecked()
        self.config.heartbeat_interval = self.heartbeat_interval.value()
        self.config.log_level = self.log_level.currentText()

        self.config_manager.config = self.config
        self.config_manager.save()

        QMessageBox.information(self, "Settings", "Settings saved successfully!")
        self._log("Settings saved", "INFO")

    def _log(self, message: str, level: str = "INFO"):
        """Add message to log view."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {
            "DEBUG": "#888888",
            "INFO": "#ffffff",
            "WARNING": "#ff9800",
            "ERROR": "#f44336",
        }
        color = colors.get(level, "#ffffff")
        html = f'<span style="color: {color}">[{timestamp}] [{level}] {message}</span>'
        self.log_view.append(html)

    def closeEvent(self, event):
        """Handle window close."""
        self._disconnect()
        super().closeEvent(event)
