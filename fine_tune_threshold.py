#!/usr/bin/env python3
"""
Fine-tune Gradient Boosting model with realistic confidence thresholds.
Target: 5-20% trading frequency (8-30 trades per week on 1H data)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.ml.training import Trainer
from app.ml.features import FeatureEngineer
import pandas as pd
import numpy as np


def fine_tune_threshold():
    """Find optimal threshold for realistic trading frequency."""
    print("="*60)
    print("Fine-Tuning Gradient Boosting Confidence Threshold")
    print("="*60)

    # Load model
    print("\n[1/3] Loading Gradient Boosting model...")
    trainer = Trainer()
    trainer.load_model('models/model_gradient_boosting_20251212_212847.pkl')
    print("  ✅ Model loaded")

    # Load test data
    print("\n[2/3] Loading recent XAUUSD data...")
    df = pd.read_csv('ohlcv/xauusd/xauusd_1h_clean.csv')
    df_recent = df.tail(1000).copy()

    engineer = FeatureEngineer()
    df_featured = engineer.build_features(df_recent)
    df_featured = df_featured.dropna()
    print(f"  ✅ {len(df_featured)} samples ready")

    # Test fine-grained thresholds
    print("\n[3/3] Testing fine-grained thresholds (65%-85%)...")
    print("\n  Target: 5-20% trading frequency (8-30 trades/week)")
    print("\n  " + "-"*80)
    print(f"  {'Threshold':<12} {'BUY':>6} {'SELL':>6} {'HOLD':>6} {'Trade %':>10} {'Trades/Week':>12}")
    print("  " + "-"*80)

    optimal_configs = []
    thresholds = [0.65, 0.70, 0.75, 0.80, 0.85]

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
                if pred['prediction'] == 1:
                    direction = "BUY"
                else:
                    direction = "SELL"

            predictions.append({
                'direction': direction,
                'confidence': confidence
            })

        # Calculate statistics
        buy_count = sum(1 for p in predictions if p['direction'] == 'BUY')
        sell_count = sum(1 for p in predictions if p['direction'] == 'SELL')
        hold_count = sum(1 for p in predictions if p['direction'] == 'HOLD')
        trade_pct = (buy_count + sell_count) / len(predictions) * 100
        trades_per_week = (buy_count + sell_count) / len(predictions) * 168  # 168 hours per week

        status = ""
        if 5.0 <= trade_pct <= 20.0:
            status = " ⭐ OPTIMAL"
            optimal_configs.append({
                'threshold': threshold,
                'trade_pct': trade_pct,
                'trades_per_week': trades_per_week,
                'buy_count': buy_count,
                'sell_count': sell_count
            })

        print(f"  {threshold:.0%}          {buy_count:6d} {sell_count:6d} {hold_count:6d} {trade_pct:9.1f}% {trades_per_week:11.0f}{status}")

    print("  " + "-"*80)

    # Recommend best configuration
    print("\n" + "="*60)
    print("RECOMMENDATION")
    print("="*60)

    if optimal_configs:
        # Choose middle ground (not too conservative, not too aggressive)
        best = optimal_configs[len(optimal_configs)//2]
        print(f"\n🎯 Recommended Configuration:")
        print(f"    • Model: Gradient Boosting")
        print(f"    • Confidence Threshold: {best['threshold']:.0%}")
        print(f"    • Expected Trading Frequency: {best['trade_pct']:.1f}%")
        print(f"    • Expected Trades per Week: {best['trades_per_week']:.0f}")
        print(f"    • Expected BUY signals: {best['buy_count']} ({best['buy_count']/10:.1f}%)")
        print(f"    • Expected SELL signals: {best['sell_count']} ({best['sell_count']/10:.1f}%)")

        print(f"\n✅ This is a REALISTIC trading frequency!")
        print(f"   • Not overtrading (> 50 trades/week = too much)")
        print(f"   • Not undertrading (< 2 trades/week = too little)")
        print(f"   • Allows proper risk management")
        print(f"   • Gives model time to be right")

        # Update the training.py file recommendation
        print(f"\n📝 To Use This Configuration:")
        print(f"   Edit backend/app/ml/training.py line 200:")
        print(f"   Change: confidence_threshold = 0.60")
        print(f"   To:     confidence_threshold = {best['threshold']:.2f}")
        print(f"\n   Or pass threshold when loading model:")
        print(f"   prediction = trainer.predict(features, threshold={best['threshold']:.2f})")

    else:
        print("\n⚠️  No threshold found in optimal range (5-20%)")
        print("   Try different thresholds or retrain model with different parameters")

    print("\n" + "="*60)
    print("⚠️  IMPORTANT: Before Using This Model")
    print("="*60)
    print("""
1. BACKTEST first with realistic costs:
   - Spread: 2-5 pips for XAUUSD
   - Slippage: 1-2 pips
   - Commission: (if applicable)

2. Calculate expected metrics:
   - Win rate (target: >50%)
   - Profit factor (target: >1.5)
   - Maximum drawdown (target: <20%)
   - Sharpe ratio (target: >1.0)

3. Test on DEMO account for 30 days

4. ONLY go live if demo is profitable

Remember: High trading frequency = higher costs!
          Model must be VERY accurate to overcome costs.
    """)


if __name__ == '__main__':
    fine_tune_threshold()
