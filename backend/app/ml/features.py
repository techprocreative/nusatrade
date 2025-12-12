"""Feature engineering for ML models with comprehensive technical indicators."""

from typing import Dict, List, Optional

import pandas as pd
import numpy as np


class FeatureEngineer:
    """Builds features from OHLCV data for ML models."""

    def __init__(self, include_all: bool = True):
        self.include_all = include_all

    def build_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Build all features from OHLCV data."""
        df = df.copy()

        # Trend Indicators
        df = self._add_moving_averages(df)
        df = self._add_macd(df)
        df = self._add_adx(df)

        # Momentum Indicators
        df = self._add_rsi(df)
        df = self._add_stochastic(df)
        df = self._add_momentum(df)
        df = self._add_cci(df)

        # Volatility Indicators
        df = self._add_bollinger_bands(df)
        df = self._add_atr(df)

        # Volume Indicators
        if "volume" in df.columns:
            df = self._add_volume_features(df)

        # Price Action
        df = self._add_price_features(df)
        df = self._add_candlestick_patterns(df)

        # Time features
        df = self._add_time_features(df)

        # Clean up
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.bfill().ffill()

        return df

    def _add_moving_averages(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add various moving averages."""
        periods = [5, 10, 20, 50, 100, 200]

        for period in periods:
            df[f"sma_{period}"] = df["close"].rolling(window=period).mean()
            df[f"ema_{period}"] = df["close"].ewm(span=period, adjust=False).mean()

        # MA crossover signals
        df["sma_cross_10_20"] = (df["sma_10"] > df["sma_20"]).astype(int)
        df["sma_cross_20_50"] = (df["sma_20"] > df["sma_50"]).astype(int)
        df["ema_cross_10_20"] = (df["ema_10"] > df["ema_20"]).astype(int)

        # Price vs MA
        df["price_vs_sma_20"] = (df["close"] - df["sma_20"]) / df["sma_20"] * 100
        df["price_vs_sma_50"] = (df["close"] - df["sma_50"]) / df["sma_50"] * 100

        return df

    def _add_rsi(self, df: pd.DataFrame, periods: List[int] = [14, 7, 21]) -> pd.DataFrame:
        """Add RSI indicator."""
        for period in periods:
            delta = df["close"].diff()
            gain = delta.where(delta > 0, 0).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

            rs = gain / loss
            df[f"rsi_{period}"] = 100 - (100 / (1 + rs))

        # RSI zones
        df["rsi_oversold"] = (df["rsi_14"] < 30).astype(int)
        df["rsi_overbought"] = (df["rsi_14"] > 70).astype(int)

        return df

    def _add_macd(
        self,
        df: pd.DataFrame,
        fast: int = 12,
        slow: int = 26,
        signal: int = 9,
    ) -> pd.DataFrame:
        """Add MACD indicator."""
        ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df["close"].ewm(span=slow, adjust=False).mean()

        df["macd"] = ema_fast - ema_slow
        df["macd_signal"] = df["macd"].ewm(span=signal, adjust=False).mean()
        df["macd_hist"] = df["macd"] - df["macd_signal"]

        # MACD crossover
        df["macd_cross"] = (df["macd"] > df["macd_signal"]).astype(int)
        df["macd_hist_positive"] = (df["macd_hist"] > 0).astype(int)

        return df

    def _add_bollinger_bands(
        self,
        df: pd.DataFrame,
        period: int = 20,
        std_dev: float = 2.0,
    ) -> pd.DataFrame:
        """Add Bollinger Bands."""
        sma = df["close"].rolling(window=period).mean()
        std = df["close"].rolling(window=period).std()

        df["bb_upper"] = sma + (std_dev * std)
        df["bb_middle"] = sma
        df["bb_lower"] = sma - (std_dev * std)

        df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / df["bb_middle"] * 100
        df["bb_percent"] = (df["close"] - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"])

        return df

    def _add_atr(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Add Average True Range."""
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()

        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df["atr"] = true_range.rolling(window=period).mean()
        df["atr_percent"] = df["atr"] / df["close"] * 100

        return df

    def _add_adx(self, df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
        """Add Average Directional Index."""
        plus_dm = df["high"].diff()
        minus_dm = df["low"].diff().apply(lambda x: -x)

        plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0)
        minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0)

        tr = self._true_range(df)

        plus_di = 100 * (plus_dm.ewm(span=period).mean() / tr.ewm(span=period).mean())
        minus_di = 100 * (minus_dm.ewm(span=period).mean() / tr.ewm(span=period).mean())

        dx = (abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
        df["adx"] = dx.ewm(span=period).mean()
        df["plus_di"] = plus_di
        df["minus_di"] = minus_di

        # Trend strength
        df["strong_trend"] = (df["adx"] > 25).astype(int)

        return df

    def _add_stochastic(
        self,
        df: pd.DataFrame,
        k_period: int = 14,
        d_period: int = 3,
    ) -> pd.DataFrame:
        """Add Stochastic Oscillator."""
        lowest_low = df["low"].rolling(window=k_period).min()
        highest_high = df["high"].rolling(window=k_period).max()

        df["stoch_k"] = 100 * (df["close"] - lowest_low) / (highest_high - lowest_low)
        df["stoch_d"] = df["stoch_k"].rolling(window=d_period).mean()

        df["stoch_oversold"] = (df["stoch_k"] < 20).astype(int)
        df["stoch_overbought"] = (df["stoch_k"] > 80).astype(int)

        return df

    def _add_momentum(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add momentum indicators."""
        df["momentum_10"] = df["close"] - df["close"].shift(10)
        df["roc_10"] = (df["close"] - df["close"].shift(10)) / df["close"].shift(10) * 100
        df["roc_20"] = (df["close"] - df["close"].shift(20)) / df["close"].shift(20) * 100

        return df

    def _add_cci(self, df: pd.DataFrame, period: int = 20) -> pd.DataFrame:
        """
        Add Commodity Channel Index (CCI).
        
        CCI = (Typical Price - SMA of TP) / (0.015 * Mean Deviation)
        Typical Price = (High + Low + Close) / 3
        
        Interpretation:
        - CCI > 100: Overbought (potential sell signal)
        - CCI < -100: Oversold (potential buy signal)
        - CCI crossing above 0: Bullish momentum
        - CCI crossing below 0: Bearish momentum
        """
        # Calculate Typical Price
        tp = (df["high"] + df["low"] + df["close"]) / 3
        
        # Calculate SMA of Typical Price
        sma_tp = tp.rolling(window=period).mean()
        
        # Calculate Mean Deviation
        mean_deviation = tp.rolling(window=period).apply(
            lambda x: np.abs(x - x.mean()).mean(), raw=True
        )
        
        # Calculate CCI
        df["cci"] = (tp - sma_tp) / (0.015 * mean_deviation)
        df[f"cci_{period}"] = df["cci"]
        
        # CCI zones for quick reference
        df["cci_overbought"] = (df["cci"] > 100).astype(int)
        df["cci_oversold"] = (df["cci"] < -100).astype(int)
        
        return df

    def _add_volume_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add volume-based features."""
        df["volume_sma_20"] = df["volume"].rolling(window=20).mean()
        df["volume_ratio"] = df["volume"] / df["volume_sma_20"]

        # On-Balance Volume
        df["obv"] = (np.sign(df["close"].diff()) * df["volume"]).cumsum()

        return df

    def _add_price_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add price action features."""
        df["returns"] = df["close"].pct_change()
        df["log_returns"] = np.log(df["close"] / df["close"].shift(1))

        df["high_low_range"] = df["high"] - df["low"]
        df["body_size"] = abs(df["close"] - df["open"])
        df["upper_wick"] = df["high"] - df[["close", "open"]].max(axis=1)
        df["lower_wick"] = df[["close", "open"]].min(axis=1) - df["low"]

        # Volatility
        df["volatility_20"] = df["returns"].rolling(window=20).std() * np.sqrt(252)

        return df

    def _add_candlestick_patterns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add candlestick pattern detection."""
        body = df["close"] - df["open"]
        body_abs = abs(body)
        range_hl = df["high"] - df["low"]

        # Doji
        df["doji"] = (body_abs < range_hl * 0.1).astype(int)

        # Hammer (long lower wick, small body at top)
        df["hammer"] = (
            (df["lower_wick"] > body_abs * 2) &
            (df["upper_wick"] < body_abs * 0.5) &
            (body > 0)
        ).astype(int)

        # Shooting Star (long upper wick, small body at bottom)
        df["shooting_star"] = (
            (df["upper_wick"] > body_abs * 2) &
            (df["lower_wick"] < body_abs * 0.5) &
            (body < 0)
        ).astype(int)

        # Engulfing
        prev_body = body.shift(1)
        df["bullish_engulfing"] = (
            (prev_body < 0) &
            (body > 0) &
            (body_abs > abs(prev_body))
        ).astype(int)

        df["bearish_engulfing"] = (
            (prev_body > 0) &
            (body < 0) &
            (body_abs > abs(prev_body))
        ).astype(int)

        return df

    def _add_time_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add time-based features."""
        if "timestamp" in df.columns:
            ts = pd.to_datetime(df["timestamp"])
            df["hour"] = ts.dt.hour
            df["day_of_week"] = ts.dt.dayofweek
            df["is_asian"] = ((ts.dt.hour >= 0) & (ts.dt.hour < 8)).astype(int)
            df["is_london"] = ((ts.dt.hour >= 8) & (ts.dt.hour < 16)).astype(int)
            df["is_ny"] = ((ts.dt.hour >= 13) & (ts.dt.hour < 22)).astype(int)

        return df

    def _true_range(self, df: pd.DataFrame) -> pd.Series:
        """Calculate True Range."""
        high_low = df["high"] - df["low"]
        high_close = (df["high"] - df["close"].shift()).abs()
        low_close = (df["low"] - df["close"].shift()).abs()
        return pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)


# Convenience function for backward compatibility
def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build all features from OHLCV data."""
    engineer = FeatureEngineer()
    return engineer.build_features(df)
