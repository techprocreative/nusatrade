"""Audit logging for trade actions and system events."""

import json
import logging
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy.orm import Session
from sqlalchemy import Column, String, Text, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB

from app.core.database import Base


logger = logging.getLogger("audit")


class AuditAction(str, Enum):
    """Types of auditable actions."""
    # Trade actions
    TRADE_OPEN = "trade_open"
    TRADE_CLOSE = "trade_close"
    TRADE_MODIFY = "trade_modify"
    
    # Signal actions
    SIGNAL_CREATED = "signal_created"
    SIGNAL_APPROVED = "signal_approved"
    SIGNAL_REJECTED = "signal_rejected"
    SIGNAL_EXECUTED = "signal_executed"
    
    # User actions
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_REGISTER = "user_register"
    USER_PASSWORD_CHANGE = "user_password_change"
    
    # Bot actions
    BOT_ACTIVATED = "bot_activated"
    BOT_DEACTIVATED = "bot_deactivated"
    BOT_TRADE = "bot_trade"
    
    # System actions
    SYSTEM_ERROR = "system_error"
    CONNECTOR_CONNECTED = "connector_connected"
    CONNECTOR_DISCONNECTED = "connector_disconnected"


class AuditLog(Base):
    """Audit log database model."""
    __tablename__ = "audit_logs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id = Column(PGUUID(as_uuid=True), nullable=True, index=True)
    action = Column(String(50), nullable=False, index=True)
    entity_type = Column(String(50), nullable=True)  # trade, signal, user, bot
    entity_id = Column(String(100), nullable=True)
    details = Column(JSONB, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class AuditLogger:
    """Audit logger for recording all important actions."""

    def __init__(self, db: Optional[Session] = None):
        self.db = db

    def log(
        self,
        action: AuditAction,
        user_id: Optional[UUID] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[UUID]:
        """Log an auditable action."""
        log_entry = {
            "action": action.value,
            "user_id": str(user_id) if user_id else None,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details,
            "ip_address": ip_address,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Always log to file
        logger.info(json.dumps(log_entry))

        # Log to database if session available
        if self.db:
            try:
                audit_log = AuditLog(
                    user_id=user_id,
                    action=action.value,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    details=details,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )
                self.db.add(audit_log)
                self.db.commit()
                return audit_log.id
            except Exception as e:
                logger.error(f"Failed to write audit log to database: {e}")
                self.db.rollback()

        return None

    def log_trade(
        self,
        action: AuditAction,
        user_id: UUID,
        trade_id: str,
        symbol: str,
        order_type: str,
        lot_size: float,
        price: Optional[float] = None,
        profit: Optional[float] = None,
        ip_address: Optional[str] = None,
    ):
        """Log a trade action with standardized details."""
        details = {
            "symbol": symbol,
            "order_type": order_type,
            "lot_size": lot_size,
        }
        if price is not None:
            details["price"] = price
        if profit is not None:
            details["profit"] = profit

        self.log(
            action=action,
            user_id=user_id,
            entity_type="trade",
            entity_id=trade_id,
            details=details,
            ip_address=ip_address,
        )

    def log_signal(
        self,
        action: AuditAction,
        user_id: UUID,
        signal_id: str,
        symbol: str,
        direction: str,
        confidence: Optional[float] = None,
        ip_address: Optional[str] = None,
    ):
        """Log a signal action."""
        details = {
            "symbol": symbol,
            "direction": direction,
        }
        if confidence is not None:
            details["confidence"] = confidence

        self.log(
            action=action,
            user_id=user_id,
            entity_type="signal",
            entity_id=signal_id,
            details=details,
            ip_address=ip_address,
        )

    def log_user_action(
        self,
        action: AuditAction,
        user_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        details: Optional[Dict] = None,
    ):
        """Log a user action."""
        self.log(
            action=action,
            user_id=user_id,
            entity_type="user",
            entity_id=str(user_id),
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def log_error(
        self,
        error_type: str,
        error_message: str,
        user_id: Optional[UUID] = None,
        details: Optional[Dict] = None,
    ):
        """Log a system error."""
        error_details = {
            "error_type": error_type,
            "error_message": error_message,
            **(details or {}),
        }
        self.log(
            action=AuditAction.SYSTEM_ERROR,
            user_id=user_id,
            entity_type="system",
            details=error_details,
        )


# Singleton instance for global use
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger(db: Optional[Session] = None) -> AuditLogger:
    """Get or create audit logger instance."""
    global _audit_logger
    if _audit_logger is None or db is not None:
        _audit_logger = AuditLogger(db)
    return _audit_logger


def audit_trade_open(
    user_id: UUID,
    trade_id: str,
    symbol: str,
    order_type: str,
    lot_size: float,
    price: float,
    ip: Optional[str] = None,
    db: Optional[Session] = None,
):
    """Convenience function to audit trade open."""
    logger = get_audit_logger(db)
    logger.log_trade(
        AuditAction.TRADE_OPEN,
        user_id=user_id,
        trade_id=trade_id,
        symbol=symbol,
        order_type=order_type,
        lot_size=lot_size,
        price=price,
        ip_address=ip,
    )


def audit_trade_close(
    user_id: UUID,
    trade_id: str,
    symbol: str,
    order_type: str,
    lot_size: float,
    profit: float,
    ip: Optional[str] = None,
    db: Optional[Session] = None,
):
    """Convenience function to audit trade close."""
    logger = get_audit_logger(db)
    logger.log_trade(
        AuditAction.TRADE_CLOSE,
        user_id=user_id,
        trade_id=trade_id,
        symbol=symbol,
        order_type=order_type,
        lot_size=lot_size,
        profit=profit,
        ip_address=ip,
    )
