"""Example MA Crossover strategy for backtesting."""

from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from app.backtesting.engine import BacktestEngine


class MACrossoverStrategy:
    """Moving Average Crossover Strategy.
    
    Buys when fast MA crosses above slow MA.
    Sells when fast MA crosses below slow MA.
    """

    def __init__(
        self,
        fast_period: int = 10,
        slow_period: int = 20,
        lot_size: float = 0.1,
        stop_loss_pips: float = 50,
        take_profit_pips: float = 100,
    ):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.lot_size = lot_size
        self.stop_loss_pips = stop_loss_pips
        self.take_profit_pips = take_profit_pips
        
        self._prev_fast = None
        self._prev_slow = None

    def initialize(self, engine: "BacktestEngine"):
        """Called once before backtest starts."""
        pass

    def on_bar(self, engine: "BacktestEngine", data: pd.DataFrame):
        """Called on each bar during backtest."""
        if len(data) < self.slow_period:
            return

        # Calculate MAs
        fast_ma = data["close"].rolling(self.fast_period).mean().iloc[-1]
        slow_ma = data["close"].rolling(self.slow_period).mean().iloc[-1]

        if self._prev_fast is None or self._prev_slow is None:
            self._prev_fast = fast_ma
            self._prev_slow = slow_ma
            return

        current_price = engine.current_price

        # Check for crossover
        prev_diff = self._prev_fast - self._prev_slow
        curr_diff = fast_ma - slow_ma

        # Bullish crossover: fast crosses above slow
        if prev_diff <= 0 < curr_diff:
            if not engine.has_position():
                sl = current_price - (self.stop_loss_pips * 0.0001)
                tp = current_price + (self.take_profit_pips * 0.0001)
                engine.buy(self.lot_size, stop_loss=sl, take_profit=tp)

        # Bearish crossover: fast crosses below slow
        elif prev_diff >= 0 > curr_diff:
            if not engine.has_position():
                sl = current_price + (self.stop_loss_pips * 0.0001)
                tp = current_price - (self.take_profit_pips * 0.0001)
                engine.sell(self.lot_size, stop_loss=sl, take_profit=tp)

        # Update previous values
        self._prev_fast = fast_ma
        self._prev_slow = slow_ma


class RSIStrategy:
    """RSI Overbought/Oversold Strategy.
    
    Buys when RSI is oversold (< 30).
    Sells when RSI is overbought (> 70).
    """

    def __init__(
        self,
        rsi_period: int = 14,
        oversold: float = 30,
        overbought: float = 70,
        lot_size: float = 0.1,
        stop_loss_pips: float = 50,
        take_profit_pips: float = 100,
    ):
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.lot_size = lot_size
        self.stop_loss_pips = stop_loss_pips
        self.take_profit_pips = take_profit_pips

    def initialize(self, engine: "BacktestEngine"):
        """Called once before backtest starts."""
        pass

    def _calculate_rsi(self, prices: pd.Series) -> float:
        """Calculate RSI."""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(self.rsi_period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(self.rsi_period).mean()
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    def on_bar(self, engine: "BacktestEngine", data: pd.DataFrame):
        """Called on each bar during backtest."""
        if len(data) < self.rsi_period + 1:
            return

        rsi = self._calculate_rsi(data["close"])
        current_price = engine.current_price

        if rsi < self.oversold and not engine.has_position():
            sl = current_price - (self.stop_loss_pips * 0.0001)
            tp = current_price + (self.take_profit_pips * 0.0001)
            engine.buy(self.lot_size, stop_loss=sl, take_profit=tp)

        elif rsi > self.overbought and not engine.has_position():
            sl = current_price + (self.stop_loss_pips * 0.0001)
            tp = current_price - (self.take_profit_pips * 0.0001)
            engine.sell(self.lot_size, stop_loss=sl, take_profit=tp)
