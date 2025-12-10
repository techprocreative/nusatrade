"""Risk Management Service - SL/TP Calculation with ATR and Adaptive Methods."""

from enum import Enum
from typing import List, Optional, Tuple
from dataclasses import dataclass

from app.core.logging import get_logger


logger = get_logger(__name__)


class SLType(str, Enum):
    FIXED_PIPS = "fixed_pips"
    ATR_BASED = "atr_based"
    PERCENTAGE = "percentage"


class TPType(str, Enum):
    FIXED_PIPS = "fixed_pips"
    RISK_REWARD = "risk_reward"
    ATR_BASED = "atr_based"


class Direction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class RiskConfig:
    """Configuration for risk management calculations."""
    sl_type: SLType = SLType.ATR_BASED
    sl_value: float = 2.0  # pips, ATR multiplier, or percentage
    tp_type: TPType = TPType.RISK_REWARD
    tp_value: float = 2.0  # pips, risk:reward ratio, or ATR multiplier
    risk_per_trade_percent: float = 2.0
    max_position_size: float = 1.0
    min_position_size: float = 0.01


def calculate_atr(candles: List[dict], period: int = 14) -> float:
    """
    Calculate Average True Range (ATR) for volatility-based SL/TP.
    
    Args:
        candles: List of OHLC candles with 'high', 'low', 'close' keys
        period: ATR period (default 14)
        
    Returns:
        ATR value in price units
    """
    if len(candles) < period + 1:
        logger.warning(f"Not enough candles for ATR calculation. Need {period + 1}, got {len(candles)}")
        return 0.0
    
    true_ranges = []
    
    for i in range(1, len(candles)):
        high = candles[i].get("high", 0)
        low = candles[i].get("low", 0)
        prev_close = candles[i - 1].get("close", 0)
        
        tr1 = high - low
        tr2 = abs(high - prev_close)
        tr3 = abs(low - prev_close)
        
        true_range = max(tr1, tr2, tr3)
        true_ranges.append(true_range)
    
    if len(true_ranges) < period:
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0
    
    # Simple Moving Average of True Range
    atr = sum(true_ranges[-period:]) / period
    return atr


def calculate_atr_from_dataframe(df, period: int = 14) -> float:
    """Calculate ATR from pandas DataFrame."""
    if len(df) < period + 1:
        return 0.0
    
    high = df["high"].values
    low = df["low"].values
    close = df["close"].values
    
    true_ranges = []
    for i in range(1, len(df)):
        tr1 = high[i] - low[i]
        tr2 = abs(high[i] - close[i - 1])
        tr3 = abs(low[i] - close[i - 1])
        true_ranges.append(max(tr1, tr2, tr3))
    
    if len(true_ranges) < period:
        return sum(true_ranges) / len(true_ranges) if true_ranges else 0.0
    
    return sum(true_ranges[-period:]) / period


def calculate_stop_loss(
    entry_price: float,
    direction: str,
    sl_type: SLType,
    sl_value: float,
    atr: Optional[float] = None,
) -> float:
    """
    Calculate stop loss price based on type and parameters.
    
    Args:
        entry_price: Entry price of the trade
        direction: "BUY" or "SELL"
        sl_type: Type of stop loss calculation
        sl_value: Value for calculation (pips, ATR multiplier, or percentage)
        atr: Current ATR value (required for ATR_BASED)
        
    Returns:
        Stop loss price
    """
    direction = direction.upper()
    
    if sl_type == SLType.FIXED_PIPS:
        sl_distance = sl_value * 0.0001  # Convert pips to price
    elif sl_type == SLType.ATR_BASED:
        if atr is None or atr == 0:
            logger.warning("ATR not provided for ATR_BASED SL, using 50 pips default")
            sl_distance = 50 * 0.0001
        else:
            sl_distance = atr * sl_value  # ATR * multiplier
    elif sl_type == SLType.PERCENTAGE:
        sl_distance = entry_price * (sl_value / 100)
    else:
        sl_distance = 50 * 0.0001  # Default 50 pips
    
    if direction == "BUY":
        stop_loss = entry_price - sl_distance
    else:  # SELL
        stop_loss = entry_price + sl_distance
    
    return round(stop_loss, 5)


def calculate_take_profit(
    entry_price: float,
    direction: str,
    tp_type: TPType,
    tp_value: float,
    stop_loss: Optional[float] = None,
    atr: Optional[float] = None,
) -> float:
    """
    Calculate take profit price based on type and parameters.
    
    Args:
        entry_price: Entry price of the trade
        direction: "BUY" or "SELL"
        tp_type: Type of take profit calculation
        tp_value: Value for calculation (pips, risk:reward ratio, or ATR multiplier)
        stop_loss: Stop loss price (required for RISK_REWARD)
        atr: Current ATR value (required for ATR_BASED)
        
    Returns:
        Take profit price
    """
    direction = direction.upper()
    
    if tp_type == TPType.FIXED_PIPS:
        tp_distance = tp_value * 0.0001  # Convert pips to price
    elif tp_type == TPType.RISK_REWARD:
        if stop_loss is None:
            logger.warning("Stop loss not provided for RISK_REWARD TP, using 100 pips default")
            tp_distance = 100 * 0.0001
        else:
            sl_distance = abs(entry_price - stop_loss)
            tp_distance = sl_distance * tp_value  # SL distance * R:R ratio
    elif tp_type == TPType.ATR_BASED:
        if atr is None or atr == 0:
            logger.warning("ATR not provided for ATR_BASED TP, using 100 pips default")
            tp_distance = 100 * 0.0001
        else:
            tp_distance = atr * tp_value  # ATR * multiplier
    else:
        tp_distance = 100 * 0.0001  # Default 100 pips
    
    if direction == "BUY":
        take_profit = entry_price + tp_distance
    else:  # SELL
        take_profit = entry_price - tp_distance
    
    return round(take_profit, 5)


def calculate_sl_tp(
    entry_price: float,
    direction: str,
    config: RiskConfig,
    atr: Optional[float] = None,
) -> Tuple[float, float]:
    """
    Calculate both SL and TP in one call.
    
    Args:
        entry_price: Entry price of the trade
        direction: "BUY" or "SELL"
        config: RiskConfig with SL/TP settings
        atr: Current ATR value
        
    Returns:
        Tuple of (stop_loss, take_profit) prices
    """
    stop_loss = calculate_stop_loss(
        entry_price=entry_price,
        direction=direction,
        sl_type=config.sl_type,
        sl_value=config.sl_value,
        atr=atr,
    )
    
    take_profit = calculate_take_profit(
        entry_price=entry_price,
        direction=direction,
        tp_type=config.tp_type,
        tp_value=config.tp_value,
        stop_loss=stop_loss,
        atr=atr,
    )
    
    return stop_loss, take_profit


def calculate_position_size(
    account_balance: float,
    risk_percent: float,
    entry_price: float,
    stop_loss: float,
    pip_value: float = 10.0,
    min_lot: float = 0.01,
    max_lot: float = 10.0,
) -> float:
    """
    Calculate position size based on risk management.
    
    Args:
        account_balance: Current account balance
        risk_percent: Percentage of account to risk (e.g., 2.0 for 2%)
        entry_price: Entry price
        stop_loss: Stop loss price
        pip_value: Value per pip per standard lot (default $10)
        min_lot: Minimum lot size
        max_lot: Maximum lot size
        
    Returns:
        Calculated lot size
    """
    if stop_loss == entry_price:
        return min_lot
    
    risk_amount = account_balance * (risk_percent / 100)
    sl_distance_pips = abs(entry_price - stop_loss) * 10000  # Convert to pips
    
    if sl_distance_pips == 0:
        return min_lot
    
    lot_size = risk_amount / (sl_distance_pips * pip_value)
    
    # Apply limits
    lot_size = max(min_lot, min(max_lot, lot_size))
    
    # Round to 2 decimal places
    return round(lot_size, 2)


def validate_sl_tp(
    entry_price: float,
    direction: str,
    stop_loss: Optional[float],
    take_profit: Optional[float],
) -> List[str]:
    """
    Validate SL and TP values are logical.
    
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    direction = direction.upper()
    
    if stop_loss is not None:
        if stop_loss <= 0:
            errors.append("Stop loss must be positive")
        elif direction == "BUY" and stop_loss >= entry_price:
            errors.append("Stop loss must be below entry for BUY orders")
        elif direction == "SELL" and stop_loss <= entry_price:
            errors.append("Stop loss must be above entry for SELL orders")
    
    if take_profit is not None:
        if take_profit <= 0:
            errors.append("Take profit must be positive")
        elif direction == "BUY" and take_profit <= entry_price:
            errors.append("Take profit must be above entry for BUY orders")
        elif direction == "SELL" and take_profit >= entry_price:
            errors.append("Take profit must be below entry for SELL orders")
    
    return errors


def get_risk_reward_ratio(
    entry_price: float,
    stop_loss: float,
    take_profit: float,
) -> float:
    """
    Calculate risk:reward ratio for a trade.
    
    Returns:
        Risk:reward ratio (e.g., 2.0 means TP is 2x the SL distance)
    """
    sl_distance = abs(entry_price - stop_loss)
    tp_distance = abs(take_profit - entry_price)
    
    if sl_distance == 0:
        return 0.0
    
    return round(tp_distance / sl_distance, 2)


# Default configurations for different risk profiles
RISK_PROFILES = {
    "conservative": RiskConfig(
        sl_type=SLType.ATR_BASED,
        sl_value=2.5,
        tp_type=TPType.RISK_REWARD,
        tp_value=1.5,
        risk_per_trade_percent=1.0,
        max_position_size=0.05,
    ),
    "moderate": RiskConfig(
        sl_type=SLType.ATR_BASED,
        sl_value=2.0,
        tp_type=TPType.RISK_REWARD,
        tp_value=2.0,
        risk_per_trade_percent=2.0,
        max_position_size=0.1,
    ),
    "aggressive": RiskConfig(
        sl_type=SLType.ATR_BASED,
        sl_value=1.5,
        tp_type=TPType.RISK_REWARD,
        tp_value=3.0,
        risk_per_trade_percent=3.0,
        max_position_size=0.2,
    ),
}


def get_risk_config(profile: str = "moderate") -> RiskConfig:
    """Get risk configuration for a given profile."""
    return RISK_PROFILES.get(profile.lower(), RISK_PROFILES["moderate"])
