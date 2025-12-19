#!/usr/bin/env python3
"""
BUY-ONLY High Win-Rate Model for XAUUSD.

Strategy: Only take BUY trades when all conditions align.
Based on previous analysis showing BUY signals have higher win rate.
"""

import os
import sys
import pickle
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import accuracy_score, classification_report
import xgboost as xgb
import lightgbm as lgb
import warnings
warnings.filterwarnings('ignore')

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def create_buy_focused_features(df: pd.DataFrame):
    """Create features optimized for BUY signal detection."""
    df = df.copy()
    
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # EMAs for trend
    for p in [10, 20, 50, 100]:
        df[f'ema_{p}'] = df['Close'].ewm(span=p).mean()
    
    # Trend alignment
    df['trend_score'] = (
        (df['ema_10'] > df['ema_20']).astype(int) +
        (df['ema_20'] > df['ema_50']).astype(int) +
        (df['ema_50'] > df['ema_100']).astype(int)
    )
    df['strong_uptrend'] = (df['trend_score'] >= 2).astype(int)
    
    # Price position
    df['above_ema_20'] = (df['Close'] > df['ema_20']).astype(int)
    df['above_ema_50'] = (df['Close'] > df['ema_50']).astype(int)
    df['dist_from_ema_20'] = (df['Close'] - df['ema_20']) / df['ema_20']
    
    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / (avg_loss + 1e-8)
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # RSI conditions for buying
    df['rsi_buy_zone'] = ((df['rsi'] > 40) & (df['rsi'] < 65)).astype(int)
    df['rsi_oversold'] = (df['rsi'] < 35).astype(int)
    
    # MACD
    ema_12 = df['Close'].ewm(span=12).mean()
    ema_26 = df['Close'].ewm(span=26).mean()
    df['macd'] = ema_12 - ema_26
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    df['macd_bullish'] = (df['macd'] > df['macd_signal']).astype(int)
    df['macd_rising'] = (df['macd'] > df['macd'].shift(1)).astype(int)
    
    # ATR
    df['tr'] = np.maximum(
        df['High'] - df['Low'],
        np.maximum(
            abs(df['High'] - df['Close'].shift(1)),
            abs(df['Low'] - df['Close'].shift(1))
        )
    )
    df['atr'] = df['tr'].rolling(14).mean()
    df['atr_norm'] = df['atr'] / df['Close']
    
    # Volatility
    df['vol_ratio'] = df['atr'] / df['atr'].rolling(50).mean()
    df['normal_vol'] = ((df['vol_ratio'] > 0.7) & (df['vol_ratio'] < 1.5)).astype(int)
    
    # Candle
    df['bullish_candle'] = (df['Close'] > df['Open']).astype(int)
    df['body_pct'] = abs(df['Close'] - df['Open']) / (df['High'] - df['Low'] + 1e-8)
    df['strong_bull'] = ((df['Close'] > df['Open']) & (df['body_pct'] > 0.5)).astype(int)
    
    # Recent momentum
    df['up_momentum'] = (df['Close'] > df['Close'].shift(3)).astype(int)
    df['returns_5'] = df['Close'].pct_change(5)
    
    # Support level (buying at support)
    df['recent_low'] = df['Low'].rolling(20).min()
    df['near_support'] = (df['Close'] < df['recent_low'] * 1.005).astype(int)
    
    # Time
    if 'Date' in df.columns:
        try:
            df['datetime'] = pd.to_datetime(df['Date'])
            df['hour'] = df['datetime'].dt.hour
            df['is_london'] = ((df['hour'] >= 7) & (df['hour'] < 15)).astype(int)
            df['is_ny'] = ((df['hour'] >= 12) & (df['hour'] < 20)).astype(int)
            df['prime_time'] = ((df['hour'] >= 8) & (df['hour'] < 16)).astype(int)
        except:
            df['hour'] = 12
            df['prime_time'] = 1
    
    # Buy confluence score
    df['buy_score'] = (
        df['strong_uptrend'] +
        df['above_ema_20'] +
        df['macd_bullish'] +
        df['rsi_buy_zone'] +
        df['bullish_candle'] +
        df['normal_vol']
    )
    
    feature_cols = [
        'trend_score', 'strong_uptrend',
        'above_ema_20', 'above_ema_50', 'dist_from_ema_20',
        'rsi', 'rsi_buy_zone', 'rsi_oversold',
        'macd_bullish', 'macd_rising',
        'atr_norm', 'vol_ratio', 'normal_vol',
        'bullish_candle', 'body_pct', 'strong_bull',
        'up_momentum', 'returns_5', 'near_support',
        'hour', 'prime_time',
        'buy_score',
    ]
    
    return df, feature_cols


def create_binary_target(df: pd.DataFrame, lookahead: int = 6, threshold_pips: float = 5.0):
    """Binary target: Will price go UP by threshold?"""
    df = df.copy()
    
    pip_value = 0.1
    threshold = threshold_pips * pip_value
    
    # Does price reach threshold UP within lookahead?
    df['future_max'] = df['High'].shift(-1).rolling(lookahead).max()
    df['up_move'] = df['future_max'] - df['Close']
    df['target'] = (df['up_move'] >= threshold).astype(int)
    
    return df


def train_buy_only_model(data_path: str, timeframe: str = "M5"):
    """Train model focused on high win-rate BUY signals."""
    
    print("=" * 70)
    print(f"🎯 BUY-ONLY High Win-Rate Model ({timeframe})")
    print("=" * 70)
    
    # Load
    print("\n📊 Loading data...")
    df = pd.read_csv(data_path, sep=';')
    print(f"   Loaded {len(df):,} rows")
    
    if len(df) > 500000:
        df = df.tail(500000).reset_index(drop=True)
    
    # Features
    print("\n🔧 Creating features...")
    df, feature_cols = create_buy_focused_features(df)
    df = create_binary_target(df, lookahead=8, threshold_pips=5.0)
    df = df.dropna()
    
    print(f"   Dataset: {len(df):,} rows")
    
    # Filter to only train on prime trading conditions
    # This teaches model what a "good BUY setup" looks like
    train_filter = (
        (df['prime_time'] == 1) &
        (df['strong_uptrend'] == 1) &
        (df['normal_vol'] == 1)
    )
    
    X_all = df[feature_cols].values
    y_all = df['target'].values
    
    # Split
    split_idx = int(len(df) * 0.8)
    X_train = X_all[:split_idx]
    y_train = y_all[:split_idx]
    X_test = X_all[split_idx:]
    y_test = y_all[split_idx:]
    
    # Apply filter on training set
    train_mask = train_filter.iloc[:split_idx].values
    X_train_filtered = X_train[train_mask]
    y_train_filtered = y_train[train_mask]
    
    print(f"\n📈 Training samples (filtered): {len(X_train_filtered):,}")
    print(f"   Test samples: {len(X_test):,}")
    print(f"   Train target rate: {y_train_filtered.mean()*100:.1f}% go UP")
    
    # Scale
    scaler = RobustScaler()
    X_train_scaled = scaler.fit_transform(X_train_filtered)
    X_test_scaled = scaler.transform(X_test)
    
    X_train_scaled = np.nan_to_num(X_train_scaled)
    X_test_scaled = np.nan_to_num(X_test_scaled)
    
    # Train
    print("\n🎯 Training LightGBM...")
    model = lgb.LGBMClassifier(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.02,
        num_leaves=24,
        subsample=0.7,
        colsample_bytree=0.7,
        min_child_samples=100,
        reg_alpha=1.0,
        reg_lambda=2.0,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    
    model.fit(X_train_scaled, y_train_filtered)
    
    # Evaluate
    print("\n📊 EVALUATION:")
    
    y_proba = model.predict_proba(X_test_scaled)[:, 1]
    
    # Reconstruct test data conditions
    test_data = df.iloc[split_idx:].copy()
    
    print("\n💰 WIN RATE BY CONFIDENCE & CONDITIONS:")
    print("-" * 70)
    
    for conf_thresh in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80]:
        for require_trend in [False, True]:
            for require_prime in [False, True]:
                
                # Build mask
                mask = y_proba >= conf_thresh
                
                if require_trend:
                    mask &= (test_data['strong_uptrend'].values == 1)
                if require_prime:
                    mask &= (test_data['prime_time'].values == 1)
                
                if mask.sum() < 20:
                    continue
                
                # Calculate win rate
                actual = y_test[mask]
                wins = actual.sum()
                total = len(actual)
                win_rate = wins / total * 100
                
                conditions = []
                if require_trend:
                    conditions.append("TREND")
                if require_prime:
                    conditions.append("PRIME")
                cond_str = "+".join(conditions) if conditions else "ANY"
                
                marker = " ⭐" if win_rate >= 50 else ""
                print(f"   Conf>={conf_thresh:.0%} [{cond_str:12s}]: Trades={total:5,}  Win={win_rate:5.1f}%{marker}")
    
    print("-" * 70)
    
    # Best combo analysis
    print("\n🏆 RECOMMENDED SETTINGS FOR >50% WIN RATE:")
    
    best_settings = []
    
    for conf in [0.50, 0.55, 0.60, 0.65, 0.70, 0.75]:
        mask = (y_proba >= conf) & (test_data['strong_uptrend'].values == 1) & (test_data['prime_time'].values == 1)
        if mask.sum() >= 50:
            actual = y_test[mask]
            wr = actual.sum() / len(actual) * 100
            if wr >= 50:
                best_settings.append((conf, mask.sum(), wr))
    
    if best_settings:
        best = max(best_settings, key=lambda x: x[1])  # Most trades with >50% WR
        print(f"   Confidence: >={best[0]:.0%}")
        print(f"   Conditions: TREND + PRIME TIME")
        print(f"   Expected Trades: {best[1]:,}")
        print(f"   Win Rate: {best[2]:.1f}%")
    else:
        print("   No combination achieves >50% with enough trades.")
        print("   Consider using H1 timeframe or combining with other filters.")
    
    # Feature importance
    print("\n🔍 Top 10 Features:")
    importance = model.feature_importances_
    indices = np.argsort(importance)[-10:][::-1]
    for i in indices:
        print(f"   {feature_cols[i]}: {importance[i]:.0f}")
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_dir = backend_dir / "models"
    model_path = model_dir / f"model_buyonly_xauusd_{timeframe}_{timestamp}.pkl"
    
    model_data = {
        'model': model,
        'scaler': scaler,
        'feature_columns': feature_cols,
        'timeframe': timeframe,
        'strategy': 'buy_only',
        'recommended_conditions': ['strong_uptrend', 'prime_time'],
        'trained_at': datetime.now().isoformat(),
    }
    
    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)
    
    print(f"\n✅ Model saved: {model_path}")
    
    return model_path, model_data


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeframe', default='M5', choices=['M5', 'M15'])
    args = parser.parse_args()
    
    base = Path(__file__).parent.parent.parent
    data = base / 'ohlcv' / 'xauusd' / f"XAU_{args.timeframe.lower().replace('m', '')}m_data.csv"
    
    if not data.exists():
        print(f"❌ Not found: {data}")
        return 1
    
    train_buy_only_model(str(data), args.timeframe)
    return 0


if __name__ == "__main__":
    sys.exit(main())
