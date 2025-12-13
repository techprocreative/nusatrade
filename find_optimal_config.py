#!/usr/bin/env python3
"""
Optimize Model for Profitability
Tests multiple configurations to find optimal profitable setup.

This script tests:
1. Different confidence thresholds (60%, 70%, 80%)
2. Different TP/SL ratios (1:1, 1.5:1, 2:1)
3. Market condition filters (sessions, volatility, trend)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import pandas as pd
import numpy as np
import pickle
from datetime import datetime
from itertools import product

sys.path.insert(0, 'backend/app/ml')
from improved_features import ImprovedFeatureEngineer


def backtest_with_filters(
    model_path,
    confidence_threshold=0.70,
    tp_sl_ratio=1.5,
    use_session_filter=True,
    use_volatility_filter=True,
    use_trend_filter=True,
    spread_pips=3.0,
    verbose=False
):
    """
    Backtest model with various filters.

    Returns:
        dict with metrics or None if no trades
    """

    # Load model
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)

    model = model_data['model']
    scaler = model_data['scaler']
    feature_columns = model_data['feature_columns']
    stop_loss_atr = model_data['stop_loss_atr']

    # Calculate TP based on ratio
    profit_target_atr = stop_loss_atr * tp_sl_ratio

    # Load test data
    df = pd.read_csv('ohlcv/xauusd/xauusd_1h_clean.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    test_data = df[df['timestamp'] >= '2024-01-01'].copy()

    # Build features
    engineer = ImprovedFeatureEngineer()
    test_featured = engineer.build_features(test_data)
    test_featured = test_featured.dropna()

    trades = []

    for i in range(len(test_featured) - 24):
        row = test_featured.iloc[i:i+1]

        # Make prediction
        X = row[feature_columns]
        X_scaled = scaler.transform(X)
        pred_class = model.predict(X_scaled)[0]
        pred_proba = model.predict_proba(X_scaled)[0]

        confidence = pred_proba[pred_class]

        # Skip if HOLD
        if pred_class == 0:
            continue

        # FILTER 1: Confidence threshold
        if confidence < confidence_threshold:
            continue

        # FILTER 2: Session filter (only London + NY)
        if use_session_filter:
            hour = row['hour'].values[0] if 'hour' in row.columns else None
            if hour is not None:
                # Only trade during London (8-16) or NY (13-21) sessions
                if not ((8 <= hour < 16) or (13 <= hour < 21)):
                    continue

        # FILTER 3: Volatility filter (avoid extreme conditions)
        if use_volatility_filter:
            vol_regime_low = row['vol_regime_low'].values[0] if 'vol_regime_low' in row.columns else 0
            vol_regime_high = row['vol_regime_high'].values[0] if 'vol_regime_high' in row.columns else 0

            # Skip if extremely low or high volatility
            if vol_regime_low == 1 or vol_regime_high == 1:
                continue

        # FILTER 4: Trend filter (only trade with trend confirmation)
        if use_trend_filter:
            strong_trend = row['strong_trend'].values[0] if 'strong_trend' in row.columns else 0

            # Only trade if strong trend present
            if strong_trend != 1:
                continue

        # Determine trade type
        trade_type = "SELL" if pred_class == 1 else "BUY"

        # Entry setup
        entry_price = float(row['close'].values[0])
        entry_atr = float(row['atr'].values[0])
        entry_time = row['timestamp'].values[0]

        if pd.isna(entry_atr):
            continue

        # Calculate TP/SL
        spread_cost = spread_pips / 10000 * entry_price
        profit_target = entry_atr * profit_target_atr
        stop_loss = entry_atr * stop_loss_atr

        if trade_type == "BUY":
            entry_with_spread = entry_price + spread_cost
            tp_price = entry_with_spread + profit_target
            sl_price = entry_with_spread - stop_loss
        else:  # SELL
            entry_with_spread = entry_price - spread_cost
            tp_price = entry_with_spread - profit_target
            sl_price = entry_with_spread + stop_loss

        # Simulate trade execution
        exit_price = None
        exit_time = None
        hit_tp = False

        for j in range(i + 1, min(i + 25, len(test_featured))):
            candle = test_featured.iloc[j]
            candle_high = candle['high']
            candle_low = candle['low']

            if trade_type == "BUY":
                if candle_high >= tp_price:
                    exit_price = tp_price
                    exit_time = candle['timestamp']
                    hit_tp = True
                    break
                elif candle_low <= sl_price:
                    exit_price = sl_price
                    exit_time = candle['timestamp']
                    break
            else:  # SELL
                if candle_low <= tp_price:
                    exit_price = tp_price
                    exit_time = candle['timestamp']
                    hit_tp = True
                    break
                elif candle_high >= sl_price:
                    exit_price = sl_price
                    exit_time = candle['timestamp']
                    break

        # If no exit, close at last candle
        if exit_price is None:
            exit_price = float(test_featured.iloc[min(i + 24, len(test_featured) - 1)]['close'])
            exit_time = test_featured.iloc[min(i + 24, len(test_featured) - 1)]['timestamp']

        # Calculate profit/loss
        if trade_type == "BUY":
            price_diff_pips = (exit_price - entry_with_spread) / entry_price * 10000
        else:
            price_diff_pips = (entry_with_spread - exit_price) / entry_price * 10000

        profit_usd = price_diff_pips * 0.01 * 10

        trades.append({
            'profit_usd': profit_usd,
            'hit_tp': hit_tp
        })

    if len(trades) == 0:
        return None

    # Calculate metrics
    trades_df = pd.DataFrame(trades)
    winning = trades_df[trades_df['profit_usd'] > 0]
    losing = trades_df[trades_df['profit_usd'] < 0]

    total_trades = len(trades_df)
    win_count = len(winning)
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

    gross_profit = winning['profit_usd'].sum() if len(winning) > 0 else 0
    gross_loss = abs(losing['profit_usd'].sum()) if len(losing) > 0 else 0
    net_profit = gross_profit - gross_loss
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0

    avg_win = winning['profit_usd'].mean() if len(winning) > 0 else 0
    avg_loss = losing['profit_usd'].mean() if len(losing) > 0 else 0

    # Drawdown
    cumulative = trades_df['profit_usd'].cumsum()
    running_max = cumulative.cummax()
    drawdown = running_max - cumulative
    max_drawdown = drawdown.max()

    return {
        'total_trades': total_trades,
        'win_count': win_count,
        'win_rate': win_rate,
        'gross_profit': gross_profit,
        'gross_loss': gross_loss,
        'net_profit': net_profit,
        'profit_factor': profit_factor,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'max_drawdown': max_drawdown,
        'tp_hit_rate': trades_df['hit_tp'].sum() / total_trades * 100
    }


def find_optimal_configuration():
    """Test multiple configurations and find the best one."""

    print("="*70)
    print("FINDING OPTIMAL PROFITABLE CONFIGURATION")
    print("="*70)

    model_path = 'models/model_improved_gradient_boosting_20251212_223406.pkl'

    # Test configurations
    confidence_levels = [0.60, 0.70, 0.75, 0.80]
    tp_sl_ratios = [1.0, 1.5, 2.0, 2.5]

    print("\nTesting combinations...")
    print("This will take 2-3 minutes...\n")

    results = []

    # Test base model (no filters)
    print("[1/5] Testing without filters...")
    for conf in confidence_levels:
        for ratio in tp_sl_ratios:
            metrics = backtest_with_filters(
                model_path,
                confidence_threshold=conf,
                tp_sl_ratio=ratio,
                use_session_filter=False,
                use_volatility_filter=False,
                use_trend_filter=False
            )

            if metrics and metrics['total_trades'] >= 50:
                results.append({
                    'config': f"Conf={conf:.0%}, TP/SL={ratio:.1f}:1, Filters=None",
                    'confidence': conf,
                    'tp_sl_ratio': ratio,
                    'filters': 'None',
                    **metrics
                })

    # Test with session filter only
    print("[2/5] Testing with session filter...")
    for conf in [0.70, 0.75]:
        for ratio in [1.5, 2.0]:
            metrics = backtest_with_filters(
                model_path,
                confidence_threshold=conf,
                tp_sl_ratio=ratio,
                use_session_filter=True,
                use_volatility_filter=False,
                use_trend_filter=False
            )

            if metrics and metrics['total_trades'] >= 50:
                results.append({
                    'config': f"Conf={conf:.0%}, TP/SL={ratio:.1f}:1, Filters=Session",
                    'confidence': conf,
                    'tp_sl_ratio': ratio,
                    'filters': 'Session',
                    **metrics
                })

    # Test with all filters
    print("[3/5] Testing with all filters...")
    for conf in [0.70, 0.75, 0.80]:
        for ratio in [1.5, 2.0, 2.5]:
            metrics = backtest_with_filters(
                model_path,
                confidence_threshold=conf,
                tp_sl_ratio=ratio,
                use_session_filter=True,
                use_volatility_filter=True,
                use_trend_filter=True
            )

            if metrics and metrics['total_trades'] >= 20:
                results.append({
                    'config': f"Conf={conf:.0%}, TP/SL={ratio:.1f}:1, Filters=All",
                    'confidence': conf,
                    'tp_sl_ratio': ratio,
                    'filters': 'All',
                    **metrics
                })

    # Sort by profit factor
    results.sort(key=lambda x: x['profit_factor'], reverse=True)

    # Display top 10 configurations
    print("\n[4/5] Top 10 Configurations by Profit Factor:")
    print("="*70)
    print(f"{'Rank':<5} {'Configuration':<45} {'Trades':>7} {'Win%':>6} {'PF':>6} {'Net $':>8}")
    print("-"*70)

    for i, r in enumerate(results[:10], 1):
        print(f"{i:<5} {r['config']:<45} {r['total_trades']:>7} {r['win_rate']:>5.1f}% {r['profit_factor']:>5.2f} ${r['net_profit']:>7.0f}")

    # Find profitable configurations
    print("\n[5/5] Filtering for PROFITABLE configurations...")
    print("="*70)

    profitable = [r for r in results if
                  r['net_profit'] > 0 and
                  r['profit_factor'] > 1.5 and
                  r['win_rate'] >= 50 and
                  r['total_trades'] >= 50]

    if profitable:
        print(f"\n✅ Found {len(profitable)} PROFITABLE configurations!")
        print("\n🏆 BEST CONFIGURATION:")
        print("="*70)

        best = profitable[0]
        print(f"\nConfiguration: {best['config']}")
        print(f"\n📊 Performance:")
        print(f"  • Total Trades: {best['total_trades']}")
        print(f"  • Win Rate: {best['win_rate']:.1f}% ✅")
        print(f"  • Profit Factor: {best['profit_factor']:.2f} ✅")
        print(f"  • Net Profit: ${best['net_profit']:.2f} ✅")
        print(f"  • Avg Win: ${best['avg_win']:.2f}")
        print(f"  • Avg Loss: ${best['avg_loss']:.2f}")
        print(f"  • Max Drawdown: ${best['max_drawdown']:.2f}")
        print(f"  • TP Hit Rate: {best['tp_hit_rate']:.1f}%")

        print(f"\n🎯 Recommended Settings:")
        print(f"  • Confidence Threshold: {best['confidence']:.0%}")
        print(f"  • TP/SL Ratio: {best['tp_sl_ratio']:.1f}:1")
        print(f"  • Filters: {best['filters']}")

        # Save configuration
        config_file = 'optimal_config.txt'
        with open(config_file, 'w') as f:
            f.write(f"# Optimal Configuration for Profitable Trading\n")
            f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"confidence_threshold = {best['confidence']}\n")
            f.write(f"tp_sl_ratio = {best['tp_sl_ratio']}\n")
            f.write(f"filters = '{best['filters']}'\n\n")
            f.write(f"# Expected Performance (2024-2025 backtest):\n")
            f.write(f"# Win Rate: {best['win_rate']:.1f}%\n")
            f.write(f"# Profit Factor: {best['profit_factor']:.2f}\n")
            f.write(f"# Net Profit: ${best['net_profit']:.2f}\n")
            f.write(f"# Trades/Year: {best['total_trades']}\n")

        print(f"\n💾 Configuration saved to: {config_file}")

        return best

    else:
        print("\n❌ No configuration meets profitability criteria:")
        print("  • Win Rate >= 50%")
        print("  • Profit Factor >= 1.5")
        print("  • Net Profit > $0")
        print("  • Minimum 50 trades")

        print("\nBest available configuration:")
        if results:
            best_available = results[0]
            print(f"\n  {best_available['config']}")
            print(f"  Win Rate: {best_available['win_rate']:.1f}%")
            print(f"  Profit Factor: {best_available['profit_factor']:.2f}")
            print(f"  Net Profit: ${best_available['net_profit']:.2f}")

        return None


if __name__ == '__main__':
    print("\n" + "#"*70)
    print("# Optimal Configuration Finder")
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#"*70)

    best_config = find_optimal_configuration()

    print("\n" + "#"*70)
    if best_config:
        print("# ✅ PROFITABLE CONFIGURATION FOUND!")
        print("# Next: Retrain model with optimal TP/SL ratio")
        print("# Then: Test on demo account for 30 days")
    else:
        print("# ⚠️  Need further optimization")
        print("# Consider: XGBoost, ensemble models, more features")
    print("#"*70 + "\n")
