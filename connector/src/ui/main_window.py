"""Main Window for NusaTrade Connector."""

import logging
from datetime import datetime
from typing import Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit, QSpinBox,
    QGroupBox, QFormLayout, QTabWidget, QStatusBar,
    QMessageBox, QCheckBox, QComboBox, QFrame
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QColor, QPalette, QFont

from core.mt5_service import MT5Service
from core.ws_service import WebSocketService, ConnectionState, MessageHandler
from core.config import ConfigManager
from core.auth_service import AuthService


logger = logging.getLogger(__name__)


class SignalBridge(QObject):
    """Bridge for thread-safe signal emission."""
    state_changed = pyqtSignal(str)
    message_received = pyqtSignal(str)
    log_message = pyqtSignal(str, str)


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self, auth_service: AuthService = None):
        super().__init__()
        self.auth = auth_service
        
        # Set window title with user email
        title = "NusaTrade Connector"
        if self.auth and self.auth.is_authenticated():
            title += f" - {self.auth.get_user_email()}"
        self.setWindowTitle(title)
        self.setMinimumSize(700, 550)

        # Services
        self.config_manager = ConfigManager()
        self.config = self.config_manager.load()
        self.mt5 = MT5Service()
        self.ws: Optional[WebSocketService] = None
        self.message_handler: Optional[MessageHandler] = None
        
        # Current broker connection ID (from backend)
        self.current_connection_id: Optional[str] = None

        # Signal bridge for thread-safe updates
        self.signals = SignalBridge()
        self.signals.state_changed.connect(self._on_state_changed)
        self.signals.message_received.connect(self._on_message_received)
        self.signals.log_message.connect(self._log)

        self._build_ui()
        self._setup_timers()

    def _build_ui(self):
        """Build the user interface."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

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
        self.status_bar.showMessage("Ready - Enter MT5 credentials and click Connect")

    def _create_header(self) -> QHBoxLayout:
        """Create header with connection status."""
        layout = QHBoxLayout()

        # Connection status indicators
        status_frame = QFrame()
        status_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2a2a;
                border-radius: 8px;
                padding: 10px;
            }
        """)
        status_layout = QHBoxLayout(status_frame)
        status_layout.setSpacing(20)

        self.mt5_status = QLabel("MT5: ⚫ Disconnected")
        self.ws_status = QLabel("Server: ⚫ Disconnected")
        
        self.mt5_status.setStyleSheet("font-weight: bold; font-size: 13px;")
        self.ws_status.setStyleSheet("font-weight: bold; font-size: 13px;")

        status_layout.addWidget(self.mt5_status)
        status_layout.addWidget(self.ws_status)

        layout.addWidget(status_frame)
        layout.addStretch()

        # Connect/Disconnect buttons
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setMinimumSize(120, 40)
        self.connect_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 10px 25px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #43A047;
            }
            QPushButton:disabled {
                background-color: #555555;
            }
        """)
        self.connect_btn.clicked.connect(self._connect)

        self.disconnect_btn = QPushButton("Disconnect")
        self.disconnect_btn.setMinimumSize(120, 40)
        self.disconnect_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 10px 25px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 13px;
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
        layout.setSpacing(20)

        # MT5 Configuration
        mt5_group = QGroupBox("MetaTrader 5 Credentials")
        mt5_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #444;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
            }
        """)
        mt5_layout = QFormLayout()
        mt5_layout.setSpacing(12)
        mt5_layout.setContentsMargins(20, 25, 20, 20)

        # MT5 Login
        self.mt5_login = QSpinBox()
        self.mt5_login.setMaximum(999999999)
        self.mt5_login.setValue(self.config.mt5.login)
        self.mt5_login.setMinimumHeight(40)
        self.mt5_login.setFont(QFont("Arial", 12))
        self.mt5_login.setStyleSheet(self._input_style())

        # MT5 Password
        self.mt5_password = QLineEdit()
        self.mt5_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.mt5_password.setText(self.config.mt5.password)
        self.mt5_password.setMinimumHeight(40)
        self.mt5_password.setFont(QFont("Arial", 12))
        self.mt5_password.setStyleSheet(self._input_style())
        self.mt5_password.setPlaceholderText("MT5 Password")

        # MT5 Server
        self.mt5_server = QLineEdit()
        self.mt5_server.setText(self.config.mt5.server)
        self.mt5_server.setMinimumHeight(40)
        self.mt5_server.setFont(QFont("Arial", 12))
        self.mt5_server.setStyleSheet(self._input_style())
        self.mt5_server.setPlaceholderText("e.g., ICMarketsSC-Demo")

        label_style = "font-size: 13px; color: #aaa;"
        
        login_label = QLabel("Login:")
        login_label.setStyleSheet(label_style)
        mt5_layout.addRow(login_label, self.mt5_login)
        
        pass_label = QLabel("Password:")
        pass_label.setStyleSheet(label_style)
        mt5_layout.addRow(pass_label, self.mt5_password)
        
        server_label = QLabel("Server:")
        server_label.setStyleSheet(label_style)
        mt5_layout.addRow(server_label, self.mt5_server)
        
        mt5_group.setLayout(mt5_layout)

        # Detected Info (shown after connection)
        self.detected_group = QGroupBox("Detected Information")
        self.detected_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #4CAF50;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
                color: #4CAF50;
            }
        """)
        detected_layout = QFormLayout()
        detected_layout.setSpacing(10)
        detected_layout.setContentsMargins(20, 25, 20, 20)

        self.detected_broker = QLabel("—")
        self.detected_account = QLabel("—")
        self.detected_server = QLabel("—")
        
        for label in [self.detected_broker, self.detected_account, self.detected_server]:
            label.setStyleSheet("font-size: 13px; color: #4CAF50;")

        detected_layout.addRow(QLabel("Broker:"), self.detected_broker)
        detected_layout.addRow(QLabel("Account:"), self.detected_account)
        detected_layout.addRow(QLabel("Server:"), self.detected_server)
        self.detected_group.setLayout(detected_layout)
        self.detected_group.hide()  # Hidden until connected

        # Account info display
        account_group = QGroupBox("Account Information")
        account_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #444;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
            }
        """)
        account_layout = QFormLayout()
        account_layout.setSpacing(10)
        account_layout.setContentsMargins(20, 25, 20, 20)

        self.account_balance = QLabel("—")
        self.account_equity = QLabel("—")
        self.account_margin = QLabel("—")
        self.account_profit = QLabel("—")

        for label in [self.account_balance, self.account_equity, self.account_margin, self.account_profit]:
            label.setStyleSheet("font-size: 13px;")

        account_layout.addRow(QLabel("Balance:"), self.account_balance)
        account_layout.addRow(QLabel("Equity:"), self.account_equity)
        account_layout.addRow(QLabel("Free Margin:"), self.account_margin)
        account_layout.addRow(QLabel("Profit:"), self.account_profit)
        account_group.setLayout(account_layout)

        layout.addWidget(mt5_group)
        layout.addWidget(self.detected_group)
        layout.addWidget(account_group)
        layout.addStretch()

        return widget

    def _input_style(self) -> str:
        return """
            QLineEdit, QSpinBox {
                background-color: #3a3a3a;
                border: 2px solid #555;
                border-radius: 6px;
                padding: 8px 12px;
                color: white;
                font-size: 13px;
            }
            QLineEdit:focus, QSpinBox:focus {
                border-color: #2196F3;
            }
        """

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
        self.positions_text.setFont(QFont("Consolas", 11))

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
        settings_layout.setSpacing(15)
        settings_layout.setContentsMargins(20, 25, 20, 20)

        self.auto_connect = QCheckBox("Auto-connect on startup")
        self.auto_connect.setChecked(self.config.auto_connect)

        self.heartbeat_interval = QSpinBox()
        self.heartbeat_interval.setRange(10, 120)
        self.heartbeat_interval.setValue(self.config.heartbeat_interval)
        self.heartbeat_interval.setSuffix(" seconds")
        self.heartbeat_interval.setMinimumHeight(35)

        self.log_level = QComboBox()
        self.log_level.addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        self.log_level.setCurrentText(self.config.log_level)
        self.log_level.setMinimumHeight(35)

        settings_layout.addRow("", self.auto_connect)
        settings_layout.addRow("Heartbeat Interval:", self.heartbeat_interval)
        settings_layout.addRow("Log Level:", self.log_level)
        settings_group.setLayout(settings_layout)

        # Logout button
        logout_btn = QPushButton("Logout")
        logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                padding: 12px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #f57c00;
            }
        """)
        logout_btn.clicked.connect(self._logout)

        save_btn = QPushButton("Save Settings")
        save_btn.clicked.connect(self._save_settings)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #43A047;
            }
        """)

        layout.addWidget(settings_group)
        layout.addWidget(save_btn)
        layout.addStretch()
        layout.addWidget(logout_btn)

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
        self.account_timer = QTimer()
        self.account_timer.timeout.connect(self._update_account_info)
        self.account_timer.setInterval(5000)

    def _connect(self):
        """Connect to MT5 and server."""
        self._log("Connecting...", "INFO")
        self.connect_btn.setEnabled(False)
        self.connect_btn.setText("Connecting...")

        # Update config from UI
        self.config.mt5.login = self.mt5_login.value()
        self.config.mt5.password = self.mt5_password.text()
        self.config.mt5.server = self.mt5_server.text()

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
                
                # Auto-detect broker info
                account_info = self.mt5.get_account_info()
                if account_info:
                    self.detected_broker.setText(account_info.company)
                    self.detected_account.setText(str(account_info.login))
                    self.detected_server.setText(account_info.server)
                    self.detected_group.show()
                    
                    self._log(f"Detected: {account_info.company} - {account_info.login}", "INFO")
                    
                    # Auto-register broker connection
                    self._register_broker_connection(account_info)
                
                self._update_account_info()
                self.account_timer.start()
            else:
                self.mt5_status.setText("MT5: 🔴 Failed")
                self._log("MT5 connection failed - check credentials", "ERROR")
                self.connect_btn.setEnabled(True)
                self.connect_btn.setText("Connect")
                return

        except Exception as e:
            self._log(f"MT5 error: {e}", "ERROR")
            self.mt5_status.setText("MT5: 🔴 Error")
            self.connect_btn.setEnabled(True)
            self.connect_btn.setText("Connect")
            return

        # Connect to WebSocket server (using auth service)
        try:
            if self.auth and self.auth.is_authenticated():
                ws_url = self.auth.get_ws_url()
                ws_token = self.auth.get_access_token()
                
                # Add connection_id to URL if we have one
                if self.current_connection_id:
                    ws_url = f"{ws_url}?connection_id={self.current_connection_id}"
                
                self._log(f"Connecting to server...", "INFO")
            else:
                self._log("Not authenticated - please restart and login", "ERROR")
                return

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

        self.connect_btn.setText("Connected")
        self.disconnect_btn.setEnabled(True)

    def _register_broker_connection(self, account_info):
        """Register or update broker connection in backend."""
        if not self.auth or not self.auth.is_authenticated():
            return
            
        try:
            import requests
            
            server_url = self.auth.server_url
            token = self.auth.get_access_token()
            headers = {"Authorization": f"Bearer {token}"}
            
            # Check existing connections
            resp = requests.get(
                f"{server_url}/api/v1/brokers/connections",
                headers=headers,
                timeout=10
            )
            
            if resp.status_code == 200:
                connections = resp.json()
                
                # Find matching connection
                for conn in connections:
                    if (conn.get("account_number") == str(account_info.login) and
                        conn.get("server") == account_info.server):
                        self.current_connection_id = conn["id"]
                        self._log(f"Using existing connection: {conn['id'][:8]}...", "INFO")
                        return
                
                # Create new connection
                resp = requests.post(
                    f"{server_url}/api/v1/brokers/connections",
                    headers=headers,
                    json={
                        "broker_name": account_info.company,
                        "account_number": str(account_info.login),
                        "server": account_info.server,
                    },
                    timeout=10
                )
                
                if resp.status_code == 201:
                    data = resp.json()
                    self.current_connection_id = data["id"]
                    self._log(f"Registered new connection: {data['id'][:8]}...", "INFO")
                else:
                    self._log(f"Failed to register connection: {resp.status_code}", "WARNING")
                    
        except Exception as e:
            self._log(f"Connection registration error: {e}", "WARNING")

    def _disconnect(self):
        """Disconnect from all services."""
        if self.ws:
            self.ws.stop()
            self.ws = None

        self.mt5.shutdown()
        self.account_timer.stop()

        self.mt5_status.setText("MT5: ⚫ Disconnected")
        self.ws_status.setText("Server: ⚫ Disconnected")
        self.detected_group.hide()

        self.connect_btn.setEnabled(True)
        self.connect_btn.setText("Connect")
        self.disconnect_btn.setEnabled(False)

        self._log("Disconnected", "INFO")

    def _logout(self):
        """Logout and close application."""
        reply = QMessageBox.question(
            self,
            "Logout",
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self._disconnect()
            if self.auth:
                self.auth.logout()
            self.close()
            # Restart application to show login
            import sys
            from PyQt6.QtWidgets import QApplication
            QApplication.quit()

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
        self._log(f"Server: {state}", "INFO")

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
            
            profit_color = "#4CAF50" if account.profit >= 0 else "#f44336"
            self.account_profit.setText(f"${account.profit:,.2f}")
            self.account_profit.setStyleSheet(f"color: {profit_color}; font-size: 13px;")

    def _refresh_positions(self):
        """Refresh open positions display."""
        positions = self.mt5.get_positions()
        if positions:
            text = ""
            for p in positions:
                profit_sign = "+" if p.profit >= 0 else ""
                text += f"#{p.ticket} | {p.symbol} | {p.order_type} | {p.volume} lots | P/L: {profit_sign}${p.profit:,.2f}\n"
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
