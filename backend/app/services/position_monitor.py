"""Position Monitor Service - Monitors open positions and manages trailing stops.

This service:
1. Syncs positions from MT5 connector to database
2. Manages trailing stops for open positions
3. Detects position closures (SL/TP hits)
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.core.database import SessionLocal
from app.models.trade import Trade, Position
from app.models.broker import BrokerConnection
from app.services.trailing_stop import (
    TrailingStopManager,
    TrailingStopConfig,
    TrailingStopType,
    PositionState,
    process_trailing_stop,
)
from app.services.market_data import MarketDataFetcher
from app.api.websocket.connection_manager import connection_manager


logger = get_logger(__name__)


class PositionMonitorService:
    """
    Service for monitoring positions and managing trailing stops.
    
    This service runs in the background and:
    1. Periodically syncs positions from connected MT5 terminals
    2. Updates trailing stops based on current prices
    3. Sends SL/TP modification commands to MT5
    """
    
    def __init__(self):
        self._is_running = False
        self._last_sync: Optional[datetime] = None
        self._trailing_managers: Dict[str, TrailingStopManager] = {}  # connection_id -> manager
        self._position_cache: Dict[str, Dict[int, dict]] = {}  # connection_id -> {ticket: position_data}
    
    async def start(self):
        """Start the position monitoring loop."""
        if self._is_running:
            logger.warning("Position monitor already running")
            return
        
        self._is_running = True
        logger.info("Position monitor started")
        
        while self._is_running:
            try:
                await self._monitoring_cycle()
            except Exception as e:
                logger.error(f"Position monitor error: {e}")
            
            # Wait before next cycle (every 10 seconds)
            await asyncio.sleep(10)
    
    def stop(self):
        """Stop the position monitoring loop."""
        self._is_running = False
        logger.info("Position monitor stopped")
    
    async def _monitoring_cycle(self):
        """Single monitoring cycle."""
        db = SessionLocal()
        try:
            # Get all online connectors
            online_connectors = list(connection_manager.connector_sessions.keys())
            
            for connection_id in online_connectors:
                session = connection_manager.connector_sessions.get(connection_id)
                if not session or not session.mt5_connected:
                    continue
                
                # Request position update from connector
                await self._request_position_sync(connection_id)
                
                # Process trailing stops for this connection
                await self._process_trailing_stops(db, connection_id)
            
            self._last_sync = datetime.utcnow()
            
        finally:
            db.close()
    
    async def _request_position_sync(self, connection_id: str):
        """Request position sync from connector."""
        try:
            await connection_manager.send_to_connector(connection_id, {
                "type": "GET_POSITIONS",
                "request_id": f"sync_{datetime.utcnow().timestamp()}",
            })
        except Exception as e:
            logger.error(f"Failed to request position sync from {connection_id}: {e}")
    
    async def _process_trailing_stops(self, db: Session, connection_id: str):
        """Process trailing stops for positions on a connection."""
        # Get trailing stop manager for this connection
        manager = self._trailing_managers.get(connection_id)
        if not manager:
            manager = TrailingStopManager()
            self._trailing_managers[connection_id] = manager
        
        # Get positions from cache
        positions = self._position_cache.get(connection_id, {})
        
        for ticket, pos_data in positions.items():
            symbol = pos_data.get("symbol", "EURUSD")
            direction = pos_data.get("order_type", "BUY")
            entry_price = pos_data.get("open_price", 0)
            current_sl = pos_data.get("stop_loss")
            current_price = pos_data.get("current_price", entry_price)
            
            # Ensure position is in manager
            if ticket not in manager.positions:
                manager.add_position(
                    position_id=ticket,
                    direction=direction,
                    entry_price=entry_price,
                    stop_loss=current_sl,
                    lot_size=pos_data.get("volume", 0.1),
                )
            
            # Get ATR for this symbol
            atr = self._get_cached_atr(symbol)
            
            # Process trailing stop
            state = manager.positions[ticket]
            new_sl, breakeven_triggered = process_trailing_stop(
                state, current_price, manager.config, atr
            )
            
            if new_sl is not None:
                # Send SL modification to MT5
                await self._send_sl_modification(
                    connection_id, ticket, new_sl, breakeven_triggered
                )
                
                # Update database
                self._update_position_sl(db, connection_id, ticket, new_sl)
    
    async def _send_sl_modification(
        self,
        connection_id: str,
        ticket: int,
        new_sl: float,
        is_breakeven: bool
    ):
        """Send stop loss modification to MT5 via connector."""
        try:
            action = "breakeven" if is_breakeven else "trailing"
            await connection_manager.send_to_connector(connection_id, {
                "type": "TRADE_MODIFY",
                "request_id": f"sl_{ticket}_{datetime.utcnow().timestamp()}",
                "ticket": ticket,
                "stop_loss": new_sl,
                "action": action,
            })
            logger.info(f"Sent SL modification for ticket {ticket}: SL={new_sl} ({action})")
        except Exception as e:
            logger.error(f"Failed to send SL modification: {e}")
    
    def _update_position_sl(
        self, db: Session, connection_id: str, ticket: int, new_sl: float
    ):
        """Update position stop loss in database."""
        try:
            position = db.query(Position).filter(
                Position.connection_id == UUID(connection_id),
                Position.ticket == ticket,
            ).first()
            
            if position:
                from decimal import Decimal
                position.stop_loss = Decimal(str(new_sl))
                position.updated_at = datetime.utcnow()
                db.commit()
        except Exception as e:
            logger.error(f"Failed to update position SL in DB: {e}")
            db.rollback()
    
    def _get_cached_atr(self, symbol: str) -> Optional[float]:
        """Get cached ATR for a symbol."""
        # Simple ATR estimation based on typical volatility
        atr_estimates = {
            "EURUSD": 0.0008,
            "GBPUSD": 0.0012,
            "USDJPY": 0.08,
            "AUDUSD": 0.0006,
            "USDCAD": 0.0007,
            "XAUUSD": 15.0,
        }
        return atr_estimates.get(symbol.upper(), 0.001)
    
    def handle_position_update(self, connection_id: str, positions: List[dict]):
        """
        Handle position update from connector.
        
        Called when connector sends POSITION_UPDATE message.
        """
        # Update position cache
        self._position_cache[connection_id] = {
            pos.get("ticket"): pos for pos in positions if pos.get("ticket")
        }
        
        # Get or create trailing manager
        if connection_id not in self._trailing_managers:
            self._trailing_managers[connection_id] = TrailingStopManager()
        
        manager = self._trailing_managers[connection_id]
        
        # Sync positions with manager
        current_tickets = set(self._position_cache[connection_id].keys())
        managed_tickets = set(manager.positions.keys())
        
        # Remove closed positions
        for ticket in managed_tickets - current_tickets:
            manager.remove_position(ticket)
            logger.info(f"Position {ticket} closed (removed from trailing manager)")
        
        # Add new positions
        for ticket in current_tickets - managed_tickets:
            pos = self._position_cache[connection_id][ticket]
            manager.add_position(
                position_id=ticket,
                direction=pos.get("order_type", "BUY"),
                entry_price=pos.get("open_price", 0),
                stop_loss=pos.get("stop_loss"),
                lot_size=pos.get("volume", 0.1),
            )
    
    def sync_positions_to_db(self, db: Session, connection_id: str, user_id: str):
        """
        Sync positions from MT5 to database.
        
        Ensures database positions match actual MT5 positions.
        """
        positions_data = self._position_cache.get(connection_id, {})
        
        if not positions_data:
            return
        
        try:
            conn_uuid = UUID(connection_id)
            user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        except (ValueError, TypeError):
            logger.error(f"Invalid UUID: connection_id={connection_id}, user_id={user_id}")
            return
        
        # Get current DB positions for this connection
        db_positions = db.query(Position).filter(
            Position.connection_id == conn_uuid
        ).all()
        
        db_tickets = {p.ticket: p for p in db_positions}
        mt5_tickets = set(positions_data.keys())
        
        # Remove positions that no longer exist in MT5
        for ticket, position in db_tickets.items():
            if ticket not in mt5_tickets:
                logger.info(f"Removing closed position from DB: ticket={ticket}")
                db.delete(position)
        
        # Add/update positions from MT5
        for ticket, pos_data in positions_data.items():
            if ticket in db_tickets:
                # Update existing position
                position = db_tickets[ticket]
                from decimal import Decimal
                position.current_price = Decimal(str(pos_data.get("current_price", 0)))
                position.profit = Decimal(str(pos_data.get("profit", 0)))
                position.stop_loss = Decimal(str(pos_data.get("stop_loss", 0))) if pos_data.get("stop_loss") else None
                position.take_profit = Decimal(str(pos_data.get("take_profit", 0))) if pos_data.get("take_profit") else None
                position.updated_at = datetime.utcnow()
            else:
                # Add new position
                from decimal import Decimal
                new_position = Position(
                    user_id=user_uuid,
                    connection_id=conn_uuid,
                    ticket=ticket,
                    symbol=pos_data.get("symbol"),
                    trade_type=pos_data.get("order_type"),
                    lot_size=Decimal(str(pos_data.get("volume", 0.1))),
                    open_price=Decimal(str(pos_data.get("open_price", 0))),
                    current_price=Decimal(str(pos_data.get("current_price", 0))),
                    stop_loss=Decimal(str(pos_data.get("stop_loss", 0))) if pos_data.get("stop_loss") else None,
                    take_profit=Decimal(str(pos_data.get("take_profit", 0))) if pos_data.get("take_profit") else None,
                    profit=Decimal(str(pos_data.get("profit", 0))),
                    open_time=datetime.utcnow(),
                )
                db.add(new_position)
                logger.info(f"Added new position from MT5: ticket={ticket}, symbol={pos_data.get('symbol')}")
        
        db.commit()
    
    def get_status(self) -> dict:
        """Get current status of position monitor."""
        return {
            "is_running": self._is_running,
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
            "managed_connections": len(self._trailing_managers),
            "total_positions": sum(
                len(m.positions) for m in self._trailing_managers.values()
            ),
            "position_cache_size": sum(
                len(p) for p in self._position_cache.values()
            ),
        }


# Global instance
position_monitor = PositionMonitorService()


async def start_position_monitor():
    """Start the position monitor service."""
    await position_monitor.start()


def stop_position_monitor():
    """Stop the position monitor service."""
    position_monitor.stop()
