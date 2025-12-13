#!/usr/bin/env python3
"""
Train XGBoost Model - Often Better Than Gradient Boosting
XGBoost typically handles imbalanced data and feature importance better.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import pandas as pd
import numpy as np
from datetime import datetime
import pickle

# Try to import xgboost
try:
    import xgboost as xgb
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
except ImportError:
    print("Installing xgboost...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "xgboost", "-q"])
    import xgboost as xgb
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

sys.path.insert(0, 'backend/app/ml')
from improved_features import ImprovedFeatureEngineer


def train_xgboost_model():
    """Train XGBoost model - typically better than GB."""

    print("="*70)
    print("TRAINING XGBOOST MODEL")
    print("="*70)

    # Load data
    print("\n[1/7] Loading data...")
    df = pd.read_csv('ohlcv/xauusd/xauusd_1h_clean.csv')
    print(f"  ✅ Loaded {len(df):,} rows")

    # Build features
    print("\n[2/7] Building features...")
    engineer = ImprovedFeatureEngineer()
    df_featured = engineer.build_features(df)

    # Create targets with MORE ACHIEVABLE parameters
    print("\n[3/7] Creating targets with relaxed parameters...")
    print("  • TP: 0.8x ATR (smaller target, easier to hit)")
    print("  • SL: 1.2x ATR (larger stop, less noise)")
    print("  • Max holding: 8 hours (shorter, less market risk)")

    df_featured = engineer.create_profitable_target(
        df_featured,
        spread_pips=3.0,
        profit_target_atr=0.8,  # Smaller TP
        stop_loss_atr=1.2,  # Larger SL
        max_holding_hours=8  # Shorter time
    )

    # Check distribution
    target_dist = df_featured['target'].value_counts(normalize=True)
    print(f"\n  Target Distribution:")
    print(f"    • HOLD: {target_dist.get(0, 0):.1%}")
    print(f"    • SELL: {target_dist.get(1, 0):.1%}")
    print(f"    • BUY: {target_dist.get(2, 0):.1%}")

    # Prepare data
    print("\n[4/7] Preparing data...")
    df_clean = df_featured.dropna()

    exclude_cols = ['timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'target', 'target_buy', 'target_sell', 'hour', 'day_of_week']
    feature_columns = [c for c in df_clean.columns if c not in exclude_cols]

    X = df_clean[feature_columns]
    y = df_clean['target']

    # Split chronologically
    split_idx = int(len(X) * 0.8)
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    print(f"  ✅ Train: {len(X_train):,}, Test: {len(X_test):,}")

    # Scale
    print("\n[5/7] Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # Train XGBoost
    print("\n[6/7] Training XGBoost...")
    print("  Parameters optimized for trading:")
    print("  • max_depth=6 (prevent overfitting)")
    print("  • learning_rate=0.05 (slow, steady learning)")
    print("  • subsample=0.8 (prevent overfitting)")
    print("  • colsample_bytree=0.8 (feature randomness)")

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        objective='multi:softprob',
        num_class=3,
        random_state=42,
        n_jobs=-1,
        eval_metric='mlogloss'
    )

    model.fit(
        X_train_scaled, y_train,
        eval_set=[(X_test_scaled, y_test)],
        verbose=20
    )

    # Evaluate
    print("\n[7/7] Evaluating...")
    y_pred = model.predict(X_test_scaled)
    y_proba = model.predict_proba(X_test_scaled)

    accuracy = accuracy_score(y_test, y_pred)
    print(f"\n  📊 Overall Accuracy: {accuracy:.1%}")

    # Classification report
    unique_classes = sorted(np.unique(np.concatenate([y_test, y_pred])))
    class_names = {0: 'HOLD', 1: 'SELL', 2: 'BUY'}
    target_names = [class_names.get(c, f'Class_{c}') for c in unique_classes]

    print(f"\n  📋 Classification Report:")
    report = classification_report(y_test, y_pred, labels=unique_classes,
                                   target_names=target_names, zero_division=0)
    for line in report.split('\n'):
        print(f"  {line}")

    # Feature importance
    importance = dict(zip(feature_columns, model.feature_importances_))
    sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)

    print(f"\n  🔝 Top 15 Features:")
    for i, (feature, imp) in enumerate(sorted_importance[:15], 1):
        print(f"    {i:2d}. {feature:25s} {imp:6.2%}")

    # Save model
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_path = f"models/model_xgboost_{timestamp}.pkl"

    os.makedirs('models', exist_ok=True)

    model_data = {
        'model': model,
        'scaler': scaler,
        'feature_columns': feature_columns,
        'model_type': 'xgboost',
        'spread_pips': 3.0,
        'profit_target_atr': 0.8,
        'stop_loss_atr': 1.2,
        'trained_at': datetime.utcnow().isoformat(),
        'accuracy': accuracy
    }

    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)

    print(f"\n  💾 Model saved: {model_path}")

    print("\n" + "="*70)
    print("TRAINING COMPLETE ✅")
    print("="*70)
    print(f"\nNext: Test this model with backtest_improved_model.py")
    print(f"Expected: Better performance due to:")
    print(f"  • XGBoost (usually better than GB)")
    print(f"  • Smaller TP (0.8x ATR - easier to hit)")
    print(f"  • Larger SL (1.2x ATR - less false stops)")

    return model_path


if __name__ == '__main__':
    print("\n" + "#"*70)
    print("# XGBoost Model Training")
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#"*70)

    model_path = train_xgboost_model()

    print("\n" + "#"*70)
    print(f"# Model: {model_path}")
    print("#"*70 + "\n")
