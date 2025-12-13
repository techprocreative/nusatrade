"""
Crypto-Optimized Feature Engineering for Bitcoin Trading

Key Differences from Traditional Assets (XAUUSD):
1. 24/7 market (no session gaps)
2. Extreme volatility (10x more than forex)
3. Momentum-driven (trend-following > mean-reversion)
4. Sentiment-driven (news, social media)
5. Volume spikes indicate whale movements
6. Support/resistance less reliable, momentum more important
"""

import pandas as pd
import numpy as np


class CryptoFeatureEngineer:
    """
    Crypto-specific feature engineering for Bitcoin.

    Focuses on:
    - Momentum and trend strength
    - Volume analysis (whale detection)
    - Volatility regimes
    - Multi-timeframe confirmation
    """

    def __init__(self):
        pass

    def add_crypto_momentum_features(self, df):
        """Add momentum features critical for crypto."""

        # Rate of Change (strong momentum indicator for crypto)
        df['roc_5'] = df['close'].pct_change(5) * 100
        df['roc_10'] = df['close'].pct_change(10) * 100
        df['roc_20'] = df['close'].pct_change(20) * 100

        # Momentum strength
        df['momentum_5'] = df['close'] - df['close'].shift(5)
        df['momentum_10'] = df['close'] - df['close'].shift(10)

        # Acceleration (rate of change of momentum)
        df['momentum_acceleration'] = df['momentum_5'] - df['momentum_5'].shift(5)

        return df

    def add_crypto_volume_features(self, df):
        """Volume is critical in crypto - whale movements."""

        # Volume surge detection
        df['volume_ma_20'] = df['volume'].rolling(20).mean()
        df['volume_surge'] = (df['volume'] / df['volume_ma_20']).fillna(1)
        df['is_volume_surge'] = (df['volume_surge'] > 2.0).astype(int)

        # Volume trend
        df['volume_trend'] = df['volume'].rolling(10).mean() / df['volume'].rolling(30).mean()

        # Volume-weighted price movement
        df['vwap'] = (df['close'] * df['volume']).rolling(20).sum() / df['volume'].rolling(20).sum()
        df['price_vs_vwap'] = (df['close'] - df['vwap']) / df['vwap'] * 100

        return df

    def add_crypto_volatility_features(self, df):
        """Crypto volatility is extreme - need to identify regimes."""

        # Historical volatility (% moves)
        df['volatility_5'] = df['close'].pct_change().rolling(5).std() * 100
        df['volatility_20'] = df['close'].pct_change().rolling(20).std() * 100

        # Volatility regime (avoid extreme volatility)
        vol_median = df['volatility_20'].median()
        df['normal_volatility'] = (
            (df['volatility_20'] > vol_median * 0.5) &
            (df['volatility_20'] < vol_median * 2.0)
        ).astype(int)

        # Volatility expansion (trend acceleration)
        df['volatility_expanding'] = (df['volatility_5'] > df['volatility_20']).astype(int)

        return df

    def add_crypto_trend_features(self, df):
        """Trend-following is king in crypto."""

        # Multiple EMA for trend
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        df['ema_50'] = df['close'].ewm(span=50).mean()
        df['ema_100'] = df['close'].ewm(span=100).mean()
        df['ema_200'] = df['close'].ewm(span=200).mean()

        # Trend alignment (all EMAs aligned = strong trend)
        df['bullish_alignment'] = (
            (df['close'] > df['ema_12']) &
            (df['ema_12'] > df['ema_26']) &
            (df['ema_26'] > df['ema_50']) &
            (df['ema_50'] > df['ema_200'])
        ).astype(int)

        df['bearish_alignment'] = (
            (df['close'] < df['ema_12']) &
            (df['ema_12'] < df['ema_26']) &
            (df['ema_26'] < df['ema_50']) &
            (df['ema_50'] < df['ema_200'])
        ).astype(int)

        # ADX for trend strength
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())

        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(14).mean()

        df['atr'] = atr

        # Directional movement
        plus_dm = df['high'].diff()
        minus_dm = -df['low'].diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        plus_di = 100 * (plus_dm.rolling(14).mean() / atr)
        minus_di = 100 * (minus_dm.rolling(14).mean() / atr)

        dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
        df['adx'] = dx.rolling(14).mean()

        # Strong trend if ADX > 25
        df['strong_trend'] = (df['adx'] > 25).astype(int)
        df['very_strong_trend'] = (df['adx'] > 40).astype(int)

        return df

    def add_crypto_breakout_features(self, df):
        """Crypto loves breakouts - identify them."""

        # Bollinger Bands (wider for crypto)
        df['bb_middle'] = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_middle'] + (bb_std * 2.5)  # Wider bands
        df['bb_lower'] = df['bb_middle'] - (bb_std * 2.5)

        # Breakout detection
        df['breakout_up'] = (df['close'] > df['bb_upper']).astype(int)
        df['breakout_down'] = (df['close'] < df['bb_lower']).astype(int)

        # Price position in range
        df['bb_width'] = df['bb_upper'] - df['bb_lower']
        df['bb_position'] = (df['close'] - df['bb_lower']) / df['bb_width']

        # Consolidation detection (tight bands = potential breakout)
        df['consolidation'] = (df['bb_width'] < df['bb_width'].rolling(50).mean() * 0.7).astype(int)

        return df

    def build_crypto_features(self, df):
        """Build all crypto-optimized features."""

        df = df.copy()

        # Basic features (keep from original)
        df['returns'] = df['close'].pct_change()

        # Crypto-specific features
        df = self.add_crypto_momentum_features(df)
        df = self.add_crypto_volume_features(df)
        df = self.add_crypto_volatility_features(df)
        df = self.add_crypto_trend_features(df)
        df = self.add_crypto_breakout_features(df)

        # MACD (still useful for crypto)
        df['ema_12_macd'] = df['close'].ewm(span=12).mean()
        df['ema_26_macd'] = df['close'].ewm(span=26).mean()
        df['macd'] = df['ema_12_macd'] - df['ema_26_macd']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        # RSI (overbought/oversold less reliable in crypto, but momentum is)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        df['rsi_momentum'] = df['rsi'].diff(5)  # RSI trend matters more

        return df

    def create_crypto_target(self, df, spread_pips=10.0,
                            profit_target_atr=2.5, stop_loss_atr=1.5,
                            max_holding_hours=16):
        """
        Create target variable optimized for crypto.

        Crypto-specific adjustments:
        - Larger TP/SL ratios (more volatility)
        - Longer holding period (bigger moves take time)
        - Focus on trend continuation
        """

        df = df.copy()
        df['target'] = 0  # HOLD

        spread_cost_pct = spread_pips / 10000

        for i in range(len(df) - max_holding_hours):
            atr = df.iloc[i]['atr']

            if pd.isna(atr):
                continue

            entry_price = df.iloc[i]['close']

            # Define TP/SL in dollars
            profit_target = atr * profit_target_atr
            stop_loss = atr * stop_loss_atr

            # Look ahead for TP/SL hits
            future_bars = df.iloc[i+1:i+1+max_holding_hours]

            # Check BUY
            buy_tp = entry_price * (1 + spread_cost_pct) + profit_target
            buy_sl = entry_price * (1 + spread_cost_pct) - stop_loss

            for j, future_row in future_bars.iterrows():
                if future_row['high'] >= buy_tp:
                    df.loc[df.index[i], 'target'] = 2  # BUY
                    break
                elif future_row['low'] <= buy_sl:
                    break

            # Check SELL
            sell_tp = entry_price * (1 - spread_cost_pct) - profit_target
            sell_sl = entry_price * (1 - spread_cost_pct) + stop_loss

            for j, future_row in future_bars.iterrows():
                if future_row['low'] <= sell_tp:
                    df.loc[df.index[i], 'target'] = 1  # SELL
                    break
                elif future_row['high'] >= sell_sl:
                    break

        return df


if __name__ == '__main__':
    # Test crypto features
    import sys
    sys.path.insert(0, '.')

    df = pd.read_csv('ohlcv/btc/btcusd_1h_clean.csv')
    print(f"Loaded {len(df)} BTC candles")

    engineer = CryptoFeatureEngineer()
    df_featured = engineer.build_crypto_features(df)

    print(f"\nCrypto features built: {len(df_featured.columns)} columns")
    print("\nNew crypto-specific features:")
    crypto_features = [
        'roc_5', 'roc_10', 'roc_20', 'momentum_acceleration',
        'volume_surge', 'is_volume_surge', 'volatility_expanding',
        'bullish_alignment', 'bearish_alignment', 'very_strong_trend',
        'breakout_up', 'breakout_down', 'consolidation'
    ]

    for feat in crypto_features:
        if feat in df_featured.columns:
            print(f"  ✓ {feat}")

    print("\n✅ Crypto feature engineering complete!")
