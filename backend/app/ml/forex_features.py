"""
Forex-Specific Feature Engineering for Currency Pairs

This module provides feature engineering specifically designed for forex pairs like EURUSD,
focusing on characteristics that differentiate forex from commodities:

Key Differences from Commodities (XAUUSD):
- Mean reversion tendency vs trending
- Strong support/resistance at psychological levels
- Session-based volatility patterns
- Lower overall volatility but more frequent reversals
- Interest rate differential sensitivity

Features Focus:
1. Mean Reversion Indicators
2. Support/Resistance Levels
3. Session Analysis (Asian/London/NY)
4. Volatility Regime Detection
5. Trend vs Range Classification
"""

import pandas as pd
import numpy as np
from typing import Optional


class ForexFeatureEngineer:
    """
    Feature engineering for forex currency pairs.

    Optimized for EURUSD characteristics:
    - Mean reversion patterns
    - Psychological level respect
    - Session-based behavior
    - Range vs trend detection
    """

    def __init__(self):
        """Initialize the forex feature engineer."""
        pass

    def build_forex_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Build comprehensive forex-specific feature set.

        Args:
            df: DataFrame with columns [timestamp, open, high, low, close, volume]

        Returns:
            DataFrame with all forex features added
        """
        print("Building forex-specific features...")

        # Make a copy to avoid modifying original
        df = df.copy()

        # 1. Base technical indicators (foundation)
        df = self._add_base_indicators(df)

        # 2. Mean reversion features (CRITICAL for forex)
        df = self._add_mean_reversion_features(df)

        # 3. Session and time-based features
        df = self._add_session_features(df)

        # 4. Support/Resistance features
        df = self._add_support_resistance_features(df)

        # 5. Volatility regime features
        df = self._add_volatility_regime_features(df)

        # 6. Trend vs Range detection
        df = self._add_trend_range_features(df)

        # 7. Momentum features (for trend trading)
        df = self._add_momentum_features(df)

        print(f"✅ Built {len(df.columns)} total features")

        return df

    def _add_base_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add foundational technical indicators."""

        # Moving averages (multiple timeframes)
        for period in [5, 10, 20, 50, 100, 200]:
            df[f'sma_{period}'] = df['close'].rolling(period).mean()
            df[f'ema_{period}'] = df['close'].ewm(span=period).mean()

        # ATR (volatility measure)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['atr'] = true_range.rolling(14).mean()

        # RSI (momentum oscillator)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        ema_12 = df['close'].ewm(span=12).mean()
        ema_26 = df['close'].ewm(span=26).mean()
        df['macd'] = ema_12 - ema_26
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']

        # Bollinger Bands
        df['bb_middle'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (df['bb_std'] * 2)
        df['bb_lower'] = df['bb_middle'] - (df['bb_std'] * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
        df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

        # ADX (trend strength)
        high_diff = df['high'].diff()
        low_diff = -df['low'].diff()

        pos_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        neg_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

        tr_14 = true_range.rolling(14).sum()
        pos_di = 100 * (pos_dm.rolling(14).sum() / tr_14)
        neg_di = 100 * (neg_dm.rolling(14).sum() / tr_14)

        dx = 100 * np.abs(pos_di - neg_di) / (pos_di + neg_di)
        df['adx'] = dx.rolling(14).mean()
        df['plus_di'] = pos_di
        df['minus_di'] = neg_di

        # Stochastic Oscillator
        lowest_low = df['low'].rolling(14).min()
        highest_high = df['high'].rolling(14).max()
        df['stochastic_k'] = 100 * (df['close'] - lowest_low) / (highest_high - lowest_low)
        df['stochastic_d'] = df['stochastic_k'].rolling(3).mean()

        return df

    def _add_mean_reversion_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add mean reversion features.

        Forex pairs (especially EURUSD) tend to mean-revert more than commodities.
        """

        # Z-score from various moving averages
        for period in [20, 50, 100]:
            ma = df['close'].rolling(period).mean()
            std = df['close'].rolling(period).std()
            df[f'zscore_{period}'] = (df['close'] - ma) / std

        # Distance from moving averages (percentage)
        for period in [20, 50, 100, 200]:
            df[f'dist_from_sma_{period}'] = (df['close'] - df[f'sma_{period}']) / df[f'sma_{period}']
            df[f'dist_from_ema_{period}'] = (df['close'] - df[f'ema_{period}']) / df[f'ema_{period}']

        # RSI extremes (overbought/oversold)
        df['rsi_extreme_oversold'] = (df['rsi'] < 30).astype(int)
        df['rsi_extreme_overbought'] = (df['rsi'] > 70).astype(int)
        df['rsi_mean_reversion_signal'] = ((df['rsi'] < 30) | (df['rsi'] > 70)).astype(int)

        # Bollinger Band extremes
        df['bb_oversold'] = (df['bb_position'] < 0.1).astype(int)  # Near lower band
        df['bb_overbought'] = (df['bb_position'] > 0.9).astype(int)  # Near upper band

        # Stochastic extremes
        df['stoch_oversold'] = (df['stochastic_k'] < 20).astype(int)
        df['stoch_overbought'] = (df['stochastic_k'] > 80).astype(int)

        # Combined mean reversion signal
        df['mr_signal_strength'] = (
            df['rsi_extreme_oversold'] + df['rsi_extreme_overbought'] +
            df['bb_oversold'] + df['bb_overbought'] +
            df['stoch_oversold'] + df['stoch_overbought']
        )

        return df

    def _add_session_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add session-based features.

        Forex has distinct trading sessions with different characteristics:
        - Asian session (low volatility)
        - London session (high volatility, trend starts)
        - NY session (high volatility, trend confirmation)
        """

        # Extract time features
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['hour'] = df['timestamp'].dt.hour
        df['day_of_week'] = df['timestamp'].dt.dayofweek  # 0=Monday, 4=Friday

        # Session classification (assuming UTC timestamps)
        # Asian: 0-8 UTC, London: 8-16 UTC, NY: 13-21 UTC
        df['session_asian'] = ((df['hour'] >= 0) & (df['hour'] < 8)).astype(int)
        df['session_london'] = ((df['hour'] >= 8) & (df['hour'] < 16)).astype(int)
        df['session_ny'] = ((df['hour'] >= 13) & (df['hour'] < 21)).astype(int)
        df['session_overlap'] = ((df['hour'] >= 13) & (df['hour'] < 16)).astype(int)  # London+NY overlap

        # Session volatility (ATR during each session)
        df['session_volatility'] = df.groupby('hour')['atr'].transform('mean')

        # Hour-based volatility pattern
        df['hour_avg_volatility'] = df.groupby('hour')['atr'].transform('mean')
        df['is_high_volatility_hour'] = (df['hour_avg_volatility'] > df['atr'].median()).astype(int)

        # Day of week patterns
        df['is_monday'] = (df['day_of_week'] == 0).astype(int)
        df['is_friday'] = (df['day_of_week'] == 4).astype(int)

        return df

    def _add_support_resistance_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add support/resistance features.

        Forex respects S/R levels more than commodities,
        especially psychological round numbers.
        """

        # Round number proximity (EURUSD psychological levels)
        # Example: 1.1000, 1.1500, 1.2000, etc.
        df['round_level_0001'] = np.round(df['close'], 4)  # To 4 decimals
        df['round_level_001'] = np.round(df['close'], 3)   # To 3 decimals
        df['round_level_01'] = np.round(df['close'], 2)    # To 2 decimals

        # Distance to round levels (in pips)
        df['dist_to_round_0001'] = (df['close'] - df['round_level_0001']) * 10000
        df['dist_to_round_001'] = (df['close'] - df['round_level_001']) * 10000
        df['dist_to_round_01'] = (df['close'] - df['round_level_01']) * 10000

        # Near psychological level flag
        df['near_psych_level'] = (np.abs(df['dist_to_round_001']) < 10).astype(int)  # Within 10 pips

        # Pivot points (traditional)
        df['pivot'] = (df['high'].shift() + df['low'].shift() + df['close'].shift()) / 3
        df['r1'] = 2 * df['pivot'] - df['low'].shift()
        df['s1'] = 2 * df['pivot'] - df['high'].shift()
        df['r2'] = df['pivot'] + (df['high'].shift() - df['low'].shift())
        df['s2'] = df['pivot'] - (df['high'].shift() - df['low'].shift())

        # Distance to pivot levels
        df['dist_to_pivot'] = df['close'] - df['pivot']
        df['dist_to_r1'] = df['close'] - df['r1']
        df['dist_to_s1'] = df['close'] - df['s1']

        # Recent swing highs/lows
        window = 20
        df['swing_high'] = df['high'].rolling(window, center=True).max()
        df['swing_low'] = df['low'].rolling(window, center=True).min()
        df['dist_to_swing_high'] = df['close'] - df['swing_high']
        df['dist_to_swing_low'] = df['close'] - df['swing_low']

        # At support/resistance flag
        df['at_resistance'] = (df['dist_to_swing_high'].abs() < df['atr'] * 0.5).astype(int)
        df['at_support'] = (df['dist_to_swing_low'].abs() < df['atr'] * 0.5).astype(int)

        return df

    def _add_volatility_regime_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add volatility regime detection features.

        Helps identify when to use trend-following vs mean-reversion strategies.
        """

        # ATR percentile (is volatility high or low?)
        df['atr_percentile'] = df['atr'].rolling(100).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1]
        )

        # Volatility regime classification
        df['low_volatility'] = (df['atr_percentile'] < 0.3).astype(int)
        df['normal_volatility'] = ((df['atr_percentile'] >= 0.3) & (df['atr_percentile'] <= 0.7)).astype(int)
        df['high_volatility'] = (df['atr_percentile'] > 0.7).astype(int)

        # Bollinger Band width percentile
        df['bb_width_percentile'] = df['bb_width'].rolling(100).apply(
            lambda x: pd.Series(x).rank(pct=True).iloc[-1]
        )

        # Compression vs Expansion
        df['volatility_compression'] = (df['bb_width_percentile'] < 0.2).astype(int)
        df['volatility_expansion'] = (df['bb_width_percentile'] > 0.8).astype(int)

        # ATR trend (increasing or decreasing volatility)
        df['atr_trend'] = (df['atr'] > df['atr'].shift(5)).astype(int)

        return df

    def _add_trend_range_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add trend vs range detection features.

        Critical for forex: know when to trade trend vs when to fade extremes.
        """

        # ADX-based trend classification
        df['strong_trend'] = (df['adx'] > 25).astype(int)
        df['weak_trend'] = (df['adx'] < 20).astype(int)
        df['ranging'] = ((df['adx'] < 20) & (df['bb_width'] < df['bb_width'].median())).astype(int)

        # Trend direction
        df['uptrend'] = ((df['close'] > df['sma_50']) & (df['sma_50'] > df['sma_200'])).astype(int)
        df['downtrend'] = ((df['close'] < df['sma_50']) & (df['sma_50'] < df['sma_200'])).astype(int)

        # Price position relative to MAs
        df['above_all_ma'] = (
            (df['close'] > df['sma_5']) &
            (df['close'] > df['sma_20']) &
            (df['close'] > df['sma_50'])
        ).astype(int)

        df['below_all_ma'] = (
            (df['close'] < df['sma_5']) &
            (df['close'] < df['sma_20']) &
            (df['close'] < df['sma_50'])
        ).astype(int)

        # Donchian channel (for range detection)
        df['donchian_high'] = df['high'].rolling(20).max()
        df['donchian_low'] = df['low'].rolling(20).min()
        df['donchian_middle'] = (df['donchian_high'] + df['donchian_low']) / 2
        df['donchian_width'] = df['donchian_high'] - df['donchian_low']
        df['donchian_position'] = (df['close'] - df['donchian_low']) / df['donchian_width']

        # Range breakout detection
        df['donchian_breakout_up'] = (df['close'] > df['donchian_high'].shift()).astype(int)
        df['donchian_breakout_down'] = (df['close'] < df['donchian_low'].shift()).astype(int)

        return df

    def _add_momentum_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Add momentum features for trend trading.

        Used when market is trending (high ADX).
        """

        # Rate of change
        for period in [5, 10, 20]:
            df[f'roc_{period}'] = df['close'].pct_change(period) * 100

        # Momentum oscillators
        df['momentum_5'] = df['close'] - df['close'].shift(5)
        df['momentum_10'] = df['close'] - df['close'].shift(10)
        df['momentum_20'] = df['close'] - df['close'].shift(20)

        # Momentum acceleration (second derivative)
        df['momentum_acceleration'] = df['momentum_5'] - df['momentum_5'].shift(5)

        # MACD momentum
        df['macd_momentum'] = (df['macd_histogram'] > df['macd_histogram'].shift()).astype(int)
        df['macd_bullish'] = ((df['macd'] > df['macd_signal']) & (df['macd'] > 0)).astype(int)
        df['macd_bearish'] = ((df['macd'] < df['macd_signal']) & (df['macd'] < 0)).astype(int)

        # Price momentum relative to volatility (normalized)
        df['normalized_momentum'] = df['momentum_10'] / df['atr']

        return df

    def create_forex_target(
        self,
        df: pd.DataFrame,
        spread_pips: float = 1.5,
        profit_target_atr: float = 1.5,
        stop_loss_atr: float = 1.0,
        max_holding_hours: int = 24
    ) -> pd.DataFrame:
        """
        Create forex-specific trading targets.

        Args:
            df: DataFrame with features
            spread_pips: Bid-ask spread in pips
            profit_target_atr: TP as multiple of ATR
            stop_loss_atr: SL as multiple of ATR
            max_holding_hours: Maximum hours to hold position

        Returns:
            DataFrame with 'target' column added
        """

        print(f"Creating forex targets (TP: {profit_target_atr}x ATR, SL: {stop_loss_atr}x ATR, Max Hold: {max_holding_hours}h)...")

        df = df.copy()
        df['target'] = 0  # Default: HOLD

        # Convert pips to price
        spread = spread_pips / 10000

        for i in range(len(df) - max_holding_hours):
            if pd.isna(df['atr'].iloc[i]):
                continue

            entry_price = df['close'].iloc[i]
            atr = df['atr'].iloc[i]

            # BUY scenario
            buy_entry = entry_price + spread
            buy_tp = buy_entry + (atr * profit_target_atr)
            buy_sl = buy_entry - (atr * stop_loss_atr)

            # SELL scenario
            sell_entry = entry_price - spread
            sell_tp = sell_entry - (atr * profit_target_atr)
            sell_sl = sell_entry + (atr * stop_loss_atr)

            # Check future candles - track both BUY and SELL outcomes separately
            buy_outcome = None  # None, 'TP', or 'SL'
            sell_outcome = None
            buy_bars = 0
            sell_bars = 0

            for j in range(i + 1, min(i + 1 + max_holding_hours, len(df))):
                future_high = df['high'].iloc[j]
                future_low = df['low'].iloc[j]

                # Check BUY outcome (if not already determined)
                if buy_outcome is None:
                    if future_high >= buy_tp:
                        buy_outcome = 'TP'
                        buy_bars = j - i
                    elif future_low <= buy_sl:
                        buy_outcome = 'SL'

                # Check SELL outcome (if not already determined)
                if sell_outcome is None:
                    if future_low <= sell_tp:
                        sell_outcome = 'TP'
                        sell_bars = j - i
                    elif future_high >= sell_sl:
                        sell_outcome = 'SL'

                # If both outcomes determined, we can stop checking
                if buy_outcome is not None and sell_outcome is not None:
                    break

            # Assign target based on outcomes
            # Priority: If both hit TP, choose the one that hits first
            if buy_outcome == 'TP' and sell_outcome == 'TP':
                # Both would profit - choose faster one
                if buy_bars <= sell_bars:
                    df.loc[df.index[i], 'target'] = 2  # BUY
                else:
                    df.loc[df.index[i], 'target'] = 1  # SELL
            elif buy_outcome == 'TP':
                df.loc[df.index[i], 'target'] = 2  # BUY
            elif sell_outcome == 'TP':
                df.loc[df.index[i], 'target'] = 1  # SELL
            # else: stays HOLD (both hit SL or neither hit TP)

        target_dist = df['target'].value_counts(normalize=True)
        print(f"Target distribution: HOLD {target_dist.get(0, 0):.1%}, SELL {target_dist.get(1, 0):.1%}, BUY {target_dist.get(2, 0):.1%}")

        return df


if __name__ == '__main__':
    # Test the feature engineer
    print("\nTesting Forex Feature Engineer...")

    # Load recent EURUSD data
    df = pd.read_csv('ohlcv/eurusd/eurusd_1h_recent.csv')
    print(f"Loaded {len(df):,} candles")

    # Build features
    engineer = ForexFeatureEngineer()
    df_featured = engineer.build_forex_features(df)

    print(f"\nFeatures created: {len(df_featured.columns)}")
    print("\nFeature columns:")
    for col in sorted(df_featured.columns):
        print(f"  - {col}")

    # Create targets
    df_with_target = engineer.create_forex_target(
        df_featured,
        spread_pips=1.5,
        profit_target_atr=1.5,
        stop_loss_atr=1.0,
        max_holding_hours=24
    )

    print("\n✅ Forex Feature Engineer test complete")
