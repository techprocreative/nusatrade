"""Trade execution service for MT5 orders."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from core.mt5_service import MT5Service, OrderResult


logger = logging.getLogger(__name__)


class TradeExecutor:
    """Execute trades on MT5 terminal."""

    def __init__(self, mt5_service: MT5Service):
        self.mt5 = mt5_service

    def open_trade(
        self,
        symbol: str,
        order_type: str,
        lot_size: float,
        price: Optional[float] = None,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        magic: int = 0,
        comment: str = "ForexAI Bot",
    ) -> Dict[str, Any]:
        """
        Open a new trade on MT5.
        
        Args:
            symbol: Trading symbol (e.g. "EURUSD")
            order_type: "BUY" or "SELL"
            lot_size: Position size in lots
            price: Entry price (None for market price)
            stop_loss: Stop loss price
            take_profit: Take profit price
            magic: Magic number for identification
            comment: Order comment
            
        Returns:
            Dict with trade result
        """
        try:
            logger.info(f"Opening {order_type} {lot_size} {symbol}")
            
            # Validate inputs
            if order_type not in ["BUY", "SELL"]:
                return {
                    "success": False,
                    "error": "Invalid order type. Must be BUY or SELL",
                }
            
            if lot_size <= 0:
                return {
                    "success": False,
                    "error": "Lot size must be positive",
                }
            
            # Execute order via MT5
            result: OrderResult = self.mt5.open_order(
                symbol=symbol,
                order_type=order_type,
                volume=lot_size,
                price=price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                magic=magic,
                comment=comment,
            )
            
            if result.success:
                logger.info(f"Trade opened successfully: ticket={result.ticket}")
                return {
                    "success": True,
                    "ticket": result.ticket,
                    "price": result.price,
                    "symbol": symbol,
                    "order_type": order_type,
                    "lot_size": lot_size,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                logger.error(f"Trade failed: {result.message}")
                return {
                    "success": False,
                    "error": result.message,
                    "retcode": result.retcode,
                }
                
        except Exception as e:
            logger.error(f"Exception opening trade: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def close_trade(
        self,
        ticket: int,
        volume: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Close an existing trade.
        
        Args:
            ticket: Position ticket number
            volume: Volume to close (None = close all)
            
        Returns:
            Dict with close result
        """
        try:
            logger.info(f"Closing position {ticket}")
            
            result: OrderResult = self.mt5.close_position(ticket, volume)
            
            if result.success:
                logger.info(f"Position closed successfully: ticket={ticket}")
                return {
                    "success": True,
                    "ticket": ticket,
                    "close_price": result.price,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                logger.error(f"Close failed: {result.message}")
                return {
                    "success": False,
                    "error": result.message,
                    "retcode": result.retcode,
                }
                
        except Exception as e:
            logger.error(f"Exception closing trade: {e}")
            return {
                "success": False,
                "error": str(e),
            }

    def modify_trade(
        self,
        ticket: int,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Modify stop loss and/or take profit of existing position.
        
        Args:
            ticket: Position ticket number
            stop_loss: New stop loss price
            take_profit: New take profit price
            
        Returns:
            Dict with modify result
        """
        try:
            logger.info(f"Modifying position {ticket}")
            
            if stop_loss is None and take_profit is None:
                return {
                    "success": False,
                    "error": "Must specify at least stop_loss or take_profit",
                }
            
            result: OrderResult = self.mt5.modify_position(
                ticket=ticket,
                stop_loss=stop_loss,
                take_profit=take_profit,
            )
            
            if result.success:
                logger.info(f"Position modified successfully: ticket={ticket}")
                return {
                    "success": True,
                    "ticket": ticket,
                    "stop_loss": stop_loss,
                    "take_profit": take_profit,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            else:
                logger.error(f"Modify failed: {result.message}")
                return {
                    "success": False,
                    "error": result.message,
                    "retcode": result.retcode,
                }
                
        except Exception as e:
            logger.error(f"Exception modifying trade: {e}")
            return {
                "success": False,
                "error": str(e),
            }
