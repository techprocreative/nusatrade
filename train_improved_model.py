#!/usr/bin/env python3
"""
Improved ML Training with Profitable Target Definition
and Gold-Specific Features.

This script addresses the problems found in backtesting:
1. Better target definition (profitable trades vs fixed exit)
2. Gold-specific features (sessions, volatility regimes)
3. Multi-class classification (BUY/SELL/HOLD)
4. Proper validation
"""

import sys
import os
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


def train_improved_model(
    model_type='gradient_boosting',
    spread_pips=3.0,
    profit_target_atr=1.5,
    stop_loss_atr=0.8
):
    """Train model with improved features and target definition."""

    print("="*70)
    print("IMPROVED ML MODEL TRAINING")
    print("="*70)

    # Load data
    print("\n[1/7] Loading XAUUSD data...")
    df = pd.read_csv('ohlcv/xauusd/xauusd_1h_clean.csv')
    print(f"  ✅ Loaded {len(df):,} rows")

    # Build improved features
    print("\n[2/7] Building improved features...")
    print("  • Adding Gold-specific indicators (sessions, regimes)")
    print("  • Adding trend strength features")
    print("  • Adding price level features")

    engineer = ImprovedFeatureEngineer()
    df_featured = engineer.build_features(df)
    print(f"  ✅ Features built")

    # Create profitable target
    print(f"\n[3/7] Creating profitable trade targets...")
    print(f"  • Spread: {spread_pips} pips")
    print(f"  • Profit Target: {profit_target_atr}x ATR")
    print(f"  • Stop Loss: {stop_loss_atr}x ATR")
    print(f"  • Max holding: 24 hours")
    print("  This may take 2-3 minutes...")

    df_featured = engineer.create_profitable_target(
        df_featured,
        spread_pips=spread_pips,
        profit_target_atr=profit_target_atr,
        stop_loss_atr=stop_loss_atr,
        max_holding_hours=12  # Shorter holding for better balance
    )
    print(f"  ✅ Targets created")

    # Check target distribution
    target_dist = df_featured['target'].value_counts(normalize=True)
    print(f"\n  Target Distribution:")
    print(f"    • HOLD (0): {target_dist.get(0, 0):.1%}")
    print(f"    • SELL (1): {target_dist.get(1, 0):.1%}")
    print(f"    • BUY (2): {target_dist.get(2, 0):.1%}")

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

    print(f"  ✅ Train: {len(X_train):,} samples")
    print(f"  ✅ Test: {len(X_test):,} samples")

    # Scale features
    print("\n[5/7] Scaling features...")
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    print("  ✅ Features scaled")

    # Train model
    print(f"\n[6/7] Training {model_type.upper()} model...")
    print("  This may take 3-5 minutes...")

    if model_type == 'gradient_boosting':
        model = GradientBoostingClassifier(
            n_estimators=200,
            max_depth=7,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42,
            verbose=1
        )
    else:  # random_forest
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

    accuracy = accuracy_score(y_test, y_pred)
    print(f"\n  📊 Overall Accuracy: {accuracy:.1%}")

    print(f"\n  📋 Classification Report:")
    print("  " + "-"*60)

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
    print("  " + "-"*60)
    cm = confusion_matrix(y_test, y_pred)
    print(f"              Predicted")
    print(f"  Actual    HOLD    SELL     BUY")
    print(f"  HOLD   {cm[0][0]:7d} {cm[0][1]:7d} {cm[0][2]:7d}")
    print(f"  SELL   {cm[1][0]:7d} {cm[1][1]:7d} {cm[1][2]:7d}")
    print(f"  BUY    {cm[2][0]:7d} {cm[2][1]:7d} {cm[2][2]:7d}")

    # Feature importance
    if hasattr(model, 'feature_importances_'):
        importance = dict(zip(feature_columns, model.feature_importances_))
        sorted_importance = sorted(importance.items(), key=lambda x: x[1], reverse=True)

        print(f"\n  🔝 Top 15 Most Important Features:")
        print("  " + "-"*60)
        for i, (feature, imp) in enumerate(sorted_importance[:15], 1):
            print(f"  {i:2d}. {feature:25s} {imp:6.2%}")

    # Save model
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    model_filename = f"model_improved_{model_type}_{timestamp}.pkl"
    model_path = f"models/{model_filename}"

    os.makedirs('models', exist_ok=True)

    model_data = {
        'model': model,
        'scaler': scaler,
        'feature_columns': feature_columns,
        'model_type': model_type,
        'spread_pips': spread_pips,
        'profit_target_atr': profit_target_atr,
        'stop_loss_atr': stop_loss_atr,
        'trained_at': datetime.utcnow().isoformat(),
        'accuracy': accuracy
    }

    with open(model_path, 'wb') as f:
        pickle.dump(model_data, f)

    print(f"\n  💾 Model saved: {model_path}")

    print("\n" + "="*70)
    print("TRAINING COMPLETE ✅")
    print("="*70)

    print(f"\n🎯 Next Steps:")
    print(f"  1. Run backtesting: python3 backtest_improved_model.py")
    print(f"  2. Verify win rate >50%, profit factor >1.5")
    print(f"  3. If profitable → Test on demo for 30 days")
    print(f"  4. If not profitable → Adjust parameters and retrain")

    return model_path


if __name__ == '__main__':
    print("\n" + "#"*70)
    print("# Improved ML Training Pipeline")
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#"*70)

    # Train Gradient Boosting (typically better)
    model_path = train_improved_model(
        model_type='gradient_boosting',
        spread_pips=3.0,
        profit_target_atr=1.0,  # More achievable target
        stop_loss_atr=1.0,  # Balanced risk/reward
    )

    print("\n" + "#"*70)
    print("# Training Pipeline Complete!")
    print(f"# Model: {model_path}")
    print("#"*70 + "\n")
