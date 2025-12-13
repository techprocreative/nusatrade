#!/usr/bin/env python3
"""
Symbol-Specific ML Model Training Pipeline

Train separate ML models for different trading symbols (XAUUSD, BTCUSD, EURUSD, etc).
Each symbol gets its own optimized model based on its unique characteristics.

Usage:
    python3 train_symbol_model.py --symbol BTCUSD
    python3 train_symbol_model.py --symbol EURUSD --optimize
    python3 train_symbol_model.py --symbol XAUUSD --model-type xgboost
"""

import sys
import os
import argparse
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import pickle

# Import improved feature engineer
sys.path.insert(0, 'backend/app/ml')
from improved_features import ImprovedFeatureEngineer

# Symbol-specific configurations
SYMBOL_CONFIGS = {
    'XAUUSD': {
        'spread_pips': 3.0,
        'profit_target_atr': 1.2,
        'stop_loss_atr': 0.8,
        'max_holding_hours': 12,
        'data_path': 'ohlcv/xauusd/xauusd_1h_clean.csv',
        'description': 'Gold - Commodity trading',
    },
    'BTCUSD': {
        'spread_pips': 10.0,  # Higher spread for crypto
        'profit_target_atr': 1.5,  # Larger targets for volatile crypto
        'stop_loss_atr': 1.0,
        'max_holding_hours': 8,  # Faster moves in crypto
        'data_path': 'ohlcv/btc/btcusd_1h_clean.csv',
        'description': 'Bitcoin - Cryptocurrency',
    },
    'EURUSD': {
        'spread_pips': 1.5,  # Tight spread for major forex
        'profit_target_atr': 1.0,
        'stop_loss_atr': 0.8,
        'max_holding_hours': 16,  # Slower moves in forex
        'data_path': 'ohlcv/eurusd/eurusd_1h_clean.csv',
        'description': 'EUR/USD - Major forex pair',
    },
}


def train_symbol_model(
    symbol: str,
    model_type='gradient_boosting',
    optimize=False,
):
    """Train symbol-specific ML model.

    Args:
        symbol: Trading symbol (XAUUSD, BTCUSD, EURUSD)
        model_type: 'gradient_boosting', 'random_forest', or 'xgboost'
        optimize: If True, run hyperparameter optimization

    Returns:
        Path to saved model file
    """

    # Validate symbol
    if symbol not in SYMBOL_CONFIGS:
        raise ValueError(
            f"Unsupported symbol '{symbol}'. "
            f"Supported symbols: {list(SYMBOL_CONFIGS.keys())}"
        )

    config = SYMBOL_CONFIGS[symbol]

    print("=" * 70)
    print(f"TRAINING ML MODEL FOR {symbol}")
    print("=" * 70)
    print(f"\nSymbol: {symbol} ({config['description']})")
    print(f"Model Type: {model_type}")
    print(f"Optimize: {optimize}")

    # Load data
    print(f"\n[1/7] Loading {symbol} data...")
    data_path = config['data_path']

    if not Path(data_path).exists():
        raise FileNotFoundError(
            f"Data file not found: {data_path}\n"
            f"Please prepare data first for {symbol}"
        )

    df = pd.read_csv(data_path)
    print(f"  ✅ Loaded {len(df):,} rows from {data_path}")
    print(f"  📅 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")

    # Build improved features
    print("\n[2/7] Building improved features...")
    print(f"  • Symbol-agnostic technical indicators")
    print(f"  • Trend strength features")
    print(f"  • Session and volatility features")

    engineer = ImprovedFeatureEngineer()
    df_featured = engineer.build_features(df)
    print(f"  ✅ Features built: {len(df_featured.columns)} columns")

    # Create profitable target
    print(f"\n[3/7] Creating profitable trade targets...")
    print(f"  • Spread: {config['spread_pips']} pips")
    print(f"  • Profit Target: {config['profit_target_atr']}x ATR")
    print(f"  • Stop Loss: {config['stop_loss_atr']}x ATR")
    print(f"  • Max holding: {config['max_holding_hours']} hours")
    print("  ⏱️  This may take 2-3 minutes...")

    df_featured = engineer.create_profitable_target(
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

    # Check if we have enough trading signals
    trade_signals = target_dist.get(1, 0) + target_dist.get(2, 0)
    if trade_signals < 0.10:  # Less than 10% trades
        print(f"\n  ⚠️  WARNING: Very few trade signals ({trade_signals:.1%})")
        print(f"     Consider adjusting parameters for {symbol}")

    # Prepare features
    print("\n[4/7] Preparing features for training...")

    # Remove rows with NaN
    df_clean = df_featured.dropna()
    print(f"  ✅ Clean samples: {len(df_clean):,}")

    # Select feature columns
    exclude_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'target', 'target_buy', 'target_sell', 'hour', 'day_of_week']
    feature_columns = [c for c in df_clean.columns if c not in exclude_cols]

    print(f"  ✅ Using {len(feature_columns)} features")

    X = df_clean[feature_columns]
    y = df_clean['target']

    # Split data chronologically (no shuffle!)
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    print(f"  ✅ Train: {len(X_train):,} samples ({df_clean['timestamp'].iloc[0]} to {df_clean['timestamp'].iloc[split_idx-1]})")
    print(f"  ✅ Test:  {len(X_test):,} samples ({df_clean['timestamp'].iloc[split_idx]} to {df_clean['timestamp'].iloc[-1]})")

    # Scale features
    print("\n[5/7] Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    print("  ✅ Features scaled")

    # Train model
    print(f"\n[6/7] Training {model_type.upper()} model...")
    print("  ⏱️  This may take 3-5 minutes...")

    if model_type == 'xgboost':
        try:
            import xgboost as xgb
            model = xgb.XGBClassifier(
                n_estimators=200,
                max_depth=7,
                learning_rate=0.05,
                subsample=0.8,
                colsample_bytree=0.8,
                random_state=42,
                tree_method='hist',
                verbosity=1
            )
        except ImportError:
            print("  ⚠️  XGBoost not installed, falling back to GradientBoosting")
            model_type = 'gradient_boosting'

    if model_type == 'gradient_boosting':
        model = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=7,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42,
            verbose=1
        )
    elif model_type == 'random_forest':
        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=12,
            min_samples_split=10,
            random_state=42,
            n_jobs=-1,
            verbose=1
        )

    model.fit(X_train_scaled, y_train)
    print("  ✅ Training complete")

    # Evaluate
    print("\n[7/7] Evaluating model...")

    y_pred = model.predict(X_test_scaled)
    y_pred_proba = model.predict_proba(X_test_scaled)

    accuracy = accuracy_score(y_test, y_pred)
    print(f"\n  📊 Overall Accuracy: {accuracy:.1%}")

    print(f"\n  📋 Classification Report:")
    print("  " + "-" * 60)

    # Get unique classes in predictions
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
    print(f"              Predicted")
    print(f"  Actual    HOLD    SELL     BUY")
    if len(cm) == 3:
        print(f"  HOLD   {cm[0][0]:7d} {cm[0][1]:7d} {cm[0][2]:7d}")
        print(f"  SELL   {cm[1][0]:7d} {cm[1][1]:7d} {cm[1][2]:7d}")
        print(f"  BUY    {cm[2][0]:7d} {cm[2][1]:7d} {cm[2][2]:7d}")

    # Feature importance
    if hasattr(model, 'feature_importances_'):
        importance = dict(zip(feature_columns, model.feature_importances_))
        sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)

        print(f"\n  🔝 Top 15 Most Important Features for {symbol}:")
        print("  " + "-" * 60)
        for i, (feature, imp) in enumerate(sorted_importance[:15], 1):
            print(f"  {i:2d}. {feature:25s} {imp:6.2%}")

    # Save model to symbol-specific directory
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create symbol-specific directory structure
    symbol_lower = symbol.lower()
    model_dir = Path(f"models/{symbol_lower}/staging")
    model_dir.mkdir(parents=True, exist_ok=True)

    model_filename = f"model_{model_type}_{timestamp}.pkl"
    model_path = model_dir / model_filename

    model_data = {
        'model': model,
        'scaler': scaler,
        'feature_columns': feature_columns,
        'model_type': model_type,
        'symbol': symbol,
        'spread_pips': config['spread_pips'],
        'profit_target_atr': config['profit_target_atr'],
        'stop_loss_atr': config['stop_loss_atr'],
        'max_holding_hours': config['max_holding_hours'],
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
    print(f"TRAINING COMPLETE FOR {symbol} ✅")
    print("=" * 70)

    print(f"\n🎯 Next Steps:")
    print(f"  1. Backtest this model: python3 backtest_symbol_model.py --symbol {symbol}")
    print(f"  2. Check performance metrics:")
    print(f"     • Win Rate > 60%")
    print(f"     • Profit Factor > 1.5")
    print(f"     • Max Drawdown < 5%")
    print(f"  3. If profitable → Move to production:")
    print(f"     mv {model_path} models/{symbol_lower}/production/")
    print(f"  4. If not profitable → Adjust parameters and retrain")

    return str(model_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Train symbol-specific ML trading model'
    )
    parser.add_argument(
        '--symbol',
        type=str,
        required=True,
        choices=list(SYMBOL_CONFIGS.keys()),
        help='Trading symbol to train model for'
    )
    parser.add_argument(
        '--model-type',
        type=str,
        default='gradient_boosting',
        choices=['gradient_boosting', 'random_forest', 'xgboost'],
        help='Type of ML model to train'
    )
    parser.add_argument(
        '--optimize',
        action='store_true',
        help='Run hyperparameter optimization'
    )

    args = parser.parse_args()

    print("\n" + "#" * 70)
    print(f"# Symbol-Specific ML Training Pipeline")
    print(f"# Symbol: {args.symbol}")
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#" * 70)

    try:
        model_path = train_symbol_model(
            symbol=args.symbol,
            model_type=args.model_type,
            optimize=args.optimize,
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
