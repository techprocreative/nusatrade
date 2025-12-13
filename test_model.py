#!/usr/bin/env python3
"""
Quick Model Testing Script
Tests the trained XAUUSD model and shows how to use it for predictions.

Usage:
    cd backend
    ../venv/bin/python3 ../test_model.py
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.ml.training import Trainer
import pandas as pd
import numpy as np


def test_model_predictions():
    """Test model with recent data."""
    print("="*60)
    print("XAUUSD Model Prediction Test")
    print("="*60)

    # 1. Load the trained model
    print("\n[1/5] Loading trained model...")
    trainer = Trainer()

    # Find the most recent model
    import glob
    models = glob.glob('backend/models/model_random_forest_*.pkl')
    if not models:
        print("  ❌ No trained model found!")
        print("  Run training first:")
        print("  cd backend && venv/bin/python3 -c 'from app.ml.training import Trainer; ...'")
        sys.exit(1)

    latest_model = max(models, key=os.path.getctime)
    print(f"  ✅ Loading: {latest_model}")
    trainer.load_model(latest_model)

    # 2. Load test data
    print("\n[2/5] Loading recent XAUUSD data...")
    df = pd.read_csv('ohlcv/xauusd/xauusd_1h_clean.csv')
    print(f"  ✅ Loaded {len(df):,} rows")

    # Take last 1000 rows (recent data)
    df_recent = df.tail(1000).copy()
    print(f"  Using last 1000 rows for testing")
    print(f"  Date range: {df_recent['timestamp'].min()} to {df_recent['timestamp'].max()}")

    # 3. Build features
    print("\n[3/5] Building features...")
    from app.ml.features import FeatureEngineer
    engineer = FeatureEngineer()
    df_featured = engineer.build_features(df_recent)
    df_featured = df_featured.dropna()
    print(f"  ✅ Features built: {len(df_featured)} samples")

    # 4. Make predictions
    print("\n[4/5] Making predictions on recent data...")
    predictions = []

    for i in range(min(10, len(df_featured))):
        sample = df_featured.iloc[i:i+1]
        pred = trainer.predict(sample)
        predictions.append({
            'timestamp': sample['timestamp'].values[0],
            'close': sample['close'].values[0],
            'direction': pred['direction'],
            'confidence': pred['confidence'],
        })

    print(f"\n  📊 Last 10 Predictions:")
    print(f"  {'Timestamp':<20} {'Price':>10} {'Direction':>10} {'Confidence':>12}")
    print(f"  {'-'*60}")
    for p in predictions:
        conf_str = f"{p['confidence']:.1%}"
        print(f"  {p['timestamp']:<20} ${p['close']:>9.2f} {p['direction']:>10} {conf_str:>12}")

    # 5. Statistics
    print(f"\n[5/5] Prediction Statistics:")
    buy_count = sum(1 for p in predictions if p['direction'] == 'BUY')
    sell_count = sum(1 for p in predictions if p['direction'] == 'SELL')
    hold_count = sum(1 for p in predictions if p['direction'] == 'HOLD')
    avg_confidence = np.mean([p['confidence'] for p in predictions])

    print(f"  • BUY signals: {buy_count}")
    print(f"  • SELL signals: {sell_count}")
    print(f"  • HOLD signals: {hold_count}")
    print(f"  • Average confidence: {avg_confidence:.1%}")

    if hold_count > buy_count + sell_count:
        print(f"\n  ⚠️  Model is VERY conservative (mostly HOLD signals)")
        print(f"  This is expected with 60% confidence threshold")
        print(f"  Consider lowering threshold or improving model")

    print("\n" + "="*60)
    print("✅ Model test complete!")
    print("="*60)
    print("\nNext steps:")
    print("  1. Review predictions above")
    print("  2. Check if HOLD signal is working (confidence < 60%)")
    print("  3. If too many HOLD signals, consider:")
    print("     - Training with more balanced data")
    print("     - Lowering confidence threshold")
    print("     - Using Gradient Boosting instead")
    print("\nSee ML_TRAINING_RESULTS.md for detailed analysis")
    print("="*60)


def check_class_distribution():
    """Check if training data has class imbalance."""
    print("\n" + "="*60)
    print("Checking Class Distribution (Target Balance)")
    print("="*60)

    df = pd.read_csv('ohlcv/xauusd/xauusd_1h_clean.csv')

    # Calculate target (same as training)
    df['future_return'] = df['close'].shift(-5) / df['close'] - 1
    df['target'] = (df['future_return'] > 0.0005).astype(int)

    distribution = df['target'].value_counts(normalize=True)

    print(f"\nTarget Distribution:")
    print(f"  • Class 0 (DOWN/SELL): {distribution.get(0, 0):.1%}")
    print(f"  • Class 1 (UP/BUY): {distribution.get(1, 0):.1%}")

    imbalance_ratio = max(distribution.values) / min(distribution.values)

    if imbalance_ratio > 1.5:
        print(f"\n  ⚠️  IMBALANCED DATA (ratio: {imbalance_ratio:.2f}:1)")
        print(f"  This explains the low recall!")
        print(f"\n  Recommendation:")
        print(f"  1. Retrain with class_weight='balanced'")
        print(f"  2. Or adjust threshold from 0.05% to different value")
        print(f"  3. Or use SMOTE for oversampling minority class")
    else:
        print(f"\n  ✅ Data is balanced (ratio: {imbalance_ratio:.2f}:1)")

    print("="*60)


if __name__ == '__main__':
    print("\n" + "#"*60)
    print("# XAUUSD ML Model Testing & Diagnostics")
    print("#"*60)

    # Test model predictions
    test_model_predictions()

    # Check class distribution
    check_class_distribution()

    print("\n" + "#"*60)
    print("# Testing Complete!")
    print("#"*60 + "\n")
