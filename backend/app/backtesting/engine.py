"""Event-driven backtesting engine with trailing stop and adaptive SL/TP."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

import pandas as pd

from app.backtesting.data_manager import DataManager
from app.backtesting.metrics import BacktestMetrics, calculate_metrics
from app.services.risk_management import (
    calculate_atr_from_dataframe,
    calculate_sl_tp,
    RiskConfig,
    SLType,
    TPType,
)
from app.services.trailing_stop import (
    TrailingStopConfig,
    TrailingStopType,
    PositionState,
    process_trailing_stop,
)
from app.core.logging import get_logger


logger = get_logger(__name__)


class OrderType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, Enum):
    PENDING = "pending"
    FILLED = "filled"
    CANCELLED = "cancelled"


@dataclass
class Order:
    """Represents a trading order."""
    id: int
    order_type: OrderType
    symbol: str
    lot_size: float
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    fill_price: Optional[float] = None
    fill_time: Optional[datetime] = None


@dataclass
class Position:
    """Represents an open position."""
    id: int
    order_type: OrderType
    symbol: str
    lot_size: float
    entry_price: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    bars_held: int = 0
    # Trailing stop tracking
    highest_price: float = 0.0  # For BUY positions
    lowest_price: float = float('inf')  # For SELL positions
    breakeven_hit: bool = False
    initial_sl: Optional[float] = None  # Original SL before modifications


@dataclass
class Trade:
    """Represents a closed trade."""
    id: int
    order_type: str
    symbol: str
    lot_size: float
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    profit: float
    bars_held: int
    exit_reason: str = "signal"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "order_type": self.order_type,
            "symbol": self.symbol,
            "lot_size": self.lot_size,
            "entry_price": self.entry_price,
            "exit_price": self.exit_price,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "profit": self.profit,
            "bars_held": self.bars_held,
            "exit_reason": self.exit_reason,
        }


@dataclass
class BacktestConfig:
    """Configuration for backtesting."""
    initial_balance: float = 10000.0
    commission: float = 0.0  # Per lot
    slippage_pips: float = 0.5
    spread_pips: float = 1.0
    pip_value: float = 10.0  # Per standard lot for most pairs
    allow_pyramiding: bool = False  # Multiple positions same direction
    max_positions: int = 1
    # Trailing stop configuration
    trailing_stop_enabled: bool = False
    trailing_stop_config: Optional[TrailingStopConfig] = None
    # ATR period for dynamic calculations
    atr_period: int = 14


class BacktestEngine:
    """Event-driven backtesting engine."""

    def __init__(
        self,
        data_manager: DataManager,
        strategy: Any,
        config: Optional[BacktestConfig] = None,
    ):
        self.data_manager = data_manager
        self.strategy = strategy
        self.config = config or BacktestConfig()
        
        # State
        self.balance = self.config.initial_balance
        self.equity = self.config.initial_balance
        self.positions: List[Position] = []
        self.pending_orders: List[Order] = []
        self.closed_trades: List[Trade] = []
        self.equity_curve: List[float] = [self.config.initial_balance]
        
        self._order_counter = 0
        self._current_bar_index = 0
        self._current_bar: Optional[Dict] = None
        self._current_atr: float = 0.0
        self._data: Optional[pd.DataFrame] = None
        
        # Initialize trailing stop config if not provided
        if self.config.trailing_stop_enabled and self.config.trailing_stop_config is None:
            self.config.trailing_stop_config = TrailingStopConfig()

    def run(self) -> Dict[str, Any]:
        """Run the backtest and return results."""
        data = self.data_manager.load()
        self._data = data
        
        if data.empty:
            logger.warning("No data to backtest")
            return self._create_results()

        logger.info(f"Starting backtest with {len(data)} candles")
        logger.info(f"Initial balance: ${self.config.initial_balance:,.2f}")
        if self.config.trailing_stop_enabled:
            logger.info("Trailing stop enabled")

        # Initialize strategy if it has an init method
        if hasattr(self.strategy, "initialize"):
            self.strategy.initialize(self)

        # Process each bar
        for i in range(len(data)):
            self._current_bar_index = i
            self._current_bar = data.iloc[i].to_dict()
            bar_time = self._current_bar["timestamp"]

            # 0. Calculate current ATR
            if i >= self.config.atr_period:
                self._current_atr = calculate_atr_from_dataframe(
                    data.iloc[:i + 1], self.config.atr_period
                )

            # 1. Update trailing stops (before exit check)
            if self.config.trailing_stop_enabled:
                self._update_trailing_stops()

            # 2. Check stop loss / take profit
            self._check_exit_conditions()

            # 3. Process pending orders
            self._process_pending_orders()

            # 4. Let strategy generate signals
            bars_available = data.iloc[:i + 1]
            if hasattr(self.strategy, "on_bar"):
                self.strategy.on_bar(self, bars_available)

            # 5. Update equity and record
            self._update_equity()
            self.equity_curve.append(self.equity)

            # 6. Increment bars held and update price extremes for positions
            for pos in self.positions:
                pos.bars_held += 1
                # Track price extremes for trailing stop
                current = self.current_price
                if pos.order_type == OrderType.BUY:
                    pos.highest_price = max(pos.highest_price, current)
                else:
                    pos.lowest_price = min(pos.lowest_price, current)

        # Close any remaining positions at last price
        self._close_all_positions("end_of_backtest")

        logger.info(f"Backtest complete. {len(self.closed_trades)} trades executed.")
        return self._create_results()

    def buy(
        self,
        lot_size: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> int:
        """Place a buy order."""
        return self._create_order(OrderType.BUY, lot_size, stop_loss, take_profit)

    def sell(
        self,
        lot_size: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
    ) -> int:
        """Place a sell order."""
        return self._create_order(OrderType.SELL, lot_size, stop_loss, take_profit)

    def close_position(self, position_id: int, reason: str = "signal") -> bool:
        """Close a specific position."""
        for pos in self.positions:
            if pos.id == position_id:
                self._close_position(pos, reason)
                return True
        return False

    def close_all(self, reason: str = "signal") -> int:
        """Close all open positions."""
        count = len(self.positions)
        self._close_all_positions(reason)
        return count

    def get_positions(self, order_type: Optional[OrderType] = None) -> List[Position]:
        """Get open positions, optionally filtered by type."""
        if order_type:
            return [p for p in self.positions if p.order_type == order_type]
        return self.positions.copy()

    def has_position(self, order_type: Optional[OrderType] = None) -> bool:
        """Check if there are open positions."""
        if order_type:
            return any(p.order_type == order_type for p in self.positions)
        return len(self.positions) > 0

    @property
    def current_price(self) -> float:
        """Get current bar's close price."""
        return self._current_bar["close"] if self._current_bar else 0

    @property
    def current_bar(self) -> Optional[Dict]:
        """Get the current bar data."""
        return self._current_bar

    @property
    def bar_index(self) -> int:
        """Get current bar index."""
        return self._current_bar_index

    @property
    def current_atr(self) -> float:
        """Get current ATR value."""
        return self._current_atr

    def update_position_sl(self, position_id: int, new_sl: float) -> bool:
        """
        Update the stop loss for a position (used for trailing stop).
        
        Args:
            position_id: ID of the position to update
            new_sl: New stop loss price
            
        Returns:
            True if position was found and updated
        """
        for pos in self.positions:
            if pos.id == position_id:
                old_sl = pos.stop_loss
                pos.stop_loss = new_sl
                logger.debug(f"Position {position_id}: SL updated {old_sl} -> {new_sl}")
                return True
        return False

    def _update_trailing_stops(self):
        """Update trailing stops for all open positions."""
        if not self.config.trailing_stop_config:
            return
        
        config = self.config.trailing_stop_config
        current = self.current_price
        
        for pos in self.positions:
            # Create position state for trailing stop calculation
            state = PositionState(
                position_id=pos.id,
                direction=pos.order_type.value,
                entry_price=pos.entry_price,
                current_sl=pos.stop_loss,
                lot_size=pos.lot_size,
                highest_price=pos.highest_price,
                lowest_price=pos.lowest_price,
                breakeven_hit=pos.breakeven_hit,
            )
            
            # Process trailing stop
            new_sl, is_breakeven = process_trailing_stop(
                state, current, config, self._current_atr
            )
            
            if new_sl is not None:
                pos.stop_loss = new_sl
                if is_breakeven:
                    pos.breakeven_hit = True
                    logger.debug(f"Position {pos.id}: Moved to breakeven at {new_sl}")
                else:
                    logger.debug(f"Position {pos.id}: Trailing SL updated to {new_sl}")

    def buy_with_atr_sl(
        self,
        lot_size: float,
        sl_atr_multiplier: float = 2.0,
        tp_risk_reward: float = 2.0,
    ) -> int:
        """
        Place a buy order with ATR-based stop loss.
        
        Args:
            lot_size: Position size in lots
            sl_atr_multiplier: ATR multiplier for stop loss
            tp_risk_reward: Risk:Reward ratio for take profit
        """
        if self._current_atr == 0:
            # Fallback to fixed pips if ATR not available
            sl = self.current_price - (50 * 0.0001)
            tp = self.current_price + (100 * 0.0001)
        else:
            sl_distance = self._current_atr * sl_atr_multiplier
            sl = self.current_price - sl_distance
            tp = self.current_price + (sl_distance * tp_risk_reward)
        
        return self.buy(lot_size, stop_loss=sl, take_profit=tp)

    def sell_with_atr_sl(
        self,
        lot_size: float,
        sl_atr_multiplier: float = 2.0,
        tp_risk_reward: float = 2.0,
    ) -> int:
        """
        Place a sell order with ATR-based stop loss.
        
        Args:
            lot_size: Position size in lots
            sl_atr_multiplier: ATR multiplier for stop loss
            tp_risk_reward: Risk:Reward ratio for take profit
        """
        if self._current_atr == 0:
            # Fallback to fixed pips if ATR not available
            sl = self.current_price + (50 * 0.0001)
            tp = self.current_price - (100 * 0.0001)
        else:
            sl_distance = self._current_atr * sl_atr_multiplier
            sl = self.current_price + sl_distance
            tp = self.current_price - (sl_distance * tp_risk_reward)
        
        return self.sell(lot_size, stop_loss=sl, take_profit=tp)

    def _create_order(
        self,
        order_type: OrderType,
        lot_size: float,
        stop_loss: Optional[float],
        take_profit: Optional[float],
    ) -> int:
        """Create a new order."""
        if not self.config.allow_pyramiding and self.has_position():
            logger.debug("Pyramiding not allowed, skipping order")
            return -1

        if len(self.positions) >= self.config.max_positions:
            logger.debug("Max positions reached, skipping order")
            return -1

        self._order_counter += 1
        order = Order(
            id=self._order_counter,
            order_type=order_type,
            symbol=self.data_manager.symbol,
            lot_size=lot_size,
            entry_price=self.current_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
        )
        self.pending_orders.append(order)
        return order.id

    def _process_pending_orders(self):
        """Process pending orders at current bar."""
        if not self._current_bar:
            return

        filled_orders = []
        for order in self.pending_orders:
            # Apply slippage
            slippage = self.config.slippage_pips * 0.0001
            if order.order_type == OrderType.BUY:
                fill_price = order.entry_price + slippage + (self.config.spread_pips * 0.0001)
            else:
                fill_price = order.entry_price - slippage

            # Create position
            position = Position(
                id=order.id,
                order_type=order.order_type,
                symbol=order.symbol,
                lot_size=order.lot_size,
                entry_price=fill_price,
                entry_time=self._current_bar["timestamp"],
                stop_loss=order.stop_loss,
                take_profit=order.take_profit,
                # Initialize trailing stop tracking
                highest_price=fill_price,
                lowest_price=fill_price,
                breakeven_hit=False,
                initial_sl=order.stop_loss,
            )
            self.positions.append(position)

            # Deduct commission
            self.balance -= self.config.commission * order.lot_size

            order.status = OrderStatus.FILLED
            order.fill_price = fill_price
            order.fill_time = self._current_bar["timestamp"]
            filled_orders.append(order)

            logger.debug(f"Order filled: {order.order_type.value} {order.lot_size} @ {fill_price}")

        # Remove filled orders
        self.pending_orders = [o for o in self.pending_orders if o not in filled_orders]

    def _check_exit_conditions(self):
        """Check stop loss and take profit for all positions."""
        if not self._current_bar:
            return

        high = self._current_bar["high"]
        low = self._current_bar["low"]

        positions_to_close = []
        for pos in self.positions:
            reason = None
            exit_price = None

            if pos.order_type == OrderType.BUY:
                if pos.stop_loss and low <= pos.stop_loss:
                    reason = "stop_loss"
                    exit_price = pos.stop_loss
                elif pos.take_profit and high >= pos.take_profit:
                    reason = "take_profit"
                    exit_price = pos.take_profit
            else:  # SELL
                if pos.stop_loss and high >= pos.stop_loss:
                    reason = "stop_loss"
                    exit_price = pos.stop_loss
                elif pos.take_profit and low <= pos.take_profit:
                    reason = "take_profit"
                    exit_price = pos.take_profit

            if reason:
                positions_to_close.append((pos, exit_price, reason))

        for pos, exit_price, reason in positions_to_close:
            self._close_position(pos, reason, exit_price)

    def _close_position(
        self,
        position: Position,
        reason: str = "signal",
        exit_price: Optional[float] = None,
    ):
        """Close a position and record the trade."""
        if position not in self.positions:
            return

        if exit_price is None:
            exit_price = self.current_price

        # Calculate profit
        if position.order_type == OrderType.BUY:
            pips = (exit_price - position.entry_price) / 0.0001
        else:
            pips = (position.entry_price - exit_price) / 0.0001

        profit = pips * self.config.pip_value * position.lot_size

        # Apply commission on exit
        profit -= self.config.commission * position.lot_size

        # Update balance
        self.balance += profit

        # Record trade
        trade = Trade(
            id=position.id,
            order_type=position.order_type.value,
            symbol=position.symbol,
            lot_size=position.lot_size,
            entry_price=position.entry_price,
            exit_price=exit_price,
            entry_time=position.entry_time,
            exit_time=self._current_bar["timestamp"] if self._current_bar else datetime.utcnow(),
            profit=profit,
            bars_held=position.bars_held,
            exit_reason=reason,
        )
        self.closed_trades.append(trade)
        self.positions.remove(position)

        logger.debug(f"Position closed: {reason}, profit: ${profit:.2f}")

    def _close_all_positions(self, reason: str = "signal"):
        """Close all open positions."""
        for pos in self.positions.copy():
            self._close_position(pos, reason)

    def _update_equity(self):
        """Update current equity including unrealized P/L."""
        unrealized = 0.0
        current = self.current_price

        for pos in self.positions:
            if pos.order_type == OrderType.BUY:
                pips = (current - pos.entry_price) / 0.0001
            else:
                pips = (pos.entry_price - current) / 0.0001
            unrealized += pips * self.config.pip_value * pos.lot_size

        self.equity = self.balance + unrealized

    def _create_results(self) -> Dict[str, Any]:
        """Create the backtest results dictionary."""
        trades_list = [t.to_dict() for t in self.closed_trades]
        metrics = calculate_metrics(
            trades_list,
            self.equity_curve,
            self.config.initial_balance,
        )

        return {
            "metrics": metrics.to_dict(),
            "trades": trades_list,
            "equity_curve": self.equity_curve,
            "final_balance": self.balance,
            "final_equity": self.equity,
            "total_trades": len(self.closed_trades),
        }
