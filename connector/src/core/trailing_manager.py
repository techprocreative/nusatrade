"""Trailing Stop Manager for real-time position management on MT5."""

import logging
from dataclasses import dataclass
from typing import Optional, Dict, List
from datetime import datetime


logger = logging.getLogger(__name__)


@dataclass
class TrailingConfig:
    """Configuration for trailing stop behavior."""
    enabled: bool = True
    activation_pips: float = 20.0
    trail_distance_pips: float = 15.0
    atr_multiplier: float = 1.5
    use_atr: bool = True
    breakeven_enabled: bool = True
    breakeven_pips: float = 15.0
    breakeven_offset_pips: float = 2.0


@dataclass
class PositionTracker:
    """Tracks state of a position for trailing stop."""
    ticket: int
    symbol: str
    direction: str  # "BUY" or "SELL"
    entry_price: float
    current_sl: Optional[float]
    lot_size: float
    highest_price: float
    lowest_price: float
    breakeven_hit: bool = False
    last_update: Optional[datetime] = None


class TrailingStopManager:
    """
    Manages trailing stops for MT5 positions in real-time.
    
    This class monitors positions and updates stop losses when:
    1. Price moves X pips in profit (activation)
    2. New high/low is made (trailing)
    3. Breakeven threshold is reached
    """

    def __init__(self, mt5_service, config: Optional[TrailingConfig] = None):
        self.mt5 = mt5_service
        self.config = config or TrailingConfig()
        self.tracked_positions: Dict[int, PositionTracker] = {}
        self._current_atr: Dict[str, float] = {}

    def set_config(self, config: TrailingConfig):
        """Update trailing stop configuration."""
        self.config = config
        logger.info(f"Trailing config updated: {config}")

    def update_atr(self, symbol: str, atr: float):
        """Update ATR value for a symbol."""
        self._current_atr[symbol] = atr

    def sync_positions(self, positions: List[dict]):
        """
        Sync tracked positions with MT5 positions.
        
        Args:
            positions: List of position dicts from MT5 with keys:
                ticket, symbol, type (BUY/SELL), volume, price_open, sl, tp
        """
        current_tickets = set()
        
        for pos in positions:
            ticket = pos.get("ticket")
            current_tickets.add(ticket)
            
            if ticket not in self.tracked_positions:
                # New position - start tracking
                direction = "BUY" if pos.get("type", "").upper() == "BUY" else "SELL"
                entry = pos.get("price_open", pos.get("open_price", 0))
                
                self.tracked_positions[ticket] = PositionTracker(
                    ticket=ticket,
                    symbol=pos.get("symbol", ""),
                    direction=direction,
                    entry_price=entry,
                    current_sl=pos.get("sl"),
                    lot_size=pos.get("volume", pos.get("lot_size", 0.1)),
                    highest_price=entry,
                    lowest_price=entry,
                )
                logger.info(f"Now tracking position {ticket}: {direction} {pos.get('symbol')}")
            else:
                # Update existing tracker
                tracker = self.tracked_positions[ticket]
                tracker.current_sl = pos.get("sl")
        
        # Remove closed positions
        closed = set(self.tracked_positions.keys()) - current_tickets
        for ticket in closed:
            del self.tracked_positions[ticket]
            logger.info(f"Stopped tracking position {ticket} (closed)")

    def process_tick(self, symbol: str, bid: float, ask: float) -> List[dict]:
        """
        Process a price tick and check for trailing stop updates.
        
        Args:
            symbol: Trading symbol
            bid: Current bid price
            ask: Current ask price
            
        Returns:
            List of SL update commands to send to MT5
        """
        if not self.config.enabled:
            return []
        
        updates = []
        current_price = (bid + ask) / 2  # Mid price
        
        for ticket, tracker in self.tracked_positions.items():
            if tracker.symbol != symbol:
                continue
            
            # Get price for position direction
            price = bid if tracker.direction == "BUY" else ask
            
            # Update price extremes
            if tracker.direction == "BUY":
                if price > tracker.highest_price:
                    tracker.highest_price = price
            else:
                if price < tracker.lowest_price:
                    tracker.lowest_price = price
            
            # Check for SL update
            new_sl = self._calculate_new_sl(tracker, price)
            
            if new_sl is not None:
                updates.append({
                    "ticket": ticket,
                    "symbol": symbol,
                    "new_sl": new_sl,
                    "reason": "breakeven" if not tracker.breakeven_hit else "trailing",
                })
                tracker.current_sl = new_sl
                tracker.last_update = datetime.utcnow()
        
        return updates

    def _calculate_new_sl(self, tracker: PositionTracker, current_price: float) -> Optional[float]:
        """Calculate new SL if trailing should be updated."""
        entry = tracker.entry_price
        direction = tracker.direction
        
        # Calculate current profit in pips
        if direction == "BUY":
            profit_pips = (current_price - entry) * 10000
        else:
            profit_pips = (entry - current_price) * 10000
        
        # Check breakeven first
        if self.config.breakeven_enabled and not tracker.breakeven_hit:
            if profit_pips >= self.config.breakeven_pips:
                tracker.breakeven_hit = True
                offset = self.config.breakeven_offset_pips * 0.0001
                
                if direction == "BUY":
                    new_sl = entry + offset
                    if tracker.current_sl is None or new_sl > tracker.current_sl:
                        logger.info(f"Position {tracker.ticket}: Moving to breakeven at {new_sl}")
                        return round(new_sl, 5)
                else:
                    new_sl = entry - offset
                    if tracker.current_sl is None or new_sl < tracker.current_sl:
                        logger.info(f"Position {tracker.ticket}: Moving to breakeven at {new_sl}")
                        return round(new_sl, 5)
        
        # Check trailing activation
        if profit_pips < self.config.activation_pips:
            return None
        
        # Calculate trail distance
        if self.config.use_atr and tracker.symbol in self._current_atr:
            trail_distance = self._current_atr[tracker.symbol] * self.config.atr_multiplier
        else:
            trail_distance = self.config.trail_distance_pips * 0.0001
        
        # Calculate new trailing SL
        if direction == "BUY":
            new_sl = tracker.highest_price - trail_distance
            # Only update if higher than current SL and above entry
            if new_sl > entry and (tracker.current_sl is None or new_sl > tracker.current_sl):
                logger.debug(f"Position {tracker.ticket}: Trailing SL {tracker.current_sl} -> {new_sl}")
                return round(new_sl, 5)
        else:
            new_sl = tracker.lowest_price + trail_distance
            # Only update if lower than current SL and below entry
            if new_sl < entry and (tracker.current_sl is None or new_sl < tracker.current_sl):
                logger.debug(f"Position {tracker.ticket}: Trailing SL {tracker.current_sl} -> {new_sl}")
                return round(new_sl, 5)
        
        return None

    def execute_sl_update(self, ticket: int, new_sl: float) -> bool:
        """
        Execute SL update on MT5.
        
        Args:
            ticket: Position ticket number
            new_sl: New stop loss price
            
        Returns:
            True if update was successful
        """
        try:
            result = self.mt5.modify_position(ticket=ticket, stop_loss=new_sl)
            if result and result.success:
                logger.info(f"Position {ticket}: SL updated to {new_sl}")
                return True
            else:
                logger.error(f"Failed to update SL for position {ticket}")
                return False
        except Exception as e:
            logger.error(f"Exception updating SL for position {ticket}: {e}")
            return False

    def get_tracked_positions(self) -> Dict[int, dict]:
        """Get all tracked positions and their state."""
        return {
            ticket: {
                "ticket": tracker.ticket,
                "symbol": tracker.symbol,
                "direction": tracker.direction,
                "entry_price": tracker.entry_price,
                "current_sl": tracker.current_sl,
                "highest_price": tracker.highest_price,
                "lowest_price": tracker.lowest_price,
                "breakeven_hit": tracker.breakeven_hit,
            }
            for ticket, tracker in self.tracked_positions.items()
        }

    def remove_position(self, ticket: int):
        """Stop tracking a position."""
        if ticket in self.tracked_positions:
            del self.tracked_positions[ticket]
            logger.info(f"Removed position {ticket} from tracking")
