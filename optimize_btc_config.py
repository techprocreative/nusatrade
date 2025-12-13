#!/usr/bin/env python3
"""
Multi-Configuration Backtest for BTC

Test multiple configurations in parallel to find the best combination:
- Different confidence thresholds
- Different TP/SL ratios
- Different filter settings
- Ensemble predictions
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, 'backend/app/ml')

import pandas as pd
import numpy as np
from pathlib import Path
import pickle
from crypto_features import CryptoFeatureEngineer


def test_multiple_configurations():
    """Test multiple BTC configurations to find optimal settings."""

    print("=" * 70)
    print("BTC MULTI-CONFIGURATION OPTIMIZATION")
    print("=" * 70)

    # Find all BTC models
    model_dirs = [
        Path("models/btcusd/crypto-optimized"),
        Path("models/btcusd/staging"),
    ]

    all_models = []
    for model_dir in model_dirs:
        if model_dir.exists():
            all_models.extend(list(model_dir.glob("model_*.pkl")))

    if not all_models:
        print("❌ No BTC models found")
        return

    # Sort by modification time (newest first)
    all_models = sorted(all_models, key=lambda p: p.stat().st_mtime, reverse=True)

    print(f"\n📦 Found {len(all_models)} BTC models")
    for i, model_path in enumerate(all_models[:5], 1):
        print(f"  {i}. {model_path.name}")

    # Load data
    print("\n📊 Loading BTC data...")
    df = pd.read_csv('ohlcv/btc/btcusd_1h_clean.csv')

    engineer = CryptoFeatureEngineer()
    df_featured = engineer.build_crypto_features(df)
    df_clean = df_featured.dropna()

    # Test data
    split_idx = int(len(df_clean) * 0.8)
    df_test = df_clean.iloc[split_idx:].copy()

    print(f"  Test period: {df_test['timestamp'].iloc[0]} to {df_test['timestamp'].iloc[-1]}")
    print(f"  Test samples: {len(df_test):,}")

    # Test configurations
    configurations = [
        # (model_idx, confidence, description)
        (0, 0.40, "Latest model, 40% confidence"),
        (0, 0.45, "Latest model, 45% confidence"),
        (0, 0.50, "Latest model, 50% confidence"),
        (0, 0.55, "Latest model, 55% confidence"),
        (0, 0.60, "Latest model, 60% confidence"),
    ]

    # Add older models if available
    if len(all_models) > 1:
        configurations.append((1, 0.50, "Previous model, 50% confidence"))

    results = []

    print("\n" + "=" * 70)
    print("TESTING CONFIGURATIONS")
    print("=" * 70)

    for model_idx, confidence, description in configurations:
        if model_idx >= len(all_models):
            continue

        model_path = all_models[model_idx]

        print(f"\n🧪 Test: {description}")
        print(f"   Model: {model_path.name}")
        print(f"   Confidence: {confidence:.0%}")

        try:
            # Load model
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)

            model = model_data['model']
            scaler = model_data['scaler']
            feature_columns = model_data['feature_columns']
            profit_target_atr = model_data.get('profit_target_atr', 2.5)
            stop_loss_atr = model_data.get('stop_loss_atr', 1.5)

            # Make predictions
            X_test = df_test[feature_columns]
            X_scaled = scaler.transform(X_test)

            predictions = model.predict(X_scaled)
            probabilities = model.predict_proba(X_scaled)

            df_test_copy = df_test.copy()
            df_test_copy['prediction'] = predictions
            df_test_copy['confidence'] = probabilities.max(axis=1)

            # Apply confidence threshold
            df_test_copy['signal'] = 'HOLD'
            df_test_copy.loc[(df_test_copy['prediction'] == 1) & (df_test_copy['confidence'] >= confidence), 'signal'] = 'SELL'
            df_test_copy.loc[(df_test_copy['prediction'] == 2) & (df_test_copy['confidence'] >= confidence), 'signal'] = 'BUY'

            # Simulate trades
            trades = []
            balance = 10000.0
            position = None

            for idx, row in df_test_copy.iterrows():
                # Check position
                if position:
                    if position['type'] == 'BUY':
                        if row['high'] >= position['tp']:
                            pnl = position['tp'] - position['entry_price']
                            balance += pnl
                            trades.append({'pnl': pnl, 'outcome': 'WIN'})
                            position = None
                        elif row['low'] <= position['sl']:
                            pnl = position['sl'] - position['entry_price']
                            balance += pnl
                            trades.append({'pnl': pnl, 'outcome': 'LOSS'})
                            position = None
                    elif position['type'] == 'SELL':
                        if row['low'] <= position['tp']:
                            pnl = position['entry_price'] - position['tp']
                            balance += pnl
                            trades.append({'pnl': pnl, 'outcome': 'WIN'})
                            position = None
                        elif row['high'] >= position['sl']:
                            pnl = position['entry_price'] - position['sl']
                            balance += pnl
                            trades.append({'pnl': pnl, 'outcome': 'LOSS'})
                            position = None

                # New position
                if position is None and row['signal'] in ['BUY', 'SELL']:
                    atr = row['atr']
                    if pd.notna(atr):
                        entry_price = row['close']
                        if row['signal'] == 'BUY':
                            position = {
                                'type': 'BUY',
                                'entry_price': entry_price,
                                'sl': entry_price - (atr * stop_loss_atr),
                                'tp': entry_price + (atr * profit_target_atr)
                            }
                        else:
                            position = {
                                'type': 'SELL',
                                'entry_price': entry_price,
                                'sl': entry_price + (atr * stop_loss_atr),
                                'tp': entry_price - (atr * profit_target_atr)
                            }

            # Calculate metrics
            if trades:
                df_trades = pd.DataFrame(trades)
                total_trades = len(df_trades)
                winning_trades = len(df_trades[df_trades['outcome'] == 'WIN'])
                win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

                total_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
                total_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())
                profit_factor = (total_profit / total_loss) if total_loss > 0 else 0

                net_profit = balance - 10000
                roi = (net_profit / 10000) * 100

                avg_win = df_trades[df_trades['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
                avg_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].mean()) if total_trades > winning_trades else 0
                rr_ratio = avg_win / avg_loss if avg_loss > 0 else 0

                result = {
                    'description': description,
                    'model': model_path.name,
                    'confidence': confidence,
                    'tp_sl': f"{profit_target_atr}:{stop_loss_atr}",
                    'trades': total_trades,
                    'win_rate': win_rate,
                    'profit_factor': profit_factor,
                    'roi': roi,
                    'net_profit': net_profit,
                    'rr_ratio': rr_ratio,
                }

                results.append(result)

                # Print summary
                status = "✅" if profit_factor > 1.3 and win_rate > 50 else "⚠️" if profit_factor > 1.0 else "❌"
                print(f"   {status} Trades: {total_trades} | WR: {win_rate:.1f}% | PF: {profit_factor:.2f} | ROI: {roi:+.1f}%")
            else:
                print(f"   ❌ No trades generated")

        except Exception as e:
            print(f"   ❌ Error: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("OPTIMIZATION RESULTS SUMMARY")
    print("=" * 70)

    if results:
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values('profit_factor', ascending=False)

        print(f"\n📊 Top 5 Configurations by Profit Factor:")
        print("=" * 70)

        for i, row in df_results.head(5).iterrows():
            status = "✅ PROFITABLE" if row['profit_factor'] > 1.3 and row['win_rate'] > 50 else \
                     "⚠️ MARGINAL" if row['profit_factor'] > 1.0 else \
                     "❌ UNPROFITABLE"

            print(f"\n{status}")
            print(f"  Config: {row['description']}")
            print(f"  TP/SL: {row['tp_sl']}")
            print(f"  Confidence: {row['confidence']:.0%}")
            print(f"  Trades: {row['trades']}")
            print(f"  Win Rate: {row['win_rate']:.1f}%")
            print(f"  Profit Factor: {row['profit_factor']:.2f}")
            print(f"  ROI: {row['roi']:+.1f}%")
            print(f"  R:R Ratio: 1:{row['rr_ratio']:.2f}")

        # Find best configuration
        best = df_results.iloc[0]

        print("\n" + "=" * 70)
        print("🏆 BEST CONFIGURATION")
        print("=" * 70)
        print(f"  {best['description']}")
        print(f"  Model: {best['model']}")
        print(f"  Confidence: {best['confidence']:.0%}")
        print(f"  TP/SL: {best['tp_sl']}")
        print(f"  Win Rate: {best['win_rate']:.1f}%")
        print(f"  Profit Factor: {best['profit_factor']:.2f}")
        print(f"  ROI: {best['roi']:+.1f}%")

        if best['profit_factor'] > 1.3 and best['win_rate'] > 50:
            print("\n  ✅ THIS CONFIGURATION IS PROFITABLE!")
            print("  🎯 Ready for demo testing")
        elif best['profit_factor'] > 1.0:
            print("\n  ⚠️ Marginal performance - needs more optimization")
        else:
            print("\n  ❌ Still not profitable - consider different approach")

    else:
        print("\n❌ No valid results generated")


if __name__ == '__main__':
    test_multiple_configurations()
