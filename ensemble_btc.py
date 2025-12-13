#!/usr/bin/env python3
"""
Ensemble BTC Model - Combine Multiple Models for Better Predictions

Combines predictions from multiple models using voting/averaging to improve reliability.
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


def backtest_ensemble(
    confidence_threshold=0.55,
    ensemble_method='weighted_average',  # 'voting', 'weighted_average'
):
    """
    Backtest ensemble of multiple BTC models.

    Args:
        confidence_threshold: Minimum confidence for trades
        ensemble_method: How to combine predictions
    """

    print("=" * 70)
    print("BTC ENSEMBLE MODEL BACKTEST")
    print("=" * 70)
    print(f"\nEnsemble Method: {ensemble_method}")
    print(f"Confidence Threshold: {confidence_threshold:.0%}")

    # Find all models
    models_to_ensemble = []

    # Try crypto-optimized models first
    crypto_dir = Path("models/btcusd/crypto-optimized")
    if crypto_dir.exists():
        crypto_models = sorted(
            list(crypto_dir.glob("model_crypto_*.pkl")),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:2]  # Use top 2 latest
        models_to_ensemble.extend(crypto_models)

    # Also add standard model for diversity
    staging_dir = Path("models/btcusd/staging")
    if staging_dir.exists():
        standard_models = sorted(
            list(staging_dir.glob("model_xgboost_*.pkl")),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )[:1]  # Use 1 standard model
        models_to_ensemble.extend(standard_models)

    if len(models_to_ensemble) < 2:
        print("❌ Need at least 2 models for ensemble")
        return

    print(f"\n📦 Ensemble Members ({len(models_to_ensemble)} models):")
    for i, model_path in enumerate(models_to_ensemble, 1):
        print(f"  {i}. {model_path.name}")

    # Load data
    print("\n📊 Loading BTC data...")
    df = pd.read_csv('ohlcv/btc/btcusd_1h_clean.csv')

    engineer = CryptoFeatureEngineer()
    df_featured = engineer.build_crypto_features(df)
    df_clean = df_featured.dropna()

    split_idx = int(len(df_clean) * 0.8)
    df_test = df_clean.iloc[split_idx:].copy()

    print(f"  Test period: {df_test['timestamp'].iloc[0]} to {df_test['timestamp'].iloc[-1]}")
    print(f"  Test samples: {len(df_test):,}")

    # Load all models
    print("\n🤖 Loading ensemble models...")
    loaded_models = []

    for model_path in models_to_ensemble:
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)

            loaded_models.append({
                'model': model_data['model'],
                'scaler': model_data['scaler'],
                'features': model_data['feature_columns'],
                'tp_atr': model_data.get('profit_target_atr', 2.5),
                'sl_atr': model_data.get('stop_loss_atr', 1.5),
                'name': model_path.name,
            })
            print(f"  ✅ Loaded {model_path.name}")
        except Exception as e:
            print(f"  ❌ Failed to load {model_path.name}: {e}")

    if len(loaded_models) < 2:
        print("\n❌ Not enough models loaded")
        return

    # Generate ensemble predictions
    print("\n🔮 Generating ensemble predictions...")

    all_predictions = []
    all_probabilities = []

    for model_info in loaded_models:
        X_test = df_test[model_info['features']]
        X_scaled = model_info['scaler'].transform(X_test)

        pred = model_info['model'].predict(X_scaled)
        proba = model_info['model'].predict_proba(X_scaled)

        all_predictions.append(pred)
        all_probabilities.append(proba)

    # Combine predictions
    if ensemble_method == 'voting':
        # Majority voting
        pred_array = np.array(all_predictions)
        ensemble_pred = np.apply_along_axis(
            lambda x: np.bincount(x).argmax(),
            axis=0,
            arr=pred_array
        )

        # Average probabilities
        ensemble_proba = np.mean(all_probabilities, axis=0)

    elif ensemble_method == 'weighted_average':
        # Weight newer models more
        weights = np.array([1.0 / (i + 1) for i in range(len(loaded_models))])
        weights = weights / weights.sum()

        # Weighted average of probabilities
        ensemble_proba = np.average(all_probabilities, axis=0, weights=weights)
        ensemble_pred = np.argmax(ensemble_proba, axis=1)

    df_test['prediction'] = ensemble_pred
    df_test['confidence'] = ensemble_proba.max(axis=1)

    # Apply confidence threshold
    df_test['signal'] = 'HOLD'
    df_test.loc[(df_test['prediction'] == 1) & (df_test['confidence'] >= confidence_threshold), 'signal'] = 'SELL'
    df_test.loc[(df_test['prediction'] == 2) & (df_test['confidence'] >= confidence_threshold), 'signal'] = 'BUY'

    signal_counts = df_test['signal'].value_counts()
    print(f"\n   Signal Distribution:")
    print(f"   • HOLD: {signal_counts.get('HOLD', 0):,} ({signal_counts.get('HOLD', 0)/len(df_test):.1%})")
    print(f"   • SELL: {signal_counts.get('SELL', 0):,} ({signal_counts.get('SELL', 0)/len(df_test):.1%})")
    print(f"   • BUY:  {signal_counts.get('BUY', 0):,} ({signal_counts.get('BUY', 0)/len(df_test):.1%})")

    # Simulate trades with best TP/SL from ensemble
    print("\n💹 Simulating trades...")

    trades = []
    balance = 10000.0
    position = None

    # Use aggressive TP/SL (3.0:1.5)
    profit_target_atr = 3.0
    stop_loss_atr = 1.5

    for idx, row in df_test.iterrows():
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
    print("\n" + "=" * 70)
    print("ENSEMBLE BACKTEST RESULTS")
    print("=" * 70)

    if not trades:
        print("\n⚠️  NO TRADES GENERATED")
        return

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

    print(f"\n📊 Trading Performance:")
    print(f"   Initial Balance: $10,000.00")
    print(f"   Final Balance:   ${balance:,.2f}")
    print(f"   Net Profit:      ${net_profit:,.2f}")
    print(f"   ROI:             {roi:.2f}%")

    print(f"\n🎯 Trade Statistics:")
    print(f"   Total Trades:    {total_trades}")
    print(f"   Winning Trades:  {winning_trades}")
    print(f"   Win Rate:        {win_rate:.1f}%")
    print(f"   Profit Factor:   {profit_factor:.2f}")

    print(f"\n💰 Trade Metrics:")
    print(f"   Avg Win:         ${avg_win:,.2f}")
    print(f"   Avg Loss:        ${avg_loss:,.2f}")
    print(f"   Risk/Reward:     1:{rr_ratio:.2f}")

    print("\n" + "=" * 70)
    print("PROFITABILITY ASSESSMENT")
    print("=" * 70)

    is_profitable = profit_factor > 1.3 and win_rate > 50

    if is_profitable:
        print("\n✅ ENSEMBLE MODEL IS PROFITABLE!")
        print(f"   ✓ Profit Factor: {profit_factor:.2f} > 1.3")
        print(f"   ✓ Win Rate: {win_rate:.1f}% > 50%")
        print("\n🎯 Ready for DEMO testing!")
    elif profit_factor > 1.0:
        print("\n⚠️ MARGINAL - Close to profitable")
        print(f"   • Profit Factor: {profit_factor:.2f}")
        print(f"   • Win Rate: {win_rate:.1f}%")
        print(f"   • ROI: {roi:+.1f}%")
        print("\n   Consider: Lower confidence or add trailing stops")
    else:
        print("\n❌ Still not profitable")
        print(f"   • Profit Factor: {profit_factor:.2f} < 1.0")

    return {
        'trades': total_trades,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'roi': roi,
    }


if __name__ == '__main__':
    # Test both ensemble methods
    print("\n" + "#" * 70)
    print("# BTC Ensemble Optimization")
    print("#" * 70)

    print("\n### TEST 1: Weighted Average Ensemble ###")
    result1 = backtest_ensemble(
        confidence_threshold=0.55,
        ensemble_method='weighted_average'
    )

    print("\n\n### TEST 2: Voting Ensemble ###")
    result2 = backtest_ensemble(
        confidence_threshold=0.55,
        ensemble_method='voting'
    )

    print("\n\n### TEST 3: Lower Confidence (50%) ###")
    result3 = backtest_ensemble(
        confidence_threshold=0.50,
        ensemble_method='weighted_average'
    )

    print("\n" + "#" * 70)
    print("# Ensemble Testing Complete")
    print("#" * 70 + "\n")
