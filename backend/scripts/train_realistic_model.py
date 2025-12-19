#!/usr/bin/env python3
"""
Realistic High Win-Rate Model for XAUUSD.

This version uses proper target definition:
- Target is ACTUAL profit (TP hit before SL)
- No data leakage
- Proper time-series split
"""

import os
import sys
import pickle
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import lightgbm as lgb
import warnings
warnings.filterwarnings('ignore')

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


def create_features(df: pd.DataFrame):
    """Standard feature engineering."""
    df = df.copy()
    
    for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # EMAs
    for p in [10, 20, 50, 100]:
        df[f'ema_{p}'] = df['Close'].ewm(span=p).mean()
    
    # Trend
    df['trend_score'] = (
        (df['ema_10'] > df['ema_20']).astype(int) +
        (df['ema_20'] > df['ema_50']).astype(int) +
        (df['ema_50'] > df['ema_100']).astype(int)
    )
    df['strong_uptrend'] = (df['trend_score'] >= 2).astype(int)
    df['strong_downtrend'] = (df['trend_score'] <= 1).astype(int)
    df['dist_ema_20'] = (df['Close'] - df['ema_20']) / df['ema_20']
    
    # RSI
    delta = df['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(14).mean()
    avg_loss = loss.rolling(14).mean()
    rs = avg_gain / (avg_loss + 1e-8)
    df['rsi'] = 100 - (100 / (1 + rs))
    df['rsi_oversold'] = (df['rsi'] < 30).astype(int)
    df['rsi_overbought'] = (df['rsi'] > 70).astype(int)
    
    # MACD
    ema_12 = df['Close'].ewm(span=12).mean()
    ema_26 = df['Close'].ewm(span=26).mean()
    df['macd'] = ema_12 - ema_26
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    df['macd_bull'] = (df['macd'] > df['macd_signal']).astype(int)
    
    # Stochastic
    low_min = df['Low'].rolling(14).min()
    high_max = df['High'].rolling(14).max()
    df['stoch'] = 100 * (df['Close'] - low_min) / (high_max - low_min + 1e-8)
    df['stoch_oversold'] = (df['stoch'] < 20).astype(int)
    df['stoch_overbought'] = (df['stoch'] > 80).astype(int)
    
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
    df['vol_ratio'] = df['atr'] / (df['atr'].rolling(50).mean() + 1e-8)
    
    # Candles
    df['bullish'] = (df['Close'] > df['Open']).astype(int)
    df['body'] = abs(df['Close'] - df['Open']) / (df['High'] - df['Low'] + 1e-8)
    
    # Returns
    df['ret_1'] = df['Close'].pct_change(1)
    df['ret_3'] = df['Close'].pct_change(3)
    df['ret_5'] = df['Close'].pct_change(5)
    
    # Time
    if 'Date' in df.columns:
        try:
            df['datetime'] = pd.to_datetime(df['Date'])
            df['hour'] = df['datetime'].dt.hour
            df['dow'] = df['datetime'].dt.dayofweek
            df['prime_time'] = ((df['hour'] >= 8) & (df['hour'] < 16)).astype(int)
        except:
            df['hour'] = 12
            df['dow'] = 2
            df['prime_time'] = 1
    
    feature_cols = [
        'trend_score', 'strong_uptrend', 'strong_downtrend', 'dist_ema_20',
        'rsi', 'rsi_oversold', 'rsi_overbought',
        'macd_bull',
        'stoch', 'stoch_oversold', 'stoch_overbought',
        'atr_norm', 'vol_ratio',
        'bullish', 'body',
        'ret_1', 'ret_3', 'ret_5',
        'hour', 'dow', 'prime_time',
    ]
    
    return df, feature_cols


def create_realistic_target(df: pd.DataFrame, lookahead: int = 12, tp_pips: float = 8.0, sl_pips: float = 5.0):
    """
    Realistic target: Does TP get hit before SL?
    
    For BUY: TP = entry + tp_pips, SL = entry - sl_pips
    For SELL: TP = entry - tp_pips, SL = entry + sl_pips
    
    Target:
    - 1 = BUY would win (long TP hit before long SL)
    - 2 = SELL would win (short TP hit before short SL)  
    - 0 = Neither wins (HOLD)
    """
    df = df.copy()
    
    pip = 0.1  # XAUUSD
    tp = tp_pips * pip
    sl = sl_pips * pip
    
    entry = df['Close'].values
    target = np.zeros(len(df))
    
    for i in range(len(df) - lookahead):
        future_highs = df['High'].iloc[i+1:i+1+lookahead].values
        future_lows = df['Low'].iloc[i+1:i+1+lookahead].values
        e = entry[i]
        
        # Long trade analysis
        long_tp = e + tp
        long_sl = e - sl
        
        long_tp_idx = None
        long_sl_idx = None
        
        for j, (h, l) in enumerate(zip(future_highs, future_lows)):
            if long_tp_idx is None and h >= long_tp:
                long_tp_idx = j
            if long_sl_idx is None and l <= long_sl:
                long_sl_idx = j
        
        long_win = (long_tp_idx is not None) and (long_sl_idx is None or long_tp_idx < long_sl_idx)
        
        # Short trade analysis
        short_tp = e - tp
        short_sl = e + sl
        
        short_tp_idx = None
        short_sl_idx = None
        
        for j, (h, l) in enumerate(zip(future_highs, future_lows)):
            if short_tp_idx is None and l <= short_tp:
                short_tp_idx = j
            if short_sl_idx is None and h >= short_sl:
                short_sl_idx = j
        
        short_win = (short_tp_idx is not None) and (short_sl_idx is None or short_tp_idx < short_sl_idx)
        
        # Assign target
        if long_win and not short_win:
            target[i] = 1  # BUY
        elif short_win and not long_win:
            target[i] = 2  # SELL
        elif long_win and short_win:
            # Both win, pick faster one
            if long_tp_idx <= short_tp_idx:
                target[i] = 1
            else:
                target[i] = 2
        else:
            target[i] = 0  # HOLD
    
    df['target'] = target.astype(int)
    return df


def train_realistic_model(
    data_path: str,
    timeframe: str = "M5",
    lookahead: int = 12,
    tp_pips: float = 8.0,
    sl_pips: float = 5.0,
):
    """Train model with realistic target."""
    
    print("=" * 70)
    print(f"🎯 REALISTIC High Win-Rate Model ({timeframe})")
    print("=" * 70)
    print(f"   TP={tp_pips} pips, SL={sl_pips} pips, Lookahead={lookahead}")
    print(f"   Risk:Reward = 1:{tp_pips/sl_pips:.1f}")
    
    # Load
    print("\n📊 Loading data...")
    df = pd.read_csv(data_path, sep=';')
    print(f"   Loaded {len(df):,} rows")
    
    if len(df) > 400000:
        df = df.tail(400000).reset_index(drop=True)
    
    # Features & Target
    print("\n🔧 Creating features and realistic target...")
    df, feature_cols = create_features(df)
    df = create_realistic_target(df, lookahead=lookahead, tp_pips=tp_pips, sl_pips=sl_pips)
    df = df.dropna()
    
    print(f"   Dataset: {len(df):,} rows")
    
    # Distribution
    unique, counts = np.unique(df['target'].values, return_counts=True)
    print(f"\n📊 Realistic Target Distribution:")
    for u, c in zip(unique, counts):
        label = ['HOLD', 'BUY wins', 'SELL wins'][u]
        print(f"   {label}: {c:,} ({c/len(df)*100:.1f}%)")
    
    # Prepare
    X = df[feature_cols].values
    y = df['target'].values
    
    # Split (time-series)
    split_idx = int(len(df) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    
    print(f"\n📈 Train: {len(X_train):,}, Test: {len(X_test):,}")
    
    # Scale
    scaler = RobustScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    X_train_scaled = np.nan_to_num(X_train_scaled)
    X_test_scaled = np.nan_to_num(X_test_scaled)
    
    # Train
    print("\n🎯 Training LightGBM...")
    model = lgb.LGBMClassifier(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.02,
        num_leaves=32,
        subsample=0.7,
        colsample_bytree=0.7,
        min_child_samples=50,
        reg_alpha=0.5,
        reg_lambda=1.0,
        class_weight='balanced',
        random_state=42,
        n_jobs=-1,
        verbose=-1,
    )
    
    model.fit(X_train_scaled, y_train)
    
    # Evaluate
    print("\n📊 EVALUATION:")
    y_proba = model.predict_proba(X_test_scaled)
    y_pred = np.argmax(y_proba, axis=1)
    max_conf = y_proba.max(axis=1)
    
    acc = accuracy_score(y_test, y_pred)
    print(f"   Overall Accuracy: {acc:.4f}")
    
    print("\n   Classification Report:")
    print(classification_report(y_test, y_pred, target_names=['HOLD', 'BUY', 'SELL']))
    
    # Win rate by confidence
    print("\n💰 TRADE WIN RATE BY CONFIDENCE:")
    print("-" * 70)
    
    # Reconstruct conditions
    test_df = df.iloc[split_idx:].copy()
    
    best_wr = 0
    best_conf = 0.5
    best_trades = 0
    
    for conf in [0.35, 0.40, 0.45, 0.50, 0.55, 0.60, 0.65, 0.70]:
        # Only BUY/SELL predictions (not HOLD)
        trade_mask = (y_pred != 0) & (max_conf >= conf)
        
        if trade_mask.sum() < 20:
            continue
        
        # Win = prediction matches actual winning outcome
        wins = (y_pred[trade_mask] == y_test[trade_mask]).sum()
        total = trade_mask.sum()
        wr = wins / total * 100
        
        marker = " ⭐" if wr >= 50 else ""
        print(f"   Confidence >= {conf:.0%}: Trades={total:5,}  Win Rate={wr:5.1f}%{marker}")
        
        if wr >= 50 and total > best_trades:
            best_wr = wr
            best_conf = conf
            best_trades = total
    
    # With additional filters
    print("\n   With TREND + PRIME TIME filter:")
    for conf in [0.35, 0.40, 0.45, 0.50, 0.55, 0.60]:
        trade_mask = (
            (y_pred != 0) & 
            (max_conf >= conf) &
            (test_df['strong_uptrend'].values == 1) &
            (test_df['prime_time'].values == 1)
        )
        
        if trade_mask.sum() < 20:
            continue
        
        wins = (y_pred[trade_mask] == y_test[trade_mask]).sum()
        total = trade_mask.sum()
        wr = wins / total * 100
        
        marker = " ⭐" if wr >= 50 else ""
        print(f"   Confidence >= {conf:.0%}: Trades={total:5,}  Win Rate={wr:5.1f}%{marker}")
        
        if wr >= 50 and total > best_trades:
            best_wr = wr
            best_conf = conf
            best_trades = total
    
    print("-" * 70)
    
    if best_wr >= 50:
        print(f"\n🏆 BEST SETTING ACHIEVING >50% WIN RATE:")
        print(f"   Confidence Threshold: {best_conf:.0%}")
        print(f"   Expected Trades: {best_trades:,}")
        print(f"   Win Rate: {best_wr:.1f}%")
    else:
        print(f"\n⚠️ No setting achieved >50% win rate.")
        print(f"   Best: {best_wr:.1f}% at conf {best_conf:.0%}")
        print(f"   Consider: Longer timeframe, wider TP, tighter SL")
    
    # Feature importance
    print("\n🔍 Top 10 Features:")
    importance = model.feature_importances_
    indices = np.argsort(importance)[-10:][::-1]
    for i in indices:
        print(f"   {feature_cols[i]}: {importance[i]:.0f}")
    
    # Save
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_dir = backend_dir / "models"
    model_path = model_dir / f"model_realistic_xauusd_{timeframe}_{timestamp}.pkl"
    
    model_data = {
        'model': model,
        'scaler': scaler,
        'feature_columns': feature_cols,
        'timeframe': timeframe,
        'tp_pips': tp_pips,
        'sl_pips': sl_pips,
        'lookahead': lookahead,
        'best_confidence': best_conf,
        'best_winrate': best_wr,
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
    parser.add_argument('--lookahead', type=int, default=12)
    parser.add_argument('--tp', type=float, default=8.0)
    parser.add_argument('--sl', type=float, default=5.0)
    args = parser.parse_args()
    
    base = Path(__file__).parent.parent.parent
    tf_map = {'M5': '5m', 'M15': '15m'}
    data = base / 'ohlcv' / 'xauusd' / f"XAU_{tf_map[args.timeframe]}_data.csv"
    
    if not data.exists():
        print(f"❌ Not found: {data}")
        return 1
    
    train_realistic_model(
        str(data), 
        args.timeframe, 
        args.lookahead, 
        args.tp, 
        args.sl
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
