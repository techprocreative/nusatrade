"""WebSocket connection manager for real-time trading updates."""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field

from fastapi import WebSocket, WebSocketDisconnect

from app.config import get_settings
from app.core.logging import get_logger


logger = get_logger(__name__)
settings = get_settings()


@dataclass
class ConnectorSession:
    """Represents an active connector session."""
    websocket: WebSocket
    user_id: str
    connection_id: str
    connected_at: datetime = field(default_factory=datetime.utcnow)
    last_heartbeat: datetime = field(default_factory=datetime.utcnow)
    mt5_connected: bool = False
    broker_name: Optional[str] = None
    account_number: Optional[str] = None
    # Cached account info from MT5
    account_balance: Optional[float] = None
    account_equity: Optional[float] = None
    account_margin: Optional[float] = None
    account_free_margin: Optional[float] = None
    account_profit: Optional[float] = None
    account_updated_at: Optional[datetime] = None


class ConnectionManager:
    """Manages WebSocket connections for connectors and clients."""

    def __init__(self):
        # Connector sessions: connection_id -> ConnectorSession
        self.connector_sessions: Dict[str, ConnectorSession] = {}
        # User connections: user_id -> Set[connection_ids]
        self.user_connections: Dict[str, Set[str]] = {}
        # Client websockets (dashboard viewers): user_id -> List[WebSocket]
        self.client_websockets: Dict[str, List[WebSocket]] = {}
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def start_heartbeat_monitor(self):
        """Start the heartbeat monitoring task."""
        if self._heartbeat_task is None:
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            logger.info("Heartbeat monitor started")

    async def stop_heartbeat_monitor(self):
        """Stop the heartbeat monitoring task."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None
            logger.info("Heartbeat monitor stopped")

    async def _heartbeat_loop(self):
        """Check for stale connections periodically."""
        while True:
            try:
                await asyncio.sleep(settings.ws_heartbeat_interval)
                await self._check_stale_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")

    async def _check_stale_connections(self):
        """Disconnect stale connector sessions."""
        now = datetime.utcnow()
        stale_connections = []

        for conn_id, session in self.connector_sessions.items():
            elapsed = (now - session.last_heartbeat).total_seconds()
            if elapsed > settings.ws_connection_timeout:
                stale_connections.append(conn_id)
                logger.warning(f"Stale connection detected: {conn_id}, last heartbeat {elapsed}s ago")

        for conn_id in stale_connections:
            await self.disconnect_connector(conn_id)

    async def connect_connector(
        self,
        websocket: WebSocket,
        user_id: str,
        connection_id: str,
    ) -> ConnectorSession:
        """Register a new connector session."""
        await websocket.accept()

        session = ConnectorSession(
            websocket=websocket,
            user_id=user_id,
            connection_id=connection_id,
        )

        self.connector_sessions[connection_id] = session

        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)

        logger.info(f"Connector connected: {connection_id} for user {user_id}")

        # Send welcome message
        await self.send_to_connector(connection_id, {
            "type": "WELCOME",
            "message": "Connector connected successfully",
            "connection_id": connection_id,
            "heartbeat_interval": settings.ws_heartbeat_interval,
        })

        return session

    async def disconnect_connector(self, connection_id: str):
        """Disconnect and cleanup a connector session."""
        session = self.connector_sessions.pop(connection_id, None)
        if session:
            # Remove from user connections
            if session.user_id in self.user_connections:
                self.user_connections[session.user_id].discard(connection_id)
                if not self.user_connections[session.user_id]:
                    del self.user_connections[session.user_id]

            # Close websocket
            try:
                await session.websocket.close()
            except Exception:
                pass

            logger.info(f"Connector disconnected: {connection_id}")

            # Notify user's clients
            await self.broadcast_to_user(session.user_id, {
                "type": "CONNECTOR_DISCONNECTED",
                "connection_id": connection_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })

    async def connect_client(self, websocket: WebSocket, user_id: str):
        """Register a client (dashboard) websocket."""
        await websocket.accept()

        if user_id not in self.client_websockets:
            self.client_websockets[user_id] = []
        self.client_websockets[user_id].append(websocket)

        logger.info(f"Client connected for user {user_id}")

    async def disconnect_client(self, websocket: WebSocket, user_id: str):
        """Disconnect a client websocket."""
        if user_id in self.client_websockets:
            if websocket in self.client_websockets[user_id]:
                self.client_websockets[user_id].remove(websocket)
            if not self.client_websockets[user_id]:
                del self.client_websockets[user_id]

        logger.info(f"Client disconnected for user {user_id}")

    async def send_to_connector(self, connection_id: str, message: Dict[str, Any]):
        """Send a message to a specific connector."""
        session = self.connector_sessions.get(connection_id)
        if session:
            try:
                await session.websocket.send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to connector {connection_id}: {e}")
                await self.disconnect_connector(connection_id)

    async def broadcast_to_user(self, user_id: str, message: Dict[str, Any]):
        """Broadcast a message to all of a user's clients."""
        clients = self.client_websockets.get(user_id, [])
        disconnected = []

        for client in clients:
            try:
                await client.send_json(message)
            except Exception:
                disconnected.append(client)

        # Cleanup disconnected clients
        for client in disconnected:
            await self.disconnect_client(client, user_id)

    async def handle_connector_message(self, connection_id: str, message: Dict[str, Any]):
        """Handle an incoming message from a connector."""
        session = self.connector_sessions.get(connection_id)
        if not session:
            return

        msg_type = message.get("type", "")

        if msg_type == "HEARTBEAT":
            session.last_heartbeat = datetime.utcnow()
            await self.send_to_connector(connection_id, {
                "type": "HEARTBEAT_ACK",
                "timestamp": datetime.utcnow().isoformat() + "Z",
            })

        elif msg_type == "MT5_STATUS":
            session.mt5_connected = message.get("connected", False)
            session.broker_name = message.get("broker_name")
            session.account_number = message.get("account_number")

            # Broadcast to user's dashboard
            await self.broadcast_to_user(session.user_id, {
                "type": "MT5_STATUS_UPDATE",
                "connection_id": connection_id,
                **message,
            })

        elif msg_type == "ACCOUNT_UPDATE":
            # Cache account info in session
            session.account_balance = message.get("balance")
            session.account_equity = message.get("equity")
            session.account_margin = message.get("margin")
            session.account_free_margin = message.get("free_margin")
            session.account_profit = message.get("profit")
            session.account_updated_at = datetime.utcnow()
            
            await self.broadcast_to_user(session.user_id, {
                "type": "ACCOUNT_UPDATE",
                "connection_id": connection_id,
                **message,
            })

        elif msg_type == "TRADE_RESULT":
            # Update database with trade result (MT5 ticket, actual price, etc.)
            await self._handle_trade_result(session, message)
            
            await self.broadcast_to_user(session.user_id, {
                "type": "TRADE_RESULT",
                "connection_id": connection_id,
                **message,
            })

        elif msg_type == "POSITION_UPDATE":
            await self.broadcast_to_user(session.user_id, {
                "type": "POSITION_UPDATE",
                "connection_id": connection_id,
                **message,
            })

        elif msg_type == "ERROR":
            logger.error(f"Connector error from {connection_id}: {message.get('error')}")
            await self.broadcast_to_user(session.user_id, {
                "type": "CONNECTOR_ERROR",
                "connection_id": connection_id,
                **message,
            })

        else:
            logger.warning(f"Unknown message type from connector: {msg_type}")

    async def _handle_trade_result(self, session: ConnectorSession, message: Dict[str, Any]):
        """
        Handle TRADE_RESULT from connector and update database.
        
        This updates the trade record with:
        - MT5 ticket number
        - Actual execution price
        - Success/failure status
        """
        from app.core.database import SessionLocal
        from app.models.trade import Trade
        from uuid import UUID
        
        request_id = message.get("request_id")
        success = message.get("success", False)
        ticket = message.get("ticket")
        price = message.get("price")
        error = message.get("error")
        
        if not request_id:
            logger.warning("TRADE_RESULT received without request_id")
            return
        
        db = SessionLocal()
        try:
            # Find the trade by request_id (which is the trade UUID)
            try:
                trade_uuid = UUID(request_id)
            except (ValueError, TypeError):
                logger.warning(f"Invalid request_id format: {request_id}")
                return
            
            trade = db.query(Trade).filter(Trade.id == trade_uuid).first()
            
            if not trade:
                logger.warning(f"Trade not found for request_id: {request_id}")
                return
            
            # Update trade with MT5 result
            if success and ticket:
                trade.ticket = ticket
                trade.mt5_executed = True
                if price:
                    from decimal import Decimal
                    trade.open_price = Decimal(str(price))
                logger.info(f"Trade {request_id} executed on MT5: ticket={ticket}, price={price}")
            else:
                trade.mt5_executed = False
                trade.mt5_error = error or "Unknown error"
                logger.warning(f"Trade {request_id} failed on MT5: {error}")
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error handling TRADE_RESULT: {e}")
            db.rollback()
        finally:
            db.close()

    def get_user_connections(self, user_id: str) -> List[str]:
        """Get all connection IDs for a user."""
        return list(self.user_connections.get(user_id, set()))

    def get_connection_session(self, connection_id: str) -> Optional[ConnectorSession]:
        """Get a connector session by ID."""
        return self.connector_sessions.get(connection_id)

    def is_connector_online(self, connection_id: str) -> bool:
        """Check if a connector is currently online."""
        return connection_id in self.connector_sessions

    def get_user_account_info(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get aggregated account info from all user's active connections.
        
        Returns combined balance/equity from all connected MT5 accounts,
        or None if no connections with account data.
        """
        connections = self.user_connections.get(user_id, set())
        if not connections:
            return None
        
        total_balance = 0.0
        total_equity = 0.0
        total_margin = 0.0
        total_free_margin = 0.0
        total_profit = 0.0
        has_data = False
        
        for conn_id in connections:
            session = self.connector_sessions.get(conn_id)
            if session and session.mt5_connected and session.account_balance is not None:
                has_data = True
                total_balance += session.account_balance or 0
                total_equity += session.account_equity or 0
                total_margin += session.account_margin or 0
                total_free_margin += session.account_free_margin or 0
                total_profit += session.account_profit or 0
        
        if not has_data:
            return None
        
        return {
            "balance": total_balance,
            "equity": total_equity,
            "margin": total_margin,
            "free_margin": total_free_margin,
            "profit": total_profit,
            "connections_count": len(connections),
        }


# Global connection manager instance
connection_manager = ConnectionManager()
