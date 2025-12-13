"""
Improved Feature Engineering with Gold-Specific Features
and Profitable Trade Labeling.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any


class ImprovedFeatureEngineer:
    """Enhanced feature engineering for XAUUSD trading."""

    def __init__(self):
        pass

    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Build comprehensive features including Gold-specific indicators.

        Improvements over original:
        1. Trading session indicators (London, NY, overlap)
        2. Volatility regime classification
        3. Trend strength indicators
        4. Price distance from key levels
        5. Volume regime indicators
        """
        df = df.copy()

        # Ensure timestamp is datetime
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df['hour'] = df['timestamp'].dt.hour
            df['day_of_week'] = df['timestamp'].dt.dayofweek

        # === ORIGINAL FEATURES ===
        df = self._add_basic_features(df)

        # === GOLD-SPECIFIC FEATURES ===
        df = self._add_session_features(df)
        df = self._add_volatility_regime_features(df)
        df = self._add_trend_strength_features(df)
        df = self._add_price_level_features(df)

        return df

    def _add_basic_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add basic technical indicators (original features)."""

        # Moving Averages
        for period in [20, 50, 100, 200]:
            df[f'sma_{period}'] = df['close'].rolling(window=period).mean()
            df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()

        # Price relative to MAs
        df['price_vs_sma_20'] = (df['close'] - df['sma_20']) / df['sma_20']
        df['price_vs_sma_50'] = (df['close'] - df['sma_50']) / df['sma_50']

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(window=14).mean()
        df['atr_percent'] = df['atr'] / df['close'] * 100

        # ADX
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()
        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr14 = true_range.rolling(window=14).sum()
        plus_di = 100 * (plus_dm.rolling(window=14).sum() / tr14)
        minus_di = 100 * (minus_dm.rolling(window=14).sum() / tr14)

        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        df['adx'] = dx.rolling(window=14).mean()

        # Volume indicators
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']

        # OBV
        df['obv'] = (np.sign(df['close'].diff()) * df['volume']).fillna(0).cumsum()

        # Volatility
        df['volatility_20'] = df['close'].rolling(window=20).std() / df['close'].rolling(window=20).mean()

        return df

    def _add_session_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add trading session indicators (Gold-specific)."""

        if 'hour' not in df.columns:
            return df

        # London session (8:00 - 16:00 UTC)
        df['london_session'] = ((df['hour'] >= 8) & (df['hour'] < 16)).astype(int)

        # New York session (13:00 - 21:00 UTC)
        df['ny_session'] = ((df['hour'] >= 13) & (df['hour'] < 21)).astype(int)

        # London-NY overlap (13:00 - 16:00 UTC) - Most volatile
        df['session_overlap'] = ((df['hour'] >= 13) & (df['hour'] < 16)).astype(int)

        # Asian session (0:00 - 8:00 UTC) - Typically quiet
        df['asian_session'] = (df['hour'] < 8).astype(int)

        # Avoid Friday close (21:00+ on Friday)
        if 'day_of_week' in df.columns:
            df['friday_close'] = ((df['day_of_week'] == 4) & (df['hour'] >= 21)).astype(int)

        return df

    def _add_volatility_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volatility regime classification."""

        # Calculate rolling volatility percentile
        rolling_vol = df['atr_percent'].rolling(window=100).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1] if len(x) > 0 else np.nan
        )

        # Classify into regimes
        df['vol_regime_low'] = (rolling_vol < 0.33).astype(int)
        df['vol_regime_medium'] = ((rolling_vol >= 0.33) & (rolling_vol < 0.67)).astype(int)
        df['vol_regime_high'] = (rolling_vol >= 0.67).astype(int)

        # Volatility expanding/contracting
        df['vol_expanding'] = (df['atr_percent'] > df['atr_percent'].shift(5)).astype(int)

        return df

    def _add_trend_strength_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add trend strength and direction indicators."""

        # Strong trend (ADX > 25)
        df['strong_trend'] = (df['adx'] > 25).astype(int)

        # Trend direction (price vs 200 SMA)
        df['uptrend'] = (df['close'] > df['sma_200']).astype(int)
        df['downtrend'] = (df['close'] < df['sma_200']).astype(int)

        # Momentum (rate of change)
        df['roc_5'] = (df['close'] - df['close'].shift(5)) / df['close'].shift(5) * 100
        df['roc_10'] = (df['close'] - df['close'].shift(10)) / df['close'].shift(10) * 100

        # Higher highs / Lower lows
        df['higher_high'] = (df['high'] > df['high'].shift(5)).astype(int)
        df['lower_low'] = (df['low'] < df['low'].shift(5)).astype(int)

        return df

    def _add_price_level_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add features based on key price levels."""

        # Distance from daily high/low
        df['daily_high'] = df['high'].rolling(window=24).max()
        df['daily_low'] = df['low'].rolling(window=24).min()

        df['dist_from_daily_high'] = (df['daily_high'] - df['close']) / df['close'] * 100
        df['dist_from_daily_low'] = (df['close'] - df['daily_low']) / df['close'] * 100

        # Position in daily range
        daily_range = df['daily_high'] - df['daily_low']
        df['position_in_range'] = (df['close'] - df['daily_low']) / daily_range

        # Recent price action
        df['candle_size'] = (df['high'] - df['low']) / df['close'] * 100
        df['body_size'] = np.abs(df['close'] - df['open']) / df['close'] * 100
        df['upper_wick'] = (df['high'] - df[['close', 'open']].max(axis=1)) / df['close'] * 100
        df['lower_wick'] = (df[['close', 'open']].min(axis=1) - df['low']) / df['close'] * 100

        return df

    def create_profitable_target(
        self,
        df: pd.DataFrame,
        spread_pips: float = 3.0,
        profit_target_atr: float = 1.5,
        stop_loss_atr: float = 0.8,
        max_holding_hours: int = 24
    ) -> pd.DataFrame:
        """
        Create target based on whether trade would be profitable.

        This is MUCH better than fixed-candle exit!

        Args:
            df: DataFrame with OHLCV data and features
            spread_pips: Spread cost in pips
            profit_target_atr: Profit target as multiple of ATR
            stop_loss_atr: Stop loss as multiple of ATR
            max_holding_hours: Maximum time to hold position

        Returns:
            DataFrame with 'target_buy' and 'target_sell' columns
        """
        df = df.copy()

        # Convert spread from pips to price
        spread_cost = spread_pips / 10000 * df['close']

        # Calculate dynamic profit target and stop loss
        profit_target = df['atr'] * profit_target_atr
        stop_loss = df['atr'] * stop_loss_atr

        # Initialize targets
        df['target_buy'] = 0  # Would BUY trade be profitable?
        df['target_sell'] = 0  # Would SELL trade be profitable?

        # For each candle, simulate both BUY and SELL trades
        for i in range(len(df) - max_holding_hours):
            entry_price = df.iloc[i]['close']
            entry_atr = df.iloc[i]['atr']

            if pd.isna(entry_atr):
                continue

            # BUY trade simulation
            buy_entry = entry_price + spread_cost.iloc[i]  # Pay spread on entry
            buy_tp = buy_entry + profit_target.iloc[i]
            buy_sl = buy_entry - stop_loss.iloc[i]

            # SELL trade simulation
            sell_entry = entry_price - spread_cost.iloc[i]
            sell_tp = sell_entry - profit_target.iloc[i]
            sell_sl = sell_entry + stop_loss.iloc[i]

            # Check next candles to see if TP or SL is hit
            buy_profitable = False
            sell_profitable = False
            buy_active = True
            sell_active = True

            for j in range(i + 1, min(i + max_holding_hours + 1, len(df))):
                candle_high = df.iloc[j]['high']
                candle_low = df.iloc[j]['low']

                # Check BUY trade (only if still active)
                if buy_active and not buy_profitable:
                    if candle_high >= buy_tp:
                        buy_profitable = True
                        buy_active = False  # TP hit, stop checking this trade
                    elif candle_low <= buy_sl:
                        buy_profitable = False
                        buy_active = False  # SL hit, stop checking this trade

                # Check SELL trade (only if still active)
                if sell_active and not sell_profitable:
                    if candle_low <= sell_tp:
                        sell_profitable = True
                        sell_active = False  # TP hit, stop checking this trade
                    elif candle_high >= sell_sl:
                        sell_profitable = False
                        sell_active = False  # SL hit, stop checking this trade

                # If both trades are closed, exit loop
                if not buy_active and not sell_active:
                    break

            # Set targets
            df.loc[df.index[i], 'target_buy'] = 1 if buy_profitable else 0
            df.loc[df.index[i], 'target_sell'] = 1 if sell_profitable else 0

        # Create combined target: 2 = BUY, 1 = SELL, 0 = HOLD
        df['target'] = 0  # Default HOLD
        df.loc[df['target_buy'] == 1, 'target'] = 2  # BUY
        df.loc[df['target_sell'] == 1, 'target'] = 1  # SELL

        # If both would be profitable, choose based on higher probability
        # (For now, prioritize BUY)
        df.loc[(df['target_buy'] == 1) & (df['target_sell'] == 1), 'target'] = 2

        return df
