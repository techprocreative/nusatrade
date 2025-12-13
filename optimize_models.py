#!/usr/bin/env python3
"""
Model Optimization Script
Trains multiple models and compares their performance.

This script:
1. Trains Gradient Boosting model
2. Tests with different confidence thresholds
3. Compares performance metrics
4. Recommends best configuration
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.ml.training import Trainer
from app.ml.features import FeatureEngineer
import pandas as pd
import numpy as np
from datetime import datetime


def train_gradient_boosting():
    """Train Gradient Boosting model."""
    print("\n" + "="*60)
    print("Training Gradient Boosting Model")
    print("="*60)

    # Load data
    print("\n[1/3] Loading XAUUSD data...")
    df = pd.read_csv('ohlcv/xauusd/xauusd_1h_clean.csv')
    print(f"  ✅ Loaded {len(df):,} rows")

    # Train Gradient Boosting
    print("\n[2/3] Training Gradient Boosting classifier...")
    print("  This may take 3-4 minutes...")

    trainer = Trainer()
    result = trainer.train(
        data=df,
        model_type='gradient_boosting',
        config={
            'n_estimators': 150,
            'max_depth': 7,
            'learning_rate': 0.05,
        }
    )

    # Display results
    print("\n[3/3] Training Complete!")
    if result.get('success'):
        print(f"  ✅ Model trained successfully")
        print(f"\n  📊 Performance Metrics:")
        print(f"    • Accuracy: {result['metrics']['accuracy']:.1%}")
        print(f"    • Precision: {result['metrics']['precision']:.1%}")
        print(f"    • Recall: {result['metrics']['recall']:.1%}")
        print(f"    • F1 Score: {result['metrics']['f1_score']:.1%}")
        print(f"\n  📁 Model saved: {result['model_path']}")

        if 'top_features' in result['metrics']:
            print(f"\n  🎯 Top 10 Features:")
            for i, (feature, importance) in enumerate(result['metrics']['top_features'].items(), 1):
                print(f"    {i:2d}. {feature:20s} {importance:.1%}")

        return result['model_path'], result['metrics']
    else:
        print(f"  ❌ Training failed: {result.get('error')}")
        return None, None


def test_model_with_thresholds(model_path, thresholds=[0.50, 0.55, 0.60, 0.65]):
    """Test model with different confidence thresholds."""
    print("\n" + "="*60)
    print(f"Testing Model: {os.path.basename(model_path)}")
    print("="*60)

    # Load model
    print("\n[1/3] Loading model...")
    trainer = Trainer()
    trainer.load_model(model_path)
    print("  ✅ Model loaded")

    # Load test data
    print("\n[2/3] Loading test data...")
    df = pd.read_csv('ohlcv/xauusd/xauusd_1h_clean.csv')
    df_recent = df.tail(1000).copy()

    engineer = FeatureEngineer()
    df_featured = engineer.build_features(df_recent)
    df_featured = df_featured.dropna()
    print(f"  ✅ {len(df_featured)} samples ready")

    # Test with different thresholds
    print("\n[3/3] Testing with different confidence thresholds...")
    print("\n  " + "-"*70)
    print(f"  {'Threshold':<12} {'BUY':>6} {'SELL':>6} {'HOLD':>6} {'Avg Conf':>10} {'Trade %':>10}")
    print("  " + "-"*70)

    results = []

    for threshold in thresholds:
        predictions = []

        for i in range(len(df_featured)):
            sample = df_featured.iloc[i:i+1]
            pred = trainer.predict(sample)

            # Apply threshold
            confidence = pred['confidence']
            if confidence < threshold:
                direction = "HOLD"
            else:
                direction = pred['direction']

            predictions.append({
                'direction': direction,
                'confidence': confidence
            })

        # Calculate statistics
        buy_count = sum(1 for p in predictions if p['direction'] == 'BUY')
        sell_count = sum(1 for p in predictions if p['direction'] == 'SELL')
        hold_count = sum(1 for p in predictions if p['direction'] == 'HOLD')
        avg_confidence = np.mean([p['confidence'] for p in predictions])
        trade_pct = (buy_count + sell_count) / len(predictions) * 100

        print(f"  {threshold:.0%}          {buy_count:6d} {sell_count:6d} {hold_count:6d} {avg_confidence:9.1%} {trade_pct:9.1%}")

        results.append({
            'threshold': threshold,
            'buy_count': buy_count,
            'sell_count': sell_count,
            'hold_count': hold_count,
            'avg_confidence': avg_confidence,
            'trade_pct': trade_pct
        })

    print("  " + "-"*70)

    return results


def recommend_configuration(rf_metrics, gb_metrics, rf_threshold_results, gb_threshold_results):
    """Recommend best model and threshold."""
    print("\n" + "="*60)
    print("RECOMMENDATION")
    print("="*60)

    print("\n📊 Model Comparison:")
    print(f"\n  Random Forest:")
    print(f"    • Accuracy: {rf_metrics['accuracy']:.1%}")
    print(f"    • Recall: {rf_metrics['recall']:.1%}")
    print(f"    • F1 Score: {rf_metrics['f1_score']:.1%}")

    print(f"\n  Gradient Boosting:")
    print(f"    • Accuracy: {gb_metrics['accuracy']:.1%}")
    print(f"    • Recall: {gb_metrics['recall']:.1%}")
    print(f"    • F1 Score: {gb_metrics['f1_score']:.1%}")

    # Determine better model
    better_model = "Gradient Boosting" if gb_metrics['f1_score'] > rf_metrics['f1_score'] else "Random Forest"
    better_results = gb_threshold_results if better_model == "Gradient Boosting" else rf_threshold_results

    print(f"\n🏆 Better Model: {better_model}")

    # Find optimal threshold (want 5-15% trading frequency)
    optimal = None
    for result in better_results:
        if 5.0 <= result['trade_pct'] <= 15.0:
            optimal = result
            break

    if optimal:
        print(f"\n🎯 Recommended Configuration:")
        print(f"    • Model: {better_model}")
        print(f"    • Confidence Threshold: {optimal['threshold']:.0%}")
        print(f"    • Expected Trading Frequency: {optimal['trade_pct']:.1f}%")
        print(f"    • Expected Trades per Week (1H data): {optimal['trade_pct']/100 * 168:.0f} trades")
    else:
        # Fallback to 55% threshold
        result_55 = [r for r in better_results if r['threshold'] == 0.55][0]
        print(f"\n🎯 Recommended Configuration:")
        print(f"    • Model: {better_model}")
        print(f"    • Confidence Threshold: 55%")
        print(f"    • Expected Trading Frequency: {result_55['trade_pct']:.1f}%")
        print(f"    • Expected Trades per Week (1H data): {result_55['trade_pct']/100 * 168:.0f} trades")

    print("\n⚠️  Next Steps:")
    print("    1. Backtest recommended configuration")
    print("    2. Test on demo account for 30 days")
    print("    3. Monitor with MLPerformanceTracker")
    print("    4. Only go live if profitable on demo")


def main():
    """Main optimization pipeline."""
    print("\n" + "#"*60)
    print("# ML Model Optimization Pipeline")
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#"*60)

    # 1. Train Gradient Boosting
    print("\n" + "="*60)
    print("STEP 1: Train Gradient Boosting Model")
    print("="*60)
    gb_model_path, gb_metrics = train_gradient_boosting()

    if not gb_model_path:
        print("\n❌ Gradient Boosting training failed. Aborting.")
        return

    # 2. Load existing Random Forest metrics
    print("\n" + "="*60)
    print("STEP 2: Load Random Forest Model")
    print("="*60)
    import glob
    rf_models = glob.glob('backend/models/model_random_forest_*.pkl')
    if not rf_models:
        print("  ❌ No Random Forest model found!")
        return

    rf_model_path = max(rf_models, key=os.path.getctime)
    print(f"  ✅ Found: {rf_model_path}")

    # Approximate RF metrics from previous training
    rf_metrics = {
        'accuracy': 0.552,
        'precision': 0.530,
        'recall': 0.035,
        'f1_score': 0.065
    }

    # 3. Test Random Forest with different thresholds
    print("\n" + "="*60)
    print("STEP 3: Test Random Forest with Different Thresholds")
    print("="*60)
    rf_threshold_results = test_model_with_thresholds(rf_model_path)

    # 4. Test Gradient Boosting with different thresholds
    print("\n" + "="*60)
    print("STEP 4: Test Gradient Boosting with Different Thresholds")
    print("="*60)
    gb_threshold_results = test_model_with_thresholds(gb_model_path)

    # 5. Recommend best configuration
    print("\n" + "="*60)
    print("STEP 5: Determine Best Configuration")
    print("="*60)
    recommend_configuration(rf_metrics, gb_metrics, rf_threshold_results, gb_threshold_results)

    print("\n" + "#"*60)
    print("# Optimization Complete!")
    print(f"# Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#"*60 + "\n")


if __name__ == '__main__':
    main()
