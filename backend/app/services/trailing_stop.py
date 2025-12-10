"""Trailing Stop Service - Adaptive Stop Loss Management."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from app.core.logging import get_logger


logger = get_logger(__name__)


class TrailingStopType(str, Enum):
    FIXED_PIPS = "fixed_pips"
    ATR_BASED = "atr_based"
    PERCENTAGE = "percentage"


@dataclass
class TrailingStopConfig:
    """Configuration for trailing stop behavior."""
    enabled: bool = True
    trailing_type: TrailingStopType = TrailingStopType.ATR_BASED
    activation_pips: float = 20.0  # Start trailing after X pips profit
    trail_distance_pips: float = 15.0  # Fixed pip distance for trailing
    atr_multiplier: float = 1.5  # ATR multiplier for ATR-based trailing
    percentage: float = 0.5  # Percentage for percentage-based trailing
    
    # Breakeven settings
    breakeven_enabled: bool = True
    breakeven_pips: float = 15.0  # Move SL to breakeven after X pips profit
    breakeven_offset_pips: float = 2.0  # Offset from entry (to cover spread)


@dataclass
class PositionState:
    """State of a position for trailing stop calculations."""
    position_id: int
    direction: str  # "BUY" or "SELL"
    entry_price: float
    current_sl: Optional[float]
    lot_size: float
    highest_price: float = 0.0  # Highest price since entry (for BUY)
    lowest_price: float = float('inf')  # Lowest price since entry (for SELL)
    breakeven_hit: bool = False


def calculate_profit_pips(
    entry_price: float,
    current_price: float,
    direction: str,
) -> float:
    """
    Calculate current profit in pips.
    
    Args:
        entry_price: Position entry price
        current_price: Current market price
        direction: "BUY" or "SELL"
        
    Returns:
        Profit in pips (positive = profit, negative = loss)
    """
    direction = direction.upper()
    
    if direction == "BUY":
        profit_pips = (current_price - entry_price) * 10000
    else:  # SELL
        profit_pips = (entry_price - current_price) * 10000
    
    return round(profit_pips, 1)


def check_breakeven(
    state: PositionState,
    current_price: float,
    config: TrailingStopConfig,
) -> Optional[float]:
    """
    Check if position should be moved to breakeven.
    
    Args:
        state: Current position state
        current_price: Current market price
        config: Trailing stop configuration
        
    Returns:
        New SL price if breakeven triggered, None otherwise
    """
    if not config.breakeven_enabled or state.breakeven_hit:
        return None
    
    profit_pips = calculate_profit_pips(
        state.entry_price,
        current_price,
        state.direction,
    )
    
    if profit_pips < config.breakeven_pips:
        return None
    
    # Move SL to breakeven (with small offset to cover spread)
    offset = config.breakeven_offset_pips * 0.0001
    
    if state.direction.upper() == "BUY":
        new_sl = state.entry_price + offset
        # Only update if new SL is higher than current
        if state.current_sl is None or new_sl > state.current_sl:
            logger.info(f"Position {state.position_id}: Breakeven triggered at {profit_pips:.1f} pips profit")
            return round(new_sl, 5)
    else:  # SELL
        new_sl = state.entry_price - offset
        # Only update if new SL is lower than current
        if state.current_sl is None or new_sl < state.current_sl:
            logger.info(f"Position {state.position_id}: Breakeven triggered at {profit_pips:.1f} pips profit")
            return round(new_sl, 5)
    
    return None


def calculate_trailing_stop(
    state: PositionState,
    current_price: float,
    config: TrailingStopConfig,
    atr: Optional[float] = None,
) -> Optional[float]:
    """
    Calculate new trailing stop level if position should be updated.
    
    Args:
        state: Current position state
        current_price: Current market price
        config: Trailing stop configuration
        atr: Current ATR value (required for ATR_BASED type)
        
    Returns:
        New SL price if trailing should update, None otherwise
    """
    if not config.enabled:
        return None
    
    direction = state.direction.upper()
    profit_pips = calculate_profit_pips(state.entry_price, current_price, direction)
    
    # Check if trailing should be activated
    if profit_pips < config.activation_pips:
        return None
    
    # Calculate trail distance
    if config.trailing_type == TrailingStopType.FIXED_PIPS:
        trail_distance = config.trail_distance_pips * 0.0001
    elif config.trailing_type == TrailingStopType.ATR_BASED:
        if atr is None or atr == 0:
            logger.warning("ATR not available for trailing stop, using fixed 15 pips")
            trail_distance = 15 * 0.0001
        else:
            trail_distance = atr * config.atr_multiplier
    elif config.trailing_type == TrailingStopType.PERCENTAGE:
        trail_distance = current_price * (config.percentage / 100)
    else:
        trail_distance = config.trail_distance_pips * 0.0001
    
    # Calculate new trailing SL
    if direction == "BUY":
        # Update highest price if current is higher
        if current_price > state.highest_price:
            state.highest_price = current_price
        
        # Calculate trailing SL from highest price
        new_sl = state.highest_price - trail_distance
        
        # Only update if new SL is higher than current
        if state.current_sl is None or new_sl > state.current_sl:
            # Also ensure it's above entry (we're in profit)
            if new_sl > state.entry_price:
                logger.debug(f"Position {state.position_id}: Trailing SL update {state.current_sl} -> {new_sl}")
                return round(new_sl, 5)
    
    else:  # SELL
        # Update lowest price if current is lower
        if current_price < state.lowest_price:
            state.lowest_price = current_price
        
        # Calculate trailing SL from lowest price
        new_sl = state.lowest_price + trail_distance
        
        # Only update if new SL is lower than current
        if state.current_sl is None or new_sl < state.current_sl:
            # Also ensure it's below entry (we're in profit)
            if new_sl < state.entry_price:
                logger.debug(f"Position {state.position_id}: Trailing SL update {state.current_sl} -> {new_sl}")
                return round(new_sl, 5)
    
    return None


def process_trailing_stop(
    state: PositionState,
    current_price: float,
    config: TrailingStopConfig,
    atr: Optional[float] = None,
) -> tuple[Optional[float], bool]:
    """
    Process trailing stop logic including breakeven check.
    
    Args:
        state: Current position state
        current_price: Current market price
        config: Trailing stop configuration
        atr: Current ATR value
        
    Returns:
        Tuple of (new_sl, breakeven_triggered)
        - new_sl: New SL price if update needed, None otherwise
        - breakeven_triggered: True if breakeven was just triggered
    """
    # First check for breakeven
    if not state.breakeven_hit:
        breakeven_sl = check_breakeven(state, current_price, config)
        if breakeven_sl is not None:
            state.breakeven_hit = True
            state.current_sl = breakeven_sl
            return breakeven_sl, True
    
    # Then check for trailing stop
    trailing_sl = calculate_trailing_stop(state, current_price, config, atr)
    if trailing_sl is not None:
        state.current_sl = trailing_sl
        return trailing_sl, False
    
    return None, False


def should_close_position(
    state: PositionState,
    current_price: float,
) -> bool:
    """
    Check if position should be closed due to SL hit.
    
    Args:
        state: Current position state
        current_price: Current market price (bid for BUY, ask for SELL)
        
    Returns:
        True if SL is hit
    """
    if state.current_sl is None:
        return False
    
    direction = state.direction.upper()
    
    if direction == "BUY":
        return current_price <= state.current_sl
    else:  # SELL
        return current_price >= state.current_sl


class TrailingStopManager:
    """Manager for multiple positions with trailing stops."""
    
    def __init__(self, config: Optional[TrailingStopConfig] = None):
        self.config = config or TrailingStopConfig()
        self.positions: dict[int, PositionState] = {}
    
    def add_position(
        self,
        position_id: int,
        direction: str,
        entry_price: float,
        stop_loss: Optional[float],
        lot_size: float = 0.1,
    ):
        """Add a position to be managed."""
        state = PositionState(
            position_id=position_id,
            direction=direction.upper(),
            entry_price=entry_price,
            current_sl=stop_loss,
            lot_size=lot_size,
            highest_price=entry_price,
            lowest_price=entry_price,
        )
        self.positions[position_id] = state
        logger.info(f"TrailingStopManager: Added position {position_id}")
    
    def remove_position(self, position_id: int):
        """Remove a position from management."""
        if position_id in self.positions:
            del self.positions[position_id]
            logger.info(f"TrailingStopManager: Removed position {position_id}")
    
    def update_price(
        self,
        current_price: float,
        atr: Optional[float] = None,
    ) -> list[tuple[int, float, bool]]:
        """
        Update all positions with new price.
        
        Args:
            current_price: Current market price
            atr: Current ATR value
            
        Returns:
            List of (position_id, new_sl, is_breakeven) for positions that need SL update
        """
        updates = []
        
        for pos_id, state in self.positions.items():
            new_sl, is_breakeven = process_trailing_stop(
                state, current_price, self.config, atr
            )
            if new_sl is not None:
                updates.append((pos_id, new_sl, is_breakeven))
        
        return updates
    
    def get_positions_to_close(self, current_price: float) -> list[int]:
        """Get list of position IDs that should be closed due to SL hit."""
        to_close = []
        for pos_id, state in self.positions.items():
            if should_close_position(state, current_price):
                to_close.append(pos_id)
                logger.info(f"Position {pos_id}: SL hit at {current_price}")
        return to_close
    
    def get_position_state(self, position_id: int) -> Optional[PositionState]:
        """Get state of a specific position."""
        return self.positions.get(position_id)
    
    def update_config(self, config: TrailingStopConfig):
        """Update trailing stop configuration."""
        self.config = config


# Default trailing stop configurations
TRAILING_CONFIGS = {
    "conservative": TrailingStopConfig(
        enabled=True,
        trailing_type=TrailingStopType.ATR_BASED,
        activation_pips=30,
        atr_multiplier=2.0,
        breakeven_enabled=True,
        breakeven_pips=20,
    ),
    "moderate": TrailingStopConfig(
        enabled=True,
        trailing_type=TrailingStopType.ATR_BASED,
        activation_pips=20,
        atr_multiplier=1.5,
        breakeven_enabled=True,
        breakeven_pips=15,
    ),
    "aggressive": TrailingStopConfig(
        enabled=True,
        trailing_type=TrailingStopType.FIXED_PIPS,
        activation_pips=10,
        trail_distance_pips=10,
        breakeven_enabled=True,
        breakeven_pips=10,
    ),
}


def get_trailing_config(profile: str = "moderate") -> TrailingStopConfig:
    """Get trailing stop configuration for a given profile."""
    return TRAILING_CONFIGS.get(profile.lower(), TRAILING_CONFIGS["moderate"])
