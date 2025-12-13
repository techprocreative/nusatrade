#!/usr/bin/env python3
"""
Backtest Improved Model
Tests the improved model with ATR-based exit strategy.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import pandas as pd
import numpy as np
import pickle
from datetime import datetime

sys.path.insert(0, 'backend/app/ml')
from improved_features import ImprovedFeatureEngineer


def backtest_improved_model(model_path, spread_pips=3.0):
    """Backtest improved model on 2024-2025 data."""

    print("="*70)
    print("IMPROVED MODEL BACKTESTING - XAUUSD 1H")
    print("="*70)

    # Load model
    print("\n[1/5] Loading model...")
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)

    model = model_data['model']
    scaler = model_data['scaler']
    feature_columns = model_data['feature_columns']
    profit_target_atr = model_data['profit_target_atr']
    stop_loss_atr = model_data['stop_loss_atr']

    print(f"  ✅ {os.path.basename(model_path)}")
    print(f"  Strategy: TP={profit_target_atr}xATR, SL={stop_loss_atr}xATR")

    # Load test data (2024-2025)
    print("\n[2/5] Loading test data...")
    df = pd.read_csv('ohlcv/xauusd/xauusd_1h_clean.csv')
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    test_data = df[df['timestamp'] >= '2024-01-01'].copy()
    print(f"  ✅ {len(test_data):,} candles ({test_data['timestamp'].min()} to {test_data['timestamp'].max()})")

    # Build features
    print("\n[3/5] Building features...")
    engineer = ImprovedFeatureEngineer()
    test_featured = engineer.build_features(test_data)
    test_featured = test_featured.dropna()
    print(f"  ✅ {len(test_featured):,} samples ready")

    # Backtest
    print(f"\n[4/5] Simulating trades...")
    print(f"  Spread: {spread_pips} pips")

    trades = []

    for i in range(len(test_featured) - 24):  # Need 24 candles ahead
        row = test_featured.iloc[i:i+1]

        # Make prediction
        X = row[feature_columns]
        X_scaled = scaler.transform(X)
        pred_class = model.predict(X_scaled)[0]
        pred_proba = model.predict_proba(X_scaled)[0]

        # Get prediction confidence
        confidence = pred_proba[pred_class]

        # Skip if HOLD (class 0)
        if pred_class == 0:
            continue

        # Determine trade type
        trade_type = "SELL" if pred_class == 1 else "BUY"

        # Entry setup
        entry_price = float(row['close'].values[0])
        entry_atr = float(row['atr'].values[0])
        entry_time = row['timestamp'].values[0]

        if pd.isna(entry_atr):
            continue

        # Calculate TP/SL based on ATR
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
        else:  # SELL
            price_diff_pips = (entry_with_spread - exit_price) / entry_price * 10000

        profit_usd = price_diff_pips * 0.01 * 10  # 0.01 lot, $0.10 per pip

        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'type': trade_type,
            'entry_price': entry_with_spread,
            'exit_price': exit_price,
            'profit_pips': price_diff_pips,
            'profit_usd': profit_usd,
            'confidence': confidence,
            'hit_tp': hit_tp
        })

    print(f"  ✅ Executed {len(trades)} trades")

    # Calculate metrics
    print("\n[5/5] Calculating performance...")

    if len(trades) == 0:
        print("  ❌ No trades executed!")
        return

    trades_df = pd.DataFrame(trades)

    # Win/Loss
    winning_trades = trades_df[trades_df['profit_usd'] > 0]
    losing_trades = trades_df[trades_df['profit_usd'] < 0]

    total_trades = len(trades_df)
    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

    # Profit metrics
    gross_profit = winning_trades['profit_usd'].sum() if len(winning_trades) > 0 else 0
    gross_loss = abs(losing_trades['profit_usd'].sum()) if len(losing_trades) > 0 else 0
    net_profit = gross_profit - gross_loss
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0

    avg_win = winning_trades['profit_usd'].mean() if len(winning_trades) > 0 else 0
    avg_loss = losing_trades['profit_usd'].mean() if len(losing_trades) > 0 else 0

    # Drawdown
    cumulative = trades_df['profit_usd'].cumsum()
    running_max = cumulative.cummax()
    drawdown = running_max - cumulative
    max_drawdown = drawdown.max()
    max_drawdown_pct = (max_drawdown / running_max.max() * 100) if running_max.max() > 0 else 0

    # Display results
    print("\n" + "="*70)
    print("BACKTEST RESULTS")
    print("="*70)

    print(f"\n📊 Trading Statistics:")
    print(f"  • Total Trades: {total_trades}")
    print(f"  • Winning Trades: {win_count} ({win_rate:.1f}%)")
    print(f"  • Losing Trades: {loss_count} ({loss_count/total_trades*100:.1f}%)")
    print(f"  • TP Hit Rate: {trades_df['hit_tp'].sum()}/{total_trades} ({trades_df['hit_tp'].sum()/total_trades*100:.1f}%)")

    print(f"\n💰 Profitability:")
    print(f"  • Gross Profit: ${gross_profit:.2f}")
    print(f"  • Gross Loss: ${gross_loss:.2f}")
    print(f"  • Net Profit: ${net_profit:.2f}")
    print(f"  • Profit Factor: {profit_factor:.2f}")

    print(f"\n📈 Trade Performance:")
    print(f"  • Average Win: ${avg_win:.2f}")
    print(f"  • Average Loss: ${avg_loss:.2f}")
    print(f"  • Win/Loss Ratio: {abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "N/A")

    print(f"\n⚠️  Risk Metrics:")
    print(f"  • Maximum Drawdown: ${max_drawdown:.2f} ({max_drawdown_pct:.1f}%)")

    # Assessment
    print(f"\n🎯 Assessment:")

    if net_profit > 0 and profit_factor > 1.5 and win_rate >= 50:
        verdict = "✅ PROFITABLE - Model passed all criteria!"
    elif net_profit > 0 and profit_factor > 1.0:
        verdict = "⚠️  MARGINALLY PROFITABLE - Needs improvement"
    else:
        verdict = "❌ NOT PROFITABLE - Further optimization needed"

    print(f"  {verdict}")

    if win_rate >= 50:
        print(f"  ✅ Win rate {win_rate:.1f}% ≥ 50%")
    else:
        print(f"  ❌ Win rate {win_rate:.1f}% < 50%")

    if profit_factor >= 1.5:
        print(f"  ✅ Profit factor {profit_factor:.2f} ≥ 1.5")
    elif profit_factor >= 1.0:
        print(f"  ⚠️  Profit factor {profit_factor:.2f} is marginal")
    else:
        print(f"  ❌ Profit factor {profit_factor:.2f} < 1.0")

    if max_drawdown_pct < 20:
        print(f"  ✅ Drawdown {max_drawdown_pct:.1f}% < 20%")
    else:
        print(f"  ❌ Drawdown {max_drawdown_pct:.1f}% ≥ 20%")

    # Next steps
    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)

    if net_profit > 0 and profit_factor > 1.5:
        print("""
✅ Model PASSED backtesting!

Recommended:
  1. Test on DEMO account for 30 days
  2. Use 0.01 lot size
  3. Monitor daily with MLPerformanceTracker
  4. If demo results match backtest → Consider small real account
  5. Start with $100-500, max 0.02 lots
        """)
    else:
        print("""
Model needs further optimization:
  1. Adjust confidence threshold
  2. Try different TP/SL ratios
  3. Add filters (session, volatility, trend alignment)
  4. Consider ensemble models

Current model not recommended for live trading yet.
        """)


if __name__ == '__main__':
    print("\n" + "#"*70)
    print("# Improved Model Backtesting")
    print("#"*70)

    backtest_improved_model(
        model_path='models/model_improved_gradient_boosting_20251212_223406.pkl',
        spread_pips=3.0
    )

    print("\n" + "#"*70)
    print("# Backtesting Complete!")
    print("#"*70 + "\n")
