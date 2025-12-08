"""WebSocket endpoint for MT5 connector apps."""

import json
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from jose import jwt, JWTError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.logging import get_logger
from app.api import deps
from app.models.user import User
from app.models.broker import BrokerConnection
from app.api.websocket.connection_manager import connection_manager


router = APIRouter()
logger = get_logger(__name__)
settings = get_settings()


async def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token and return user info."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return {"email": payload.get("sub")}
    except JWTError:
        return None


async def verify_connection_ownership(
    connection_id: str,
    user_email: str,
    db: Session
) -> bool:
    """Verify that the connection_id belongs to the user."""
    try:
        # Get user by email
        user = db.query(User).filter(User.email == user_email).first()
        if not user:
            return False
        
        # Check if connection belongs to user
        try:
            conn_uuid = UUID(connection_id)
        except (ValueError, TypeError):
            logger.warning(f"Invalid connection_id format: {connection_id}")
            return False
        
        connection = db.query(BrokerConnection).filter(
            BrokerConnection.id == conn_uuid,
            BrokerConnection.user_id == user.id,
        ).first()
        
        return connection is not None
        
    except Exception as e:
        logger.error(f"Error verifying connection ownership: {e}")
        return False


@router.websocket("/ws")
async def connector_ws(
    websocket: WebSocket,
    token: str = Query(..., description="JWT token for authentication"),
    connection_id: str = Query(..., description="Broker connection ID"),
    db: Session = Depends(deps.get_db),
):
    """WebSocket endpoint for connector apps to communicate with the platform."""
    
    # Verify token
    user_info = await verify_token(token)
    if not user_info:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return
    
    user_email = user_info["email"]

    # Verify connection_id belongs to user
    if not await verify_connection_ownership(connection_id, user_email, db):
        logger.warning(f"User {user_email} attempted to access connection {connection_id} they don't own")
        await websocket.close(code=4003, reason="Connection not found or access denied")
        return

    user_id = user_email

    try:
        # Register connection
        session = await connection_manager.connect_connector(
            websocket=websocket,
            user_id=user_id,
            connection_id=connection_id,
        )

        # Message loop
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                await connection_manager.handle_connector_message(connection_id, message)
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON from connector {connection_id}")
                await connection_manager.send_to_connector(connection_id, {
                    "type": "ERROR",
                    "error": "Invalid JSON format",
                })

    except WebSocketDisconnect:
        logger.info(f"Connector {connection_id} disconnected normally")
    except Exception as e:
        logger.error(f"Connector {connection_id} error: {e}")
    finally:
        await connection_manager.disconnect_connector(connection_id)


@router.websocket("/client")
async def client_ws(
    websocket: WebSocket,
    token: str = Query(..., description="JWT token for authentication"),
):
    """WebSocket endpoint for dashboard clients to receive real-time updates."""
    
    # Verify token
    user_info = await verify_token(token)
    if not user_info:
        await websocket.close(code=4001, reason="Invalid or expired token")
        return

    user_id = user_info["email"]

    try:
        await connection_manager.connect_client(websocket, user_id)

        # Send current connection status
        connections = connection_manager.get_user_connections(user_id)
        await websocket.send_json({
            "type": "CONNECTIONS_STATUS",
            "connections": [
                {
                    "connection_id": conn_id,
                    "mt5_connected": (sess := connection_manager.get_connection_session(conn_id)) and sess.mt5_connected,
                    "broker_name": sess.broker_name if sess else None,
                }
                for conn_id in connections
            ],
        })

        # Keep connection alive and handle pings
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "PING":
                await websocket.send_json({"type": "PONG"})
            
            elif message.get("type") == "SEND_TRADE_COMMAND":
                # Forward trade command to connector
                target_connection = message.get("connection_id")
                if target_connection in connection_manager.connector_sessions:
                    await connection_manager.send_to_connector(target_connection, {
                        "type": "TRADE_COMMAND",
                        "id": message.get("command_id"),
                        "action": message.get("action"),
                        "symbol": message.get("symbol"),
                        "order_type": message.get("order_type"),
                        "lot_size": message.get("lot_size"),
                        "stop_loss": message.get("stop_loss"),
                        "take_profit": message.get("take_profit"),
                    })
                else:
                    await websocket.send_json({
                        "type": "ERROR",
                        "error": "Connector not online",
                        "command_id": message.get("command_id"),
                    })

    except WebSocketDisconnect:
        logger.info(f"Client disconnected for user {user_id}")
    except Exception as e:
        logger.error(f"Client error for user {user_id}: {e}")
    finally:
        await connection_manager.disconnect_client(websocket, user_id)
