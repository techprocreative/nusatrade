"""Broker Connections API - MT5 broker management and real-time status."""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api import deps
from app.models.broker import BrokerConnection, ConnectorSession
from app.api.websocket.connection_manager import connection_manager


router = APIRouter()


# Request/Response Models
class ConnectionCreateRequest(BaseModel):
    broker_name: str = "MetaTrader 5"
    account_number: Optional[str] = None
    server: Optional[str] = None
    nickname: Optional[str] = None


class ConnectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    broker_name: str
    account_number: Optional[str]
    server: Optional[str]
    is_active: bool
    last_connected_at: Optional[datetime]
    created_at: datetime


class ConnectionStatusResponse(BaseModel):
    id: str
    status: str  # online, offline, connecting, error
    is_connected: bool
    last_heartbeat: Optional[datetime]
    account_info: Optional[dict] = None


class SyncResponse(BaseModel):
    id: str
    synced: bool
    positions_count: int
    trades_synced: int
    message: str


@router.get("/connections", response_model=List[ConnectionResponse])
def list_connections(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """List all broker connections for the current user."""
    connections = db.query(BrokerConnection).filter(
        BrokerConnection.user_id == current_user.id
    ).all()

    return [
        ConnectionResponse(
            id=str(c.id),
            broker_name=c.broker_name,
            account_number=c.account_number,
            server=c.server,
            is_active=c.is_active or False,
            last_connected_at=c.last_connected_at,
            created_at=c.created_at or datetime.utcnow(),
        )
        for c in connections
    ]


@router.post("/connections", status_code=status.HTTP_201_CREATED, response_model=ConnectionResponse)
def create_connection(
    request: ConnectionCreateRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Create a new broker connection."""
    conn = BrokerConnection(
        id=uuid4(),
        user_id=current_user.id,
        broker_name=request.broker_name,
        account_number=request.account_number,
        server=request.server,
        is_active=False,
        created_at=datetime.utcnow(),
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)

    return ConnectionResponse(
        id=str(conn.id),
        broker_name=conn.broker_name,
        account_number=conn.account_number,
        server=conn.server,
        is_active=conn.is_active or False,
        last_connected_at=conn.last_connected_at,
        created_at=conn.created_at,
    )


@router.get("/connections/{connection_id}", response_model=ConnectionResponse)
def get_connection(
    connection_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Get a specific broker connection."""
    conn = db.query(BrokerConnection).filter(
        BrokerConnection.id == connection_id,
        BrokerConnection.user_id == current_user.id,
    ).first()

    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")

    return ConnectionResponse(
        id=str(conn.id),
        broker_name=conn.broker_name,
        account_number=conn.account_number,
        server=conn.server,
        is_active=conn.is_active or False,
        last_connected_at=conn.last_connected_at,
        created_at=conn.created_at or datetime.utcnow(),
    )


@router.put("/connections/{connection_id}", response_model=ConnectionResponse)
def update_connection(
    connection_id: str,
    request: ConnectionCreateRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Update a broker connection."""
    conn = db.query(BrokerConnection).filter(
        BrokerConnection.id == connection_id,
        BrokerConnection.user_id == current_user.id,
    ).first()

    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")

    conn.broker_name = request.broker_name
    conn.account_number = request.account_number
    conn.server = request.server
    db.commit()

    return ConnectionResponse(
        id=str(conn.id),
        broker_name=conn.broker_name,
        account_number=conn.account_number,
        server=conn.server,
        is_active=conn.is_active or False,
        last_connected_at=conn.last_connected_at,
        created_at=conn.created_at or datetime.utcnow(),
    )


@router.delete("/connections/{connection_id}")
def delete_connection(
    connection_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Delete a broker connection."""
    conn = db.query(BrokerConnection).filter(
        BrokerConnection.id == connection_id,
        BrokerConnection.user_id == current_user.id,
    ).first()

    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")

    # Delete associated sessions
    db.query(ConnectorSession).filter(
        ConnectorSession.connection_id == connection_id
    ).delete()

    db.delete(conn)
    db.commit()

    return {"deleted": connection_id}


@router.get("/connections/{connection_id}/status", response_model=ConnectionStatusResponse)
def get_connection_status(
    connection_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Get real-time status of a broker connection via WebSocket manager."""
    conn = db.query(BrokerConnection).filter(
        BrokerConnection.id == connection_id,
        BrokerConnection.user_id == current_user.id,
    ).first()

    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")

    # Check if connector is online via WebSocket manager
    user_id = str(current_user.id)
    active_connections = connection_manager.user_connections.get(user_id, set())
    
    # Find if this connection has an active session
    session = db.query(ConnectorSession).filter(
        ConnectorSession.connection_id == connection_id,
        ConnectorSession.status == "online",
    ).first()

    is_connected = False
    last_heartbeat = None
    status_str = "offline"
    account_info = None

    if session:
        session_id = str(session.id)
        if session_id in connection_manager.connector_sessions:
            connector_data = connection_manager.connector_sessions[session_id]
            is_connected = True
            last_heartbeat = connector_data.get("last_heartbeat")
            status_str = "online"
            account_info = connector_data.get("account_info")
        else:
            # Session exists but not in memory - stale
            status_str = "disconnected"
            last_heartbeat = session.last_heartbeat

    return ConnectionStatusResponse(
        id=connection_id,
        status=status_str,
        is_connected=is_connected,
        last_heartbeat=last_heartbeat,
        account_info=account_info,
    )


@router.post("/connections/{connection_id}/sync", response_model=SyncResponse)
async def sync_connection(
    connection_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Request sync of positions and trades from MT5."""
    conn = db.query(BrokerConnection).filter(
        BrokerConnection.id == connection_id,
        BrokerConnection.user_id == current_user.id,
    ).first()

    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")

    # Find active connector session
    user_id = str(current_user.id)
    active_connections = connection_manager.user_connections.get(user_id, set())

    if not active_connections:
        return SyncResponse(
            id=connection_id,
            synced=False,
            positions_count=0,
            trades_synced=0,
            message="No active connector. Please connect MT5 Connector app.",
        )

    # Send sync command to connector
    sync_command = {
        "type": "SYNC_REQUEST",
        "connection_id": connection_id,
        "sync_positions": True,
        "sync_trades": True,
        "sync_account": True,
    }

    sent_count = 0
    for conn_id in active_connections:
        success = await connection_manager.send_to_connector(conn_id, sync_command)
        if success:
            sent_count += 1

    if sent_count == 0:
        return SyncResponse(
            id=connection_id,
            synced=False,
            positions_count=0,
            trades_synced=0,
            message="Failed to send sync command to connector.",
        )

    # Update last sync time
    conn.last_connected_at = datetime.utcnow()
    db.commit()

    return SyncResponse(
        id=connection_id,
        synced=True,
        positions_count=0,  # Will be updated by connector callback
        trades_synced=0,
        message="Sync request sent. Data will be updated via WebSocket.",
    )


@router.post("/connections/{connection_id}/disconnect")
async def disconnect_connection(
    connection_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Disconnect a broker connection."""
    conn = db.query(BrokerConnection).filter(
        BrokerConnection.id == connection_id,
        BrokerConnection.user_id == current_user.id,
    ).first()

    if not conn:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connection not found")

    # Update connection status
    conn.is_active = False
    db.commit()

    # Mark sessions as offline
    db.query(ConnectorSession).filter(
        ConnectorSession.connection_id == connection_id
    ).update({"status": "offline"})
    db.commit()

    return {"id": connection_id, "status": "disconnected"}


@router.get("/supported-brokers")
def list_supported_brokers():
    """List supported brokers."""
    return {
        "brokers": [
            {
                "id": "mt5",
                "name": "MetaTrader 5",
                "description": "Industry standard forex trading platform",
                "requires_connector": True,
            },
            {
                "id": "mt4",
                "name": "MetaTrader 4",
                "description": "Legacy forex trading platform (coming soon)",
                "requires_connector": True,
                "status": "coming_soon",
            },
        ]
    }
