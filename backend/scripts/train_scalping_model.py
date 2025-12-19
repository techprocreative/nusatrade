#!/usr/bin/env python3
"""
Train Scalping Model for XAUUSD using M5/M15 data.

This script trains an XGBoost model optimized for scalping strategies
with shorter timeframes and tighter SL/TP levels.
"""

import os
import sys
import pickle
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, classification_report
import xgboost as xgb

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


class ScalpingFeatureEngineer:
    """Feature engineering optimized for scalping strategies."""
    
    def __init__(self):
        self.feature_columns = []
    
    def create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create scalping-specific features."""
        df = df.copy()
        
        # Ensure numeric columns
        for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Price-based features
        df['returns_1'] = df['Close'].pct_change(1)
        df['returns_3'] = df['Close'].pct_change(3)
        df['returns_5'] = df['Close'].pct_change(5)
        df['returns_10'] = df['Close'].pct_change(10)
        
        # Volatility features (shorter windows for scalping)
        df['volatility_5'] = df['returns_1'].rolling(5).std()
        df['volatility_10'] = df['returns_1'].rolling(10).std()
        df['volatility_20'] = df['returns_1'].rolling(20).std()
        
        # ATR for scalping (shorter period)
        df['tr'] = np.maximum(
            df['High'] - df['Low'],
            np.maximum(
                abs(df['High'] - df['Close'].shift(1)),
                abs(df['Low'] - df['Close'].shift(1))
            )
        )
        df['atr_5'] = df['tr'].rolling(5).mean()
        df['atr_10'] = df['tr'].rolling(10).mean()
        df['atr_14'] = df['tr'].rolling(14).mean()
        
        # Price position within range
        df['high_low_range'] = df['High'] - df['Low']
        df['close_position'] = (df['Close'] - df['Low']) / (df['High'] - df['Low'] + 1e-8)
        
        # Moving averages (shorter periods for scalping)
        df['sma_5'] = df['Close'].rolling(5).mean()
        df['sma_10'] = df['Close'].rolling(10).mean()
        df['sma_20'] = df['Close'].rolling(20).mean()
        df['ema_5'] = df['Close'].ewm(span=5).mean()
        df['ema_10'] = df['Close'].ewm(span=10).mean()
        df['ema_20'] = df['Close'].ewm(span=20).mean()
        
        # MA crossovers
        df['ema_5_10_diff'] = (df['ema_5'] - df['ema_10']) / df['Close']
        df['ema_10_20_diff'] = (df['ema_10'] - df['ema_20']) / df['Close']
        df['price_vs_ema_10'] = (df['Close'] - df['ema_10']) / df['Close']
        
        # RSI (7 period for scalping)
        delta = df['Close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.rolling(7).mean()
        avg_loss = loss.rolling(7).mean()
        rs = avg_gain / (avg_loss + 1e-8)
        df['rsi_7'] = 100 - (100 / (1 + rs))
        
        # RSI 14 for confirmation
        avg_gain_14 = gain.rolling(14).mean()
        avg_loss_14 = loss.rolling(14).mean()
        rs_14 = avg_gain_14 / (avg_loss_14 + 1e-8)
        df['rsi_14'] = 100 - (100 / (1 + rs_14))
        
        # Stochastic
        lowest_low = df['Low'].rolling(14).min()
        highest_high = df['High'].rolling(14).max()
        df['stoch_k'] = 100 * (df['Close'] - lowest_low) / (highest_high - lowest_low + 1e-8)
        df['stoch_d'] = df['stoch_k'].rolling(3).mean()
        
        # MACD (faster settings for scalping)
        ema_6 = df['Close'].ewm(span=6).mean()
        ema_13 = df['Close'].ewm(span=13).mean()
        df['macd'] = ema_6 - ema_13
        df['macd_signal'] = df['macd'].ewm(span=5).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        df['macd_normalized'] = df['macd'] / df['Close']
        
        # Bollinger Bands (shorter period)
        bb_sma = df['Close'].rolling(10).mean()
        bb_std = df['Close'].rolling(10).std()
        df['bb_upper'] = bb_sma + (2 * bb_std)
        df['bb_lower'] = bb_sma - (2 * bb_std)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / bb_sma
        df['bb_position'] = (df['Close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 1e-8)
        
        # Volume features
        if 'Volume' in df.columns and df['Volume'].sum() > 0:
            df['volume_sma_5'] = df['Volume'].rolling(5).mean()
            df['volume_sma_10'] = df['Volume'].rolling(10).mean()
            df['volume_ratio'] = df['Volume'] / (df['volume_sma_10'] + 1)
            df['volume_spike'] = (df['Volume'] > df['Volume'].rolling(20).mean() * 1.5).astype(int)
        else:
            df['volume_sma_5'] = 0
            df['volume_sma_10'] = 0
            df['volume_ratio'] = 1
            df['volume_spike'] = 0
        
        # Momentum
        df['momentum_3'] = df['Close'] - df['Close'].shift(3)
        df['momentum_5'] = df['Close'] - df['Close'].shift(5)
        df['momentum_10'] = df['Close'] - df['Close'].shift(10)
        
        # Rate of Change
        df['roc_3'] = (df['Close'] - df['Close'].shift(3)) / (df['Close'].shift(3) + 1e-8) * 100
        df['roc_5'] = (df['Close'] - df['Close'].shift(5)) / (df['Close'].shift(5) + 1e-8) * 100
        
        # Candle patterns
        df['body_size'] = abs(df['Close'] - df['Open']) / (df['High'] - df['Low'] + 1e-8)
        df['upper_shadow'] = (df['High'] - df[['Open', 'Close']].max(axis=1)) / (df['High'] - df['Low'] + 1e-8)
        df['lower_shadow'] = (df[['Open', 'Close']].min(axis=1) - df['Low']) / (df['High'] - df['Low'] + 1e-8)
        df['is_bullish'] = (df['Close'] > df['Open']).astype(int)
        
        # Consecutive candles
        df['bullish_streak'] = df['is_bullish'].groupby((df['is_bullish'] != df['is_bullish'].shift()).cumsum()).cumcount() + 1
        df['bullish_streak'] = df['bullish_streak'] * df['is_bullish']
        df['bearish_streak'] = (~df['is_bullish'].astype(bool)).astype(int).groupby((df['is_bullish'] != df['is_bullish'].shift()).cumsum()).cumcount() + 1
        df['bearish_streak'] = df['bearish_streak'] * (1 - df['is_bullish'])
        
        # Time-based features (if datetime available)
        if 'Date' in df.columns or 'timestamp' in df.columns:
            dt_col = 'Date' if 'Date' in df.columns else 'timestamp'
            try:
                df['datetime'] = pd.to_datetime(df[dt_col])
                df['hour'] = df['datetime'].dt.hour
                df['day_of_week'] = df['datetime'].dt.dayofweek
                
                # Trading sessions (UTC)
                df['is_asian'] = ((df['hour'] >= 0) & (df['hour'] < 8)).astype(int)
                df['is_london'] = ((df['hour'] >= 8) & (df['hour'] < 16)).astype(int)
                df['is_ny'] = ((df['hour'] >= 13) & (df['hour'] < 21)).astype(int)
                df['is_overlap'] = ((df['hour'] >= 13) & (df['hour'] < 16)).astype(int)  # London-NY overlap
            except:
                df['hour'] = 12
                df['day_of_week'] = 2
                df['is_asian'] = 0
                df['is_london'] = 1
                df['is_ny'] = 0
                df['is_overlap'] = 0
        
        # Define feature columns
        self.feature_columns = [
            'returns_1', 'returns_3', 'returns_5', 'returns_10',
            'volatility_5', 'volatility_10', 'volatility_20',
            'atr_5', 'atr_10', 'atr_14',
            'close_position', 'high_low_range',
            'ema_5_10_diff', 'ema_10_20_diff', 'price_vs_ema_10',
            'rsi_7', 'rsi_14',
            'stoch_k', 'stoch_d',
            'macd_normalized', 'macd_hist',
            'bb_width', 'bb_position',
            'volume_ratio', 'volume_spike',
            'momentum_3', 'momentum_5',
            'roc_3', 'roc_5',
            'body_size', 'upper_shadow', 'lower_shadow', 'is_bullish',
            'bullish_streak', 'bearish_streak',
            'hour', 'day_of_week',
            'is_london', 'is_ny', 'is_overlap',
        ]
        
        return df
    
    def create_target(
        self, 
        df: pd.DataFrame, 
        lookahead: int = 3, 
        threshold_pips: float = 5.0
    ) -> pd.DataFrame:
        """
        Create target for scalping - shorter lookahead and pip threshold.
        
        Target classes:
        - 0: HOLD (price moves less than threshold)
        - 1: BUY (price goes up by threshold)
        - 2: SELL (price goes down by threshold)
        """
        df = df.copy()
        
        # For XAUUSD, 1 pip = 0.1 (gold is quoted in dollars)
        pip_value = 0.1
        threshold = threshold_pips * pip_value
        
        # Future price change
        df['future_high'] = df['High'].shift(-lookahead).rolling(lookahead).max()
        df['future_low'] = df['Low'].shift(-lookahead).rolling(lookahead).min()
        df['future_close'] = df['Close'].shift(-lookahead)
        
        # Determine target based on which threshold is hit first
        high_change = df['future_high'] - df['Close']
        low_change = df['Close'] - df['future_low']
        
        # Default to HOLD
        df['target'] = 0
        
        # BUY if price goes up by threshold and the up move is bigger
        df.loc[(high_change >= threshold) & (high_change > low_change), 'target'] = 1
        
        # SELL if price goes down by threshold and the down move is bigger
        df.loc[(low_change >= threshold) & (low_change >= high_change), 'target'] = 2
        
        return df


def load_and_preprocess_data(filepath: str, max_rows: int = None) -> pd.DataFrame:
    """Load and preprocess OHLCV data from CSV."""
    print(f"📊 Loading data from {filepath}...")
    
    # Read CSV with semicolon delimiter
    df = pd.read_csv(filepath, sep=';', nrows=max_rows)
    print(f"   Loaded {len(df):,} rows")
    
    # Print columns for debugging
    print(f"   Columns: {list(df.columns)}")
    
    # Rename columns if needed
    if 'Date' in df.columns:
        df['timestamp'] = pd.to_datetime(df['Date'])
    
    # Drop rows with missing values
    df = df.dropna()
    print(f"   After dropna: {len(df):,} rows")
    
    return df


def train_scalping_model(
    data_path: str,
    timeframe: str = "M5",
    lookahead: int = 3,
    threshold_pips: float = 5.0,
    test_size: float = 0.2,
    max_rows: int = None,
):
    """Train scalping model for XAUUSD."""
    
    print("=" * 60)
    print(f"🚀 XAUUSD Scalping Model Training ({timeframe})")
    print("=" * 60)
    
    # Load data
    df = load_and_preprocess_data(data_path, max_rows)
    
    # Use only recent data (last 2 years for better relevance)
    if len(df) > 500000:
        print(f"📅 Using last 500,000 rows for training...")
        df = df.tail(500000).reset_index(drop=True)
    
    # Feature engineering
    print("\n🔧 Creating features...")
    fe = ScalpingFeatureEngineer()
    df = fe.create_features(df)
    df = fe.create_target(df, lookahead=lookahead, threshold_pips=threshold_pips)
    
    # Drop NaN rows
    df = df.dropna()
    print(f"   Final dataset: {len(df):,} rows")
    
    # Prepare features
    feature_cols = [c for c in fe.feature_columns if c in df.columns]
    print(f"   Using {len(feature_cols)} features")
    
    X = df[feature_cols].values
    y = df['target'].values
    
    # Print class distribution
    unique, counts = np.unique(y, return_counts=True)
    print(f"\n📊 Target distribution:")
    for u, c in zip(unique, counts):
        label = ['HOLD', 'BUY', 'SELL'][u]
        print(f"   {label}: {c:,} ({c/len(y)*100:.1f}%)")
    
    # Split data (time-series aware - don't shuffle!)
    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    print(f"\n📈 Train size: {len(X_train):,}, Test size: {len(X_test):,}")
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    # Train XGBoost model
    print("\n🎯 Training XGBoost model...")
    
    # Calculate class weights for imbalanced data
    class_counts = np.bincount(y_train, minlength=3)
    total = len(y_train)
    class_weights = {i: total / (3 * c) if c > 0 else 1.0 for i, c in enumerate(class_counts)}
    sample_weights = np.array([class_weights[yi] for yi in y_train])
    
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        gamma=0.1,
        reg_alpha=0.1,
        reg_lambda=1.0,
        objective='multi:softprob',
        num_class=3,
        random_state=42,
        n_jobs=-1,
        verbosity=1,
    )
    
    model.fit(
        X_train_scaled, 
        y_train,
        sample_weight=sample_weights,
        eval_set=[(X_test_scaled, y_test)],
        verbose=True,
    )
    
    # Evaluate
    print("\n📊 Evaluation:")
    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)
    
    accuracy = accuracy_score(y_test, y_pred)
    print(f"   Accuracy: {accuracy:.4f}")
    
    print(f"\n   Classification Report:")
    target_names = ['HOLD', 'BUY', 'SELL']
    print(classification_report(y_test, y_pred, target_names=target_names))
    
    # Feature importance
    print("\n🔍 Top 10 Feature Importances:")
    importance = model.feature_importances_
    indices = np.argsort(importance)[-10:][::-1]
    for i in indices:
        print(f"   {feature_cols[i]}: {importance[i]:.4f}")
    
    # Calculate trading metrics (only for BUY/SELL predictions)
    buy_sell_mask = y_pred != 0
    trade_predictions = y_pred[buy_sell_mask]
    trade_actual = y_test[buy_sell_mask]
    
    if len(trade_predictions) > 0:
        # Win rate = predictions that matched actual direction
        correct_trades = (trade_predictions == trade_actual).sum()
        total_trades = len(trade_predictions)
        win_rate = correct_trades / total_trades * 100
        
        # For BUY predictions
        buy_preds = y_pred == 1
        buy_correct = ((y_pred == 1) & (y_test == 1)).sum()
        buy_wrong = ((y_pred == 1) & (y_test != 1)).sum()
        
        # For SELL predictions  
        sell_preds = y_pred == 2
        sell_correct = ((y_pred == 2) & (y_test == 2)).sum()
        sell_wrong = ((y_pred == 2) & (y_test != 2)).sum()
        
        print(f"\n💰 Trading Metrics:")
        print(f"   Total trade signals: {total_trades:,}")
        print(f"   Win Rate (direction): {win_rate:.1f}%")
        print(f"   BUY signals: {buy_preds.sum()} (correct: {buy_correct}, wrong: {buy_wrong})")
        print(f"   SELL signals: {sell_preds.sum()} (correct: {sell_correct}, wrong: {sell_wrong})")
    
    # Save model
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_dir = backend_dir / "models"
    model_dir.mkdir(exist_ok=True)
    
    model_filename = f"model_scalping_xauusd_{timeframe}_{timestamp}.pkl"
    model_path = model_dir / model_filename
    
    model_data = {
        'model': model,
        'scaler': scaler,
        'feature_columns': feature_cols,
        'timeframe': timeframe,
        'lookahead': lookahead,
        'threshold_pips': threshold_pips,
        'accuracy': accuracy,
        'win_rate': win_rate if 'win_rate' in dir() else None,
        'trained_at': datetime.now().isoformat(),
        'model_type': 'xgboost_scalping',
    }
    
    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)
    
    print(f"\n✅ Model saved to: {model_path}")
    print(f"   Model ID: {model_filename}")
    
    return str(model_path), model_data


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Train XAUUSD Scalping Model')
    parser.add_argument('--timeframe', type=str, default='M5', choices=['M5', 'M15'],
                        help='Timeframe to use (M5 or M15)')
    parser.add_argument('--lookahead', type=int, default=3,
                        help='Candles to look ahead for target')
    parser.add_argument('--threshold', type=float, default=5.0,
                        help='Pip threshold for BUY/SELL classification')
    parser.add_argument('--max-rows', type=int, default=None,
                        help='Maximum rows to load (for testing)')
    
    args = parser.parse_args()
    
    # Determine data path
    base_path = Path(__file__).parent.parent.parent
    if args.timeframe == 'M5':
        data_path = base_path / 'ohlcv' / 'xauusd' / 'XAU_5m_data.csv'
    else:
        data_path = base_path / 'ohlcv' / 'xauusd' / 'XAU_15m_data.csv'
    
    if not data_path.exists():
        print(f"❌ Data file not found: {data_path}")
        return 1
    
    # Train model
    try:
        model_path, model_data = train_scalping_model(
            data_path=str(data_path),
            timeframe=args.timeframe,
            lookahead=args.lookahead,
            threshold_pips=args.threshold,
            max_rows=args.max_rows,
        )
        
        print("\n" + "=" * 60)
        print("🎉 Training Complete!")
        print("=" * 60)
        print(f"Model: {model_path}")
        print(f"Accuracy: {model_data['accuracy']:.2%}")
        if model_data.get('win_rate'):
            print(f"Win Rate: {model_data['win_rate']:.1f}%")
        
        return 0
        
    except Exception as e:
        print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
