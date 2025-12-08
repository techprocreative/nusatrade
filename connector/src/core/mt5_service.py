"""MT5 Service for connecting to MetaTrader 5 terminal."""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    mt5 = None
    MT5_AVAILABLE = False


logger = logging.getLogger(__name__)


@dataclass
class AccountInfo:
    """Account information from MT5."""
    login: int
    balance: float
    equity: float
    margin: float
    free_margin: float
    profit: float
    leverage: int
    currency: str
    server: str
    company: str


@dataclass
class PositionInfo:
    """Open position information."""
    ticket: int
    symbol: str
    order_type: str  # BUY or SELL
    volume: float
    open_price: float
    current_price: float
    stop_loss: float
    take_profit: float
    profit: float
    open_time: datetime
    magic: int
    comment: str


@dataclass
class OrderResult:
    """Result of order execution."""
    success: bool
    ticket: int = 0
    retcode: int = 0
    message: str = ""
    price: float = 0.0


class MT5Service:
    """Service for interacting with MetaTrader 5."""

    def __init__(self):
        self.connected = False
        self._account_info: Optional[AccountInfo] = None

    def connect(self, login: int = None, password: str = None, server: str = None) -> bool:
        """Initialize and connect to MT5 terminal."""
        if not MT5_AVAILABLE:
            logger.error("MetaTrader5 package not available")
            return False

        # Initialize MT5
        if not mt5.initialize():
            logger.error(f"MT5 initialize failed: {mt5.last_error()}")
            return False

        # Login if credentials provided
        if login and password and server:
            if not mt5.login(login, password=password, server=server):
                logger.error(f"MT5 login failed: {mt5.last_error()}")
                mt5.shutdown()
                return False

        self.connected = True
        logger.info("MT5 connected successfully")
        return True

    def shutdown(self):
        """Disconnect from MT5."""
        if MT5_AVAILABLE and self.connected:
            mt5.shutdown()
        self.connected = False
        logger.info("MT5 disconnected")

    def get_account_info(self) -> Optional[AccountInfo]:
        """Get account information."""
        if not self._check_connection():
            return None

        info = mt5.account_info()
        if info is None:
            logger.error(f"Failed to get account info: {mt5.last_error()}")
            return None

        return AccountInfo(
            login=info.login,
            balance=info.balance,
            equity=info.equity,
            margin=info.margin,
            free_margin=info.margin_free,
            profit=info.profit,
            leverage=info.leverage,
            currency=info.currency,
            server=info.server,
            company=info.company,
        )

    def get_positions(self, symbol: str = None) -> List[PositionInfo]:
        """Get all open positions."""
        if not self._check_connection():
            return []

        if symbol:
            positions = mt5.positions_get(symbol=symbol)
        else:
            positions = mt5.positions_get()

        if positions is None:
            return []

        return [
            PositionInfo(
                ticket=pos.ticket,
                symbol=pos.symbol,
                order_type="BUY" if pos.type == 0 else "SELL",
                volume=pos.volume,
                open_price=pos.price_open,
                current_price=pos.price_current,
                stop_loss=pos.sl,
                take_profit=pos.tp,
                profit=pos.profit,
                open_time=datetime.fromtimestamp(pos.time),
                magic=pos.magic,
                comment=pos.comment,
            )
            for pos in positions
        ]

    def open_order(
        self,
        symbol: str,
        order_type: str,
        volume: float,
        price: float = None,
        stop_loss: float = None,
        take_profit: float = None,
        magic: int = 0,
        comment: str = "",
    ) -> OrderResult:
        """Open a new order."""
        if not self._check_connection():
            return OrderResult(success=False, message="Not connected to MT5")

        # Get symbol info
        symbol_info = mt5.symbol_info(symbol)
        if symbol_info is None:
            return OrderResult(success=False, message=f"Symbol {symbol} not found")

        if not symbol_info.visible:
            mt5.symbol_select(symbol, True)

        # Determine order type
        if order_type.upper() == "BUY":
            mt5_type = mt5.ORDER_TYPE_BUY
            price = price or mt5.symbol_info_tick(symbol).ask
        else:
            mt5_type = mt5.ORDER_TYPE_SELL
            price = price or mt5.symbol_info_tick(symbol).bid

        # Build request
        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": volume,
            "type": mt5_type,
            "price": price,
            "deviation": 20,
            "magic": magic,
            "comment": comment,
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        if stop_loss:
            request["sl"] = stop_loss
        if take_profit:
            request["tp"] = take_profit

        # Send order
        result = mt5.order_send(request)

        if result is None:
            return OrderResult(success=False, message=f"Order failed: {mt5.last_error()}")

        if result.retcode != mt5.TRADE_RETCODE_DONE:
            return OrderResult(
                success=False,
                retcode=result.retcode,
                message=f"Order failed: {result.comment}",
            )

        return OrderResult(
            success=True,
            ticket=result.order,
            retcode=result.retcode,
            price=result.price,
            message="Order executed successfully",
        )

    def close_position(self, ticket: int, volume: float = None) -> OrderResult:
        """Close an open position."""
        if not self._check_connection():
            return OrderResult(success=False, message="Not connected to MT5")

        # Get position
        position = mt5.positions_get(ticket=ticket)
        if not position:
            return OrderResult(success=False, message=f"Position {ticket} not found")

        position = position[0]
        symbol = position.symbol
        close_volume = volume or position.volume

        # Determine close order type
        if position.type == 0:  # BUY position
            close_type = mt5.ORDER_TYPE_SELL
            price = mt5.symbol_info_tick(symbol).bid
        else:  # SELL position
            close_type = mt5.ORDER_TYPE_BUY
            price = mt5.symbol_info_tick(symbol).ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": close_volume,
            "type": close_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": position.magic,
            "comment": "Close by connector",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            return OrderResult(
                success=False,
                retcode=result.retcode if result else 0,
                message=f"Close failed: {result.comment if result else mt5.last_error()}",
            )

        return OrderResult(
            success=True,
            ticket=result.order,
            price=result.price,
            message="Position closed successfully",
        )

    def modify_position(
        self,
        ticket: int,
        stop_loss: float = None,
        take_profit: float = None,
    ) -> OrderResult:
        """Modify stop loss and take profit of a position."""
        if not self._check_connection():
            return OrderResult(success=False, message="Not connected to MT5")

        position = mt5.positions_get(ticket=ticket)
        if not position:
            return OrderResult(success=False, message=f"Position {ticket} not found")

        position = position[0]

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "symbol": position.symbol,
            "position": ticket,
            "sl": stop_loss if stop_loss is not None else position.sl,
            "tp": take_profit if take_profit is not None else position.tp,
        }

        result = mt5.order_send(request)

        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            return OrderResult(
                success=False,
                retcode=result.retcode if result else 0,
                message=f"Modify failed: {result.comment if result else mt5.last_error()}",
            )

        return OrderResult(success=True, message="Position modified successfully")

    def get_symbol_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get symbol information."""
        if not self._check_connection():
            return None

        info = mt5.symbol_info(symbol)
        if info is None:
            return None

        return {
            "symbol": info.name,
            "bid": info.bid,
            "ask": info.ask,
            "spread": info.spread,
            "digits": info.digits,
            "volume_min": info.volume_min,
            "volume_max": info.volume_max,
            "volume_step": info.volume_step,
        }

    def get_tick(self, symbol: str) -> Optional[Dict[str, float]]:
        """Get current tick for a symbol."""
        if not self._check_connection():
            return None

        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None

        return {
            "bid": tick.bid,
            "ask": tick.ask,
            "last": tick.last,
            "volume": tick.volume,
            "time": tick.time,
        }

    def _check_connection(self) -> bool:
        """Check if connected to MT5."""
        if not MT5_AVAILABLE:
            return False
        if not self.connected:
            logger.warning("Not connected to MT5")
            return False
        return True
