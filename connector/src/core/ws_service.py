"""WebSocket Service with reconnection and message handling."""

import asyncio
import json
import logging
import ssl
import time
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, Optional, Any
from threading import Thread

import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode


logger = logging.getLogger(__name__)


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class WebSocketService:
    """WebSocket client with automatic reconnection and message handling."""

    def __init__(
        self,
        url: str = "ws://localhost:8000/ws/connector",
        token: Optional[str] = None,
        reconnect_interval: float = 5.0,
        max_reconnect_attempts: int = 10,
        heartbeat_interval: float = 30.0,
    ):
        self.url = url
        self.token = token
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        self.heartbeat_interval = heartbeat_interval

        self.connection: Optional[websockets.WebSocketClientProtocol] = None
        self.state = ConnectionState.DISCONNECTED
        self.reconnect_attempts = 0
        self.last_heartbeat: Optional[datetime] = None

        # Callbacks
        self._on_message: Optional[Callable[[Dict], None]] = None
        self._on_state_change: Optional[Callable[[ConnectionState], None]] = None
        self._on_error: Optional[Callable[[Exception], None]] = None

        # Event loop management
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._thread: Optional[Thread] = None
        self._running = False
        self._message_queue: asyncio.Queue = asyncio.Queue()

    def set_token(self, token: str):
        """Set authentication token."""
        self.token = token

    def on_message(self, callback: Callable[[Dict], None]):
        """Set message handler callback."""
        self._on_message = callback

    def on_state_change(self, callback: Callable[[ConnectionState], None]):
        """Set state change callback."""
        self._on_state_change = callback

    def on_error(self, callback: Callable[[Exception], None]):
        """Set error callback."""
        self._on_error = callback

    def _set_state(self, state: ConnectionState):
        """Update connection state and notify callback."""
        self.state = state
        if self._on_state_change:
            try:
                self._on_state_change(state)
            except Exception as e:
                logger.error(f"State change callback error: {e}")

    def start(self):
        """Start WebSocket connection in background thread."""
        if self._running:
            return

        self._running = True
        self._thread = Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop WebSocket connection."""
        self._running = False
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(self._disconnect(), self._loop)

    def _run_event_loop(self):
        """Run asyncio event loop in thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connection_loop())
        except Exception as e:
            logger.error(f"Event loop error: {e}")
        finally:
            self._loop.close()

    async def _connection_loop(self):
        """Main connection loop with reconnection logic."""
        while self._running:
            try:
                await self._connect()
                await self._message_loop()
            except ConnectionClosed as e:
                logger.warning(f"Connection closed: {e}")
                self._set_state(ConnectionState.RECONNECTING)
            except InvalidStatusCode as e:
                logger.error(f"Invalid status code: {e}")
                if self._on_error:
                    self._on_error(e)
                self._set_state(ConnectionState.ERROR)
            except Exception as e:
                logger.error(f"Connection error: {e}")
                if self._on_error:
                    self._on_error(e)
                self._set_state(ConnectionState.ERROR)

            if self._running:
                await self._handle_reconnect()

    async def _connect(self):
        """Establish WebSocket connection."""
        self._set_state(ConnectionState.CONNECTING)

        # Build URL with token
        connect_url = self.url
        if self.token:
            separator = "&" if "?" in self.url else "?"
            connect_url = f"{self.url}{separator}token={self.token}"

        # SSL context for wss://
        ssl_context = None
        if connect_url.startswith("wss://"):
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE  # For development

        self.connection = await websockets.connect(
            connect_url,
            ssl=ssl_context,
            ping_interval=self.heartbeat_interval,
            ping_timeout=10,
        )

        self._set_state(ConnectionState.CONNECTED)
        self.reconnect_attempts = 0
        self.last_heartbeat = datetime.now()
        logger.info(f"Connected to {self.url}")

        # Send authentication message
        await self._send_auth()

    async def _send_auth(self):
        """Send authentication message after connection."""
        auth_message = {
            "type": "AUTH",
            "token": self.token,
            "client_type": "connector",
            "timestamp": datetime.now().isoformat(),
        }
        await self.send(auth_message)

    async def _message_loop(self):
        """Listen for incoming messages."""
        async for message in self.connection:
            try:
                data = json.loads(message)
                self.last_heartbeat = datetime.now()

                # Handle pong/heartbeat
                if data.get("type") == "PONG":
                    continue

                # Handle commands
                if self._on_message:
                    self._on_message(data)

            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON message: {e}")
            except Exception as e:
                logger.error(f"Message handling error: {e}")

    async def _handle_reconnect(self):
        """Handle reconnection with backoff."""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            self._set_state(ConnectionState.ERROR)
            self._running = False
            return

        self.reconnect_attempts += 1
        wait_time = min(
            self.reconnect_interval * (2 ** (self.reconnect_attempts - 1)),
            60.0  # Max 60 seconds
        )
        logger.info(f"Reconnecting in {wait_time}s (attempt {self.reconnect_attempts})")
        await asyncio.sleep(wait_time)

    async def _disconnect(self):
        """Close connection gracefully."""
        if self.connection:
            await self.connection.close()
            self.connection = None
        self._set_state(ConnectionState.DISCONNECTED)

    async def send(self, message: Dict[str, Any]):
        """Send message to server."""
        if self.connection and self.state == ConnectionState.CONNECTED:
            try:
                await self.connection.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Send error: {e}")
                raise

    def send_sync(self, message: Dict[str, Any]):
        """Send message synchronously (from non-async context)."""
        if self._loop and self._running:
            future = asyncio.run_coroutine_threadsafe(
                self.send(message), self._loop
            )
            try:
                future.result(timeout=5.0)
            except Exception as e:
                logger.error(f"Sync send error: {e}")

    def is_connected(self) -> bool:
        """Check if connected."""
        return self.state == ConnectionState.CONNECTED


class MessageHandler:
    """Handler for incoming WebSocket messages."""

    def __init__(self, mt5_service):
        self.mt5 = mt5_service
        self.handlers: Dict[str, Callable] = {
            "PING": self._handle_ping,
            "TRADE_OPEN": self._handle_trade_open,
            "TRADE_CLOSE": self._handle_trade_close,
            "TRADE_MODIFY": self._handle_trade_modify,
            "SYNC_REQUEST": self._handle_sync,
            "GET_POSITIONS": self._handle_get_positions,
            "GET_ACCOUNT": self._handle_get_account,
        }

    def handle(self, message: Dict) -> Optional[Dict]:
        """Process incoming message and return response."""
        msg_type = message.get("type", "")
        handler = self.handlers.get(msg_type)

        if handler:
            try:
                return handler(message)
            except Exception as e:
                logger.error(f"Handler error for {msg_type}: {e}")
                return {"type": "ERROR", "error": str(e)}
        else:
            logger.warning(f"Unknown message type: {msg_type}")
            return None

    def _handle_ping(self, msg: Dict) -> Dict:
        return {"type": "PONG", "timestamp": datetime.now().isoformat()}

    def _handle_trade_open(self, msg: Dict) -> Dict:
        """Handle trade open command."""
        result = self.mt5.open_order(
            symbol=msg.get("symbol"),
            order_type=msg.get("order_type"),
            lot_size=msg.get("lot_size", 0.1),
            stop_loss=msg.get("stop_loss"),
            take_profit=msg.get("take_profit"),
            comment=msg.get("comment", "ForexAI"),
        )
        return {
            "type": "TRADE_RESULT",
            "request_id": msg.get("request_id"),
            "success": result.success if result else False,
            "ticket": result.order if result else None,
            "error": result.error_message if result else "Unknown error",
        }

    def _handle_trade_close(self, msg: Dict) -> Dict:
        """Handle trade close command."""
        result = self.mt5.close_position(
            ticket=msg.get("ticket"),
            lot_size=msg.get("lot_size"),
        )
        return {
            "type": "TRADE_RESULT",
            "request_id": msg.get("request_id"),
            "success": result.success if result else False,
            "profit": result.profit if result else 0,
        }

    def _handle_trade_modify(self, msg: Dict) -> Dict:
        """Handle trade modify command."""
        result = self.mt5.modify_position(
            ticket=msg.get("ticket"),
            stop_loss=msg.get("stop_loss"),
            take_profit=msg.get("take_profit"),
        )
        return {
            "type": "TRADE_RESULT",
            "request_id": msg.get("request_id"),
            "success": result,
        }

    def _handle_sync(self, msg: Dict) -> Dict:
        """Handle sync request."""
        positions = self.mt5.get_positions()
        account = self.mt5.get_account_info()

        return {
            "type": "SYNC_RESPONSE",
            "positions": [
                {
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "type": p.type,
                    "volume": p.volume,
                    "price": p.price,
                    "profit": p.profit,
                    "sl": p.sl,
                    "tp": p.tp,
                }
                for p in (positions or [])
            ],
            "account": {
                "balance": account.balance if account else 0,
                "equity": account.equity if account else 0,
                "margin": account.margin if account else 0,
                "free_margin": account.free_margin if account else 0,
            } if account else None,
        }

    def _handle_get_positions(self, msg: Dict) -> Dict:
        """Get all open positions."""
        positions = self.mt5.get_positions()
        return {
            "type": "POSITIONS",
            "data": [
                {
                    "ticket": p.ticket,
                    "symbol": p.symbol,
                    "type": p.type,
                    "volume": p.volume,
                    "price": p.price,
                    "profit": p.profit,
                }
                for p in (positions or [])
            ],
        }

    def _handle_get_account(self, msg: Dict) -> Dict:
        """Get account information."""
        account = self.mt5.get_account_info()
        if account:
            return {
                "type": "ACCOUNT_INFO",
                "balance": account.balance,
                "equity": account.equity,
                "margin": account.margin,
                "free_margin": account.free_margin,
                "profit": account.profit,
                "leverage": account.leverage,
            }
        return {"type": "ERROR", "error": "Failed to get account info"}
