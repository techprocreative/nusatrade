#!/usr/bin/env python3
"""
Crypto-Optimized ML Model Training for Bitcoin

This script uses crypto-specific features and parameters optimized for
Bitcoin's unique characteristics:
- High volatility
- 24/7 trading
- Momentum-driven
- Volume-sensitive

Usage:
    python3 train_crypto_model.py --symbol BTCUSD
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import pickle

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

# Import crypto feature engineer
sys.path.insert(0, 'backend/app/ml')
from crypto_features import CryptoFeatureEngineer


# Crypto-optimized configuration
CRYPTO_CONFIG = {
    'BTCUSD': {
        'spread_pips': 10.0,
        'profit_target_atr': 3.0,  # AGGRESSIVE: Larger targets for crypto
        'stop_loss_atr': 1.5,      # Wider stops
        'max_holding_hours': 20,   # Longer holding for bigger moves
        'data_path': 'ohlcv/btc/btcusd_1h_clean.csv',
        'description': 'Bitcoin - Cryptocurrency (Crypto-Optimized AGGRESSIVE)',

        # Crypto-specific filters
        'min_adx': 25,             # Only trade strong trends
        'min_volume_ratio': 1.3,   # Above average volume
        'require_trend_alignment': True,  # EMA alignment
        'avoid_extreme_volatility': True,
    },
}


def train_crypto_model(
    symbol='BTCUSD',
    model_type='xgboost',
):
    """Train crypto-optimized model for Bitcoin.

    Args:
        symbol: Trading symbol (BTCUSD)
        model_type: 'xgboost' (recommended) or 'gradient_boosting'

    Returns:
        Path to saved model
    """

    if symbol not in CRYPTO_CONFIG:
        raise ValueError(f"Unsupported symbol: {symbol}")

    config = CRYPTO_CONFIG[symbol]

    print("=" * 70)
    print(f"CRYPTO-OPTIMIZED ML TRAINING FOR {symbol}")
    print("=" * 70)
    print(f"\n🔷 Symbol: {symbol} ({config['description']})")
    print(f"🔷 Strategy: Trend-following with volume confirmation")
    print(f"🔷 Model Type: {model_type.upper()}")

    # Load data
    print(f"\n[1/8] Loading {symbol} data...")
    data_path = config['data_path']

    if not Path(data_path).exists():
        raise FileNotFoundError(f"Data file not found: {data_path}")

    df = pd.read_csv(data_path)
    print(f"  ✅ Loaded {len(df):,} candles from {data_path}")
    print(f"  📅 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Build CRYPTO-SPECIFIC features
    print("\n[2/8] Building crypto-optimized features...")
    print("  🔷 Momentum indicators (ROC, acceleration)")
    print("  🔷 Volume analysis (whale detection)")
    print("  🔷 Volatility regimes")
    print("  🔷 Trend alignment (multi-EMA)")
    print("  🔷 Breakout detection")

    engineer = CryptoFeatureEngineer()
    df_featured = engineer.build_crypto_features(df)
    print(f"  ✅ Crypto features built: {len(df_featured.columns)} columns")

    # Create CRYPTO-OPTIMIZED targets
    print(f"\n[3/8] Creating crypto-optimized trade targets...")
    print(f"  🔷 Spread: {config['spread_pips']} pips (crypto spread)")
    print(f"  🔷 Profit Target: {config['profit_target_atr']}x ATR (wider for volatility)")
    print(f"  🔷 Stop Loss: {config['stop_loss_atr']}x ATR (breathing room)")
    print(f"  🔷 Max Holding: {config['max_holding_hours']} hours (let trends develop)")
    print("  ⏱️  This may take 3-5 minutes...")

    df_featured = engineer.create_crypto_target(
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

    if trade_signals < 0.15:
        print(f"\n  ⚠️  Low trade signals ({trade_signals:.1%}) - crypto needs wider targets")

    # Prepare features
    print("\n[4/8] Preparing features for training...")

    df_clean = df_featured.dropna()
    print(f"  ✅ Clean samples: {len(df_clean):,}")

    # Select feature columns (exclude non-features)
    exclude_cols = [
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'target', 'returns',
        'ema_12_macd', 'ema_26_macd',  # Already in MACD
    ]
    feature_columns = [c for c in df_clean.columns if c not in exclude_cols]

    print(f"  ✅ Using {len(feature_columns)} crypto-optimized features")

    X = df_clean[feature_columns]
    y = df_clean['target']

    # Split chronologically
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
    print("  🔷 Crypto-optimized hyperparameters")
    print("  ⏱️  This may take 5-10 minutes...")

    if model_type == 'xgboost':
        import xgboost as xgb
        model = xgb.XGBClassifier(
            n_estimators=300,      # More trees for complex crypto patterns
            max_depth=8,            # Deeper trees for volatility
            learning_rate=0.03,     # Slower learning
            subsample=0.8,
            colsample_bytree=0.8,
            gamma=0.1,              # Regularization
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
            max_depth=8,
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

        print(f"\n  🔝 Top 20 Most Important Crypto Features:")
        print("  " + "-" * 60)
        for i, (feature, imp) in enumerate(sorted_importance[:20], 1):
            marker = ""
            if 'momentum' in feature or 'roc' in feature:
                marker = "🚀"
            elif 'volume' in feature:
                marker = "📊"
            elif 'trend' in feature or 'alignment' in feature:
                marker = "📈"
            elif 'volatility' in feature:
                marker = "⚡"

            print(f"  {i:2d}. {marker} {feature:30s} {imp:6.2%}")

    # Save model
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    symbol_lower = symbol.lower()
    model_dir = Path(f"models/{symbol_lower}/crypto-optimized")
    model_dir.mkdir(parents=True, exist_ok=True)

    model_filename = f"model_crypto_{model_type}_{timestamp}.pkl"
    model_path = model_dir / model_filename

    model_data = {
        'model': model,
        'scaler': scaler,
        'feature_columns': feature_columns,
        'model_type': model_type,
        'symbol': symbol,
        'strategy': 'crypto-optimized',
        'spread_pips': config['spread_pips'],
        'profit_target_atr': config['profit_target_atr'],
        'stop_loss_atr': config['stop_loss_atr'],
        'max_holding_hours': config['max_holding_hours'],
        'min_adx': config.get('min_adx', 25),
        'min_volume_ratio': config.get('min_volume_ratio', 1.3),
        'trained_at': datetime.utcnow().isoformat(),
        'accuracy': accuracy,
        'train_samples': len(X_train),
        'test_samples': len(X_test),
    }

    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)

    print(f"\n  💾 Model saved: {model_path}")
    print(f"     Size: {model_path.stat().st_size / 1024:.1f} KB")

    print("\n" + "=" * 70)
    print(f"CRYPTO-OPTIMIZED TRAINING COMPLETE FOR {symbol} ✅")
    print("=" * 70)

    print(f"\n🎯 Next Steps:")
    print(f"  1. Backtest with crypto filters:")
    print(f"     python3 backtest_crypto_model.py --symbol {symbol}")
    print(f"  2. Target metrics for crypto (adjusted for higher volatility):")
    print(f"     • Win Rate > 50% (lower than forex)")
    print(f"     • Profit Factor > 1.3 (crypto is harder)")
    print(f"     • Average R:R > 1.5:1")
    print(f"  3. If profitable → Test on demo for 60 days")

    return str(model_path)


if __name__ == '__main__':
    print("\n" + "#" * 70)
    print("# Crypto-Optimized ML Training Pipeline")
    print("# Symbol: BTCUSD")
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#" * 70)

    try:
        model_path = train_crypto_model(
            symbol='BTCUSD',
            model_type='xgboost',
        )

        print("\n" + "#" * 70)
        print("# Training Pipeline Complete!")
        print(f"# Model: {model_path}")
        print("#" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
