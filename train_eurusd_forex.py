#!/usr/bin/env python3
"""
EURUSD Forex-Optimized ML Training

Train EURUSD model using forex-specific features that focus on:
- Mean reversion patterns
- Support/Resistance levels
- Session-based behavior
- Volatility regime detection

This is fundamentally different from the XAUUSD approach.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, 'backend/app/ml')

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import pickle

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

from forex_features import ForexFeatureEngineer


# Forex-optimized configuration
EURUSD_FOREX_CONFIG = {
    'spread_pips': 1.5,
    'profit_target_atr': 1.0,  # Tighter for more signals
    'stop_loss_atr': 0.8,      # Tighter stop
    'max_holding_hours': 16,   # Shorter holding
    'description': 'EURUSD - Forex Pair (Forex-Optimized)',
}


def train_eurusd_forex(model_type='xgboost'):
    """
    Train EURUSD with forex-specific features.

    Args:
        model_type: 'xgboost' (recommended)

    Returns:
        Path to saved model
    """

    config = EURUSD_FOREX_CONFIG

    print("=" * 70)
    print("FOREX-OPTIMIZED ML TRAINING FOR EURUSD")
    print("=" * 70)
    print(f"\n💱 Symbol: EURUSD ({config['description']})")
    print(f"💱 Strategy: Hybrid (Trend + Mean Reversion)")
    print(f"💱 Model Type: {model_type.upper()}")
    print(f"💱 Features: Forex-specific (S/R, sessions, volatility regimes)")

    # Load historical data (balanced market conditions)
    print(f"\n[1/8] Loading EURUSD historical data...")
    data_path = 'ohlcv/eurusd/eurusd_1h_clean.csv'  # Use older data with balanced trends

    if not Path(data_path).exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    df = pd.read_csv(data_path)
    print(f"  ✅ Loaded {len(df):,} candles from {data_path}")
    print(f"  📅 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Build FOREX-SPECIFIC features
    print("\n[2/8] Building forex-optimized features...")
    print("  💱 Mean reversion indicators (Z-score, RSI extremes, BB position)")
    print("  💱 Support/Resistance levels (pivots, round numbers, swing levels)")
    print("  💱 Session analysis (Asian/London/NY, hour patterns)")
    print("  💱 Volatility regimes (compression/expansion, ATR percentile)")
    print("  💱 Trend vs Range detection (ADX, Donchian, ranging)")

    engineer = ForexFeatureEngineer()
    df_featured = engineer.build_forex_features(df)
    print(f"  ✅ Forex features built: {len(df_featured.columns)} columns")

    # Create FOREX-OPTIMIZED targets
    print(f"\n[3/8] Creating forex-optimized trade targets...")
    print(f"  💱 Spread: {config['spread_pips']} pips (forex spread)")
    print(f"  💱 Profit Target: {config['profit_target_atr']}x ATR (balanced)")
    print(f"  💱 Stop Loss: {config['stop_loss_atr']}x ATR (reasonable)")
    print(f"  💱 Max Holding: {config['max_holding_hours']} hours (daily cycles)")
    print("  ⏱️  This may take 2-3 minutes...")

    df_featured = engineer.create_forex_target(
        df_featured,
        spread_pips=config['spread_pips'],
        profit_target_atr=config['profit_target_atr'],
        stop_loss_atr=config['stop_loss_atr'],
        max_holding_hours=config['max_holding_hours']
    )
    print(f"  ✅ Targets created")

    # Check target distribution
    target_dist = df_featured['target'].value_counts(normalize=True)
    print(f"\n  📊 Target Distribution:")
    print(f"    • HOLD (0): {target_dist.get(0, 0):.1%}")
    print(f"    • SELL (1): {target_dist.get(1, 0):.1%}")
    print(f"    • BUY (2): {target_dist.get(2, 0):.1%}")

    trade_signals = target_dist.get(1, 0) + target_dist.get(2, 0)
    print(f"    • Trade Signals: {trade_signals:.1%}")

    if trade_signals < 0.10:
        print(f"\n  ⚠️  Low trade signals ({trade_signals:.1%}) - may need wider targets")
    elif trade_signals > 0.80:
        print(f"\n  ⚠️  Too many trade signals ({trade_signals:.1%}) - may need stricter targets")

    # Prepare features
    print("\n[4/8] Preparing features for training...")

    df_clean = df_featured.dropna()
    print(f"  ✅ Clean samples: {len(df_clean):,}")

    # Select feature columns (exclude non-features)
    exclude_cols = [
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'target',
        # Exclude intermediate round level values
        'round_level_0001', 'round_level_001', 'round_level_01',
    ]
    feature_columns = [c for c in df_clean.columns if c not in exclude_cols]

    print(f"  ✅ Using {len(feature_columns)} forex-optimized features")

    X = df_clean[feature_columns]
    y = df_clean['target']

    # Split chronologically (80/20)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    print(f"  ✅ Train: {len(X_train):,} samples")
    print(f"  ✅ Test:  {len(X_test):,} samples")

    # Scale features
    print("\n[5/8] Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    print("  ✅ Features scaled")

    # Train model
    print(f"\n[6/8] Training {model_type.upper()} model...")
    print("  💱 Forex-optimized hyperparameters")
    print("  ⏱️  This may take 5-10 minutes...")

    if model_type == 'xgboost':
        import xgboost as xgb
        model = xgb.XGBClassifier(
            n_estimators=300,
            max_depth=7,            # Slightly shallower for forex
            learning_rate=0.03,
            subsample=0.8,
            colsample_bytree=0.8,
            gamma=0.1,
            min_child_weight=3,
            random_state=42,
            tree_method='hist',
            eval_metric='mlogloss',
            verbosity=1
        )
    else:
        from sklearn.ensemble import GradientBoostingClassifier
        model = GradientBoostingClassifier(
            n_estimators=300,
            max_depth=7,
            learning_rate=0.03,
            subsample=0.8,
            random_state=42,
            verbose=1
        )

    model.fit(X_train_scaled, y_train)
    print("  ✅ Training complete")

    # Evaluate
    print("\n[7/8] Evaluating model...")

    y_pred = model.predict(X_test_scaled)
    y_pred_proba = model.predict_proba(X_test_scaled)

    accuracy = accuracy_score(y_test, y_pred)
    print(f"\n  📊 Overall Accuracy: {accuracy:.1%}")

    print(f"\n  📋 Classification Report:")
    print("  " + "-" * 60)

    unique_classes = sorted(np.unique(np.concatenate([y_test, y_pred])))
    class_names = {0: 'HOLD', 1: 'SELL', 2: 'BUY'}
    target_names = [class_names.get(c, f'Class_{c}') for c in unique_classes]

    report = classification_report(
        y_test, y_pred,
        labels=unique_classes,
        target_names=target_names,
        zero_division=0
    )
    for line in report.split('\n'):
        print(f"  {line}")

    print(f"\n  🎯 Confusion Matrix:")
    print("  " + "-" * 60)
    cm = confusion_matrix(y_test, y_pred)
    if len(cm) == 3:
        print(f"              Predicted")
        print(f"  Actual    HOLD    SELL     BUY")
        print(f"  HOLD   {cm[0][0]:7d} {cm[0][1]:7d} {cm[0][2]:7d}")
        print(f"  SELL   {cm[1][0]:7d} {cm[1][1]:7d} {cm[1][2]:7d}")
        print(f"  BUY    {cm[2][0]:7d} {cm[2][1]:7d} {cm[2][2]:7d}")

    # Feature importance
    if hasattr(model, 'feature_importances_'):
        importance = dict(zip(feature_columns, model.feature_importances_))
        sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)

        print(f"\n  🔝 Top 30 Most Important Forex Features:")
        print("  " + "-" * 60)
        for i, (feature, imp) in enumerate(sorted_importance[:30], 1):
            marker = ""
            if 'mean' in feature or 'reversion' in feature or 'zscore' in feature:
                marker = "🔄"  # Mean reversion
            elif 'session' in feature or 'hour' in feature:
                marker = "🕐"  # Time/session
            elif 'support' in feature or 'resistance' in feature or 'pivot' in feature or 'psych' in feature:
                marker = "📍"  # S/R levels
            elif 'volatility' in feature or 'atr' in feature or 'bb' in feature:
                marker = "⚡"  # Volatility
            elif 'trend' in feature or 'adx' in feature or 'momentum' in feature:
                marker = "📈"  # Trend

            print(f"  {i:2d}. {marker} {feature:35s} {imp:6.2%}")

    # Save model
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    model_dir = Path(f"models/eurusd/forex-optimized")
    model_dir.mkdir(parents=True, exist_ok=True)

    model_filename = f"model_forex_{model_type}_{timestamp}.pkl"
    model_path = model_dir / model_filename

    model_data = {
        'model': model,
        'scaler': scaler,
        'feature_columns': feature_columns,
        'model_type': model_type,
        'symbol': 'EURUSD',
        'strategy': 'forex-optimized',
        'spread_pips': config['spread_pips'],
        'profit_target_atr': config['profit_target_atr'],
        'stop_loss_atr': config['stop_loss_atr'],
        'max_holding_hours': config['max_holding_hours'],
        'trained_at': datetime.utcnow().isoformat(),
        'accuracy': accuracy,
        'train_samples': len(X_train),
        'test_samples': len(X_test),
        'data_period': f"{df['timestamp'].min()} to {df['timestamp'].max()}",
    }

    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)

    print(f"\n[8/8] Model saved")
    print(f"  💾 Path: {model_path}")
    print(f"  📦 Size: {model_path.stat().st_size / 1024:.1f} KB")

    print("\n" + "=" * 70)
    print(f"FOREX-OPTIMIZED TRAINING COMPLETE FOR EURUSD ✅")
    print("=" * 70)

    print(f"\n🎯 Next Steps:")
    print(f"  1. Backtest with multiple confidence thresholds")
    print(f"  2. Test different TP/SL combinations:")
    print(f"     • Current: {config['profit_target_atr']}:{config['stop_loss_atr']} ATR")
    print(f"     • Try: 1.0:0.8, 1.5:1.0, 2.0:1.2")
    print(f"  3. Target metrics:")
    print(f"     • Profit Factor > 1.5 (minimum acceptable)")
    print(f"     • Win Rate > 60% (good for forex)")
    print(f"     • Compare with baseline (old model: PF 0.94)")
    print(f"  4. If profitable → Test on demo for 30 days")

    print(f"\n💡 Key Question:")
    print(f"   Did forex-specific features improve profitability?")
    print(f"   Baseline (XAUUSD features): PF 0.94, WR 46.7%")
    print(f"   Forex features should show: PF > 1.0 at minimum")

    return str(model_path)


if __name__ == '__main__':
    print("\n" + "#" * 70)
    print("# EURUSD Forex-Optimized ML Training Pipeline")
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#" * 70)

    try:
        model_path = train_eurusd_forex(model_type='xgboost')

        print("\n" + "#" * 70)
        print("# Training Pipeline Complete!")
        print(f"# Model: {model_path}")
        print("#" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
