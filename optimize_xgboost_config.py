#!/usr/bin/env python3
"""
Optimize XGBoost Configuration for Profitability
Test various filters and thresholds to find profitable setup.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
sys.path.insert(0, 'backend/app/ml')

import pandas as pd
import numpy as np
import pickle
from datetime import datetime
from improved_features import ImprovedFeatureEngineer


def backtest_with_filters(
    model_path,
    confidence_threshold=0.70,
    use_session_filter=True,
    use_volatility_filter=True,
    use_trend_filter=True,
    spread_pips=3.0
):
    """Backtest XGBoost with filters."""

    # Load model
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)

    model = model_data['model']
    scaler = model_data['scaler']
    feature_columns = model_data['feature_columns']
    profit_target_atr = model_data['profit_target_atr']
    stop_loss_atr = model_data['stop_loss_atr']

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

        # Skip HOLD
        if pred_class == 0:
            continue

        # FILTER 1: Confidence threshold
        if confidence < confidence_threshold:
            continue

        # FILTER 2: Session filter
        if use_session_filter:
            hour = row['hour'].values[0] if 'hour' in row.columns else None
            if hour is not None:
                if not ((8 <= hour < 16) or (13 <= hour < 21)):
                    continue

        # FILTER 3: Volatility filter
        if use_volatility_filter:
            vol_regime_low = row['vol_regime_low'].values[0] if 'vol_regime_low' in row.columns else 0
            vol_regime_high = row['vol_regime_high'].values[0] if 'vol_regime_high' in row.columns else 0

            if vol_regime_low == 1 or vol_regime_high == 1:
                continue

        # FILTER 4: Trend filter
        if use_trend_filter:
            strong_trend = row['strong_trend'].values[0] if 'strong_trend' in row.columns else 0
            if strong_trend != 1:
                continue

        # Execute trade
        trade_type = 'SELL' if pred_class == 1 else 'BUY'
        entry_price = float(row['close'].values[0])
        entry_atr = float(row['atr'].values[0])

        if pd.isna(entry_atr):
            continue

        spread_cost = spread_pips / 10000 * entry_price
        profit_target = entry_atr * profit_target_atr
        stop_loss = entry_atr * stop_loss_atr

        if trade_type == 'BUY':
            entry_with_spread = entry_price + spread_cost
            tp_price = entry_with_spread + profit_target
            sl_price = entry_with_spread - stop_loss
        else:
            entry_with_spread = entry_price - spread_cost
            tp_price = entry_with_spread - profit_target
            sl_price = entry_with_spread + stop_loss

        # Simulate
        exit_price = None
        hit_tp = False

        for j in range(i + 1, min(i + 25, len(test_featured))):
            candle = test_featured.iloc[j]

            if trade_type == 'BUY':
                if candle['high'] >= tp_price:
                    exit_price = tp_price
                    hit_tp = True
                    break
                elif candle['low'] <= sl_price:
                    exit_price = sl_price
                    break
            else:
                if candle['low'] <= tp_price:
                    exit_price = tp_price
                    hit_tp = True
                    break
                elif candle['high'] >= sl_price:
                    exit_price = sl_price
                    break

        if exit_price is None:
            exit_price = float(test_featured.iloc[min(i + 24, len(test_featured) - 1)]['close'])

        # Calculate profit
        if trade_type == 'BUY':
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


def optimize_xgboost():
    """Find optimal configuration for XGBoost model."""

    print("="*70)
    print("XGBOOST OPTIMIZATION - FINDING PROFITABLE CONFIG")
    print("="*70)
    print()

    model_path = 'models/model_xgboost_20251212_235414.pkl'

    # Test configurations
    configs = [
        # No filters
        {'conf': 0.50, 'session': False, 'vol': False, 'trend': False, 'name': 'Baseline (50% conf, no filters)'},
        {'conf': 0.60, 'session': False, 'vol': False, 'trend': False, 'name': 'Baseline (60% conf, no filters)'},

        # Session filter only
        {'conf': 0.60, 'session': True, 'vol': False, 'trend': False, 'name': 'Session filter (60% conf)'},
        {'conf': 0.70, 'session': True, 'vol': False, 'trend': False, 'name': 'Session filter (70% conf)'},

        # Session + Volatility
        {'conf': 0.65, 'session': True, 'vol': True, 'trend': False, 'name': 'Session + Vol (65% conf)'},
        {'conf': 0.70, 'session': True, 'vol': True, 'trend': False, 'name': 'Session + Vol (70% conf)'},

        # All filters
        {'conf': 0.60, 'session': True, 'vol': True, 'trend': True, 'name': 'All filters (60% conf)'},
        {'conf': 0.65, 'session': True, 'vol': True, 'trend': True, 'name': 'All filters (65% conf)'},
        {'conf': 0.70, 'session': True, 'vol': True, 'trend': True, 'name': 'All filters (70% conf)'},
        {'conf': 0.75, 'session': True, 'vol': True, 'trend': True, 'name': 'All filters (75% conf)'},
    ]

    results = []

    for i, cfg in enumerate(configs, 1):
        print(f"[{i}/{len(configs)}] Testing: {cfg['name']}...", end=" ")

        metrics = backtest_with_filters(
            model_path,
            confidence_threshold=cfg['conf'],
            use_session_filter=cfg['session'],
            use_volatility_filter=cfg['vol'],
            use_trend_filter=cfg['trend']
        )

        if metrics and metrics['total_trades'] >= 20:
            results.append({
                'config': cfg['name'],
                'confidence': cfg['conf'],
                **metrics
            })
            print(f"✓ ({metrics['total_trades']} trades, {metrics['win_rate']:.1f}% WR, PF={metrics['profit_factor']:.2f})")
        else:
            print("✗ (insufficient trades)")

    # Sort by profit factor
    results.sort(key=lambda x: x['profit_factor'], reverse=True)

    print()
    print("="*70)
    print("TOP 5 CONFIGURATIONS")
    print("="*70)
    print(f"{'Rank':<5} {'Configuration':<40} {'Trades':>7} {'Win%':>6} {'PF':>6} {'Net $':>8}")
    print("-"*70)

    for i, r in enumerate(results[:5], 1):
        status = "✅" if r['profit_factor'] > 1.0 else "❌"
        print(f"{i:<5} {r['config']:<40} {r['total_trades']:>7} {r['win_rate']:>5.1f}% {r['profit_factor']:>5.2f} ${r['net_profit']:>7.0f} {status}")

    print()
    print("="*70)
    print("DETAILED ANALYSIS - BEST CONFIGURATION")
    print("="*70)

    if results:
        best = results[0]
        print(f"\n🏆 Configuration: {best['config']}")
        print(f"\n📊 Performance:")
        print(f"  • Total Trades: {best['total_trades']}")
        print(f"  • Win Rate: {best['win_rate']:.1f}%")
        print(f"  • Profit Factor: {best['profit_factor']:.2f}")
        print(f"  • Net Profit: ${best['net_profit']:.2f}")
        print(f"  • Avg Win: ${best['avg_win']:.2f}")
        print(f"  • Avg Loss: ${best['avg_loss']:.2f}")
        print(f"  • Max Drawdown: ${best['max_drawdown']:.2f}")
        print(f"  • TP Hit Rate: {best['tp_hit_rate']:.1f}%")

        print(f"\n🎯 Assessment:")
        if best['net_profit'] > 0 and best['profit_factor'] > 1.0:
            print("  ✅ PROFITABLE!")
            print("  ✅ Ready for demo testing")
        elif best['profit_factor'] > 0.95:
            print("  ⚠️  Close to breakeven - may be profitable with broker spreads optimization")
        else:
            print("  ❌ NOT PROFITABLE YET")
            print("  💡 Next steps:")
            print("     1. Add external features (USD Index, VIX, bond yields)")
            print("     2. Try ensemble models")
            print("     3. Multi-timeframe approach")

        # Save configuration
        if best['profit_factor'] > 0.90:
            config_file = 'optimal_xgboost_config.txt'
            with open(config_file, 'w') as f:
                f.write(f"# Optimal XGBoost Configuration\n")
                f.write(f"# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(f"model_path = 'models/model_xgboost_20251212_235414.pkl'\n")
                f.write(f"confidence_threshold = {best['confidence']}\n")
                f.write(f"# {best['config']}\n\n")
                f.write(f"# Expected Performance (2024-2025 backtest):\n")
                f.write(f"# Win Rate: {best['win_rate']:.1f}%\n")
                f.write(f"# Profit Factor: {best['profit_factor']:.2f}\n")
                f.write(f"# Net Profit: ${best['net_profit']:.2f}\n")
                f.write(f"# Trades/Year: {best['total_trades']}\n")

            print(f"\n💾 Configuration saved to: {config_file}")

        return best

    return None


if __name__ == '__main__':
    print("\n" + "#"*70)
    print("# XGBoost Configuration Optimization")
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#"*70)
    print()

    best = optimize_xgboost()

    print("\n" + "#"*70)
    if best and best['profit_factor'] > 1.0:
        print("# ✅ PROFITABLE CONFIGURATION FOUND!")
    elif best and best['profit_factor'] > 0.95:
        print("# ⚠️  CLOSE TO PROFITABLE - needs fine-tuning")
    else:
        print("# ❌ NOT PROFITABLE - needs advanced techniques")
    print("#"*70 + "\n")
