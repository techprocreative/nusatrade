#!/usr/bin/env python3
"""
Simple Backtesting Script
Tests model profitability with realistic trading costs.

Simulates trading on historical data with:
- Spread costs
- Position sizing
- Win rate calculation
- Profit factor calculation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.ml.training import Trainer
from app.ml.features import FeatureEngineer
import pandas as pd
import numpy as np


def backtest_model(model_path, confidence_threshold=0.85, spread_pips=3):
    """
    Backtest model on historical data.

    Args:
        model_path: Path to trained model
        confidence_threshold: Minimum confidence to trade
        spread_pips: Spread cost in pips (XAUUSD typically 2-5 pips)
    """
    print("="*70)
    print("ML Model Backtesting - XAUUSD 1H")
    print("="*70)

    # Load model
    print("\n[1/5] Loading model...")
    trainer = Trainer()
    trainer.load_model(model_path)
    print(f"  ✅ {os.path.basename(model_path)}")

    # Load historical data (use 2024-2025 as out-of-sample test period)
    print("\n[2/5] Loading test data (2024-2025)...")
    df = pd.read_csv('ohlcv/xauusd/xauusd_1h_clean.csv')

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Filter for 2024-2025 (out-of-sample)
    test_data = df[df['timestamp'] >= '2024-01-01'].copy()
    print(f"  ✅ {len(test_data):,} candles from {test_data['timestamp'].min()} to {test_data['timestamp'].max()}")

    # Build features
    print("\n[3/5] Building features...")
    engineer = FeatureEngineer()
    test_featured = engineer.build_features(test_data)
    test_featured = test_featured.dropna()
    print(f"  ✅ {len(test_featured):,} samples ready")

    # Backtest trading
    print(f"\n[4/5] Simulating trades...")
    print(f"  Confidence threshold: {confidence_threshold:.0%}")
    print(f"  Spread: {spread_pips} pips")

    trades = []

    for i in range(len(test_featured) - 5):  # Need 5 candles ahead for exit
        row = test_featured.iloc[i:i+1]
        pred = trainer.predict(row)

        # Check confidence
        if pred['confidence'] < confidence_threshold:
            continue

        # Determine direction
        if pred['prediction'] == 1:
            trade_type = "BUY"
        else:
            trade_type = "SELL"

        # Entry price
        entry_price = float(row['close'].values[0])
        entry_time = row['timestamp'].values[0]

        # Exit after 5 candles (5 hours)
        exit_row = test_featured.iloc[i+5]
        exit_price = float(exit_row['close'])
        exit_time = exit_row['timestamp']

        # Calculate profit/loss in pips
        if trade_type == "BUY":
            price_move = (exit_price - entry_price) / entry_price * 10000  # Convert to pips (approx)
        else:  # SELL
            price_move = (entry_price - exit_price) / entry_price * 10000

        # Subtract spread
        profit_pips = price_move - spread_pips

        # Calculate P/L in dollars (assuming 0.01 lot = $0.10 per pip for Gold)
        lot_size = 0.01
        profit_usd = profit_pips * lot_size * 10  # $0.10 per pip for 0.01 lot

        trades.append({
            'entry_time': entry_time,
            'exit_time': exit_time,
            'type': trade_type,
            'entry_price': entry_price,
            'exit_price': exit_price,
            'price_move_pips': price_move,
            'profit_pips': profit_pips,
            'profit_usd': profit_usd,
            'confidence': pred['confidence']
        })

    print(f"  ✅ Executed {len(trades)} trades")

    # Calculate metrics
    print("\n[5/5] Calculating performance metrics...")

    if len(trades) == 0:
        print("  ❌ No trades executed (model too conservative or no signals)")
        return

    trades_df = pd.DataFrame(trades)

    # Win/Loss statistics
    winning_trades = trades_df[trades_df['profit_usd'] > 0]
    losing_trades = trades_df[trades_df['profit_usd'] < 0]
    breakeven_trades = trades_df[trades_df['profit_usd'] == 0]

    total_trades = len(trades_df)
    win_count = len(winning_trades)
    loss_count = len(losing_trades)
    win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

    # Profit statistics
    gross_profit = winning_trades['profit_usd'].sum() if len(winning_trades) > 0 else 0
    gross_loss = abs(losing_trades['profit_usd'].sum()) if len(losing_trades) > 0 else 0
    net_profit = gross_profit - gross_loss

    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else 0

    avg_win = winning_trades['profit_usd'].mean() if len(winning_trades) > 0 else 0
    avg_loss = losing_trades['profit_usd'].mean() if len(losing_trades) > 0 else 0
    largest_win = winning_trades['profit_usd'].max() if len(winning_trades) > 0 else 0
    largest_loss = losing_trades['profit_usd'].min() if len(losing_trades) > 0 else 0

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
    print(f"  • Breakeven Trades: {len(breakeven_trades)}")
    print(f"  • Average Confidence: {trades_df['confidence'].mean():.1%}")

    print(f"\n💰 Profitability:")
    print(f"  • Gross Profit: ${gross_profit:.2f}")
    print(f"  • Gross Loss: ${gross_loss:.2f}")
    print(f"  • Net Profit: ${net_profit:.2f}")
    print(f"  • Profit Factor: {profit_factor:.2f}")

    print(f"\n📈 Trade Performance:")
    print(f"  • Average Win: ${avg_win:.2f} ({winning_trades['profit_pips'].mean():.1f} pips)")
    print(f"  • Average Loss: ${avg_loss:.2f} ({losing_trades['profit_pips'].mean():.1f} pips)")
    print(f"  • Largest Win: ${largest_win:.2f}")
    print(f"  • Largest Loss: ${largest_loss:.2f}")
    print(f"  • Win/Loss Ratio: {abs(avg_win/avg_loss):.2f}" if avg_loss != 0 else "N/A")

    print(f"\n⚠️  Risk Metrics:")
    print(f"  • Maximum Drawdown: ${max_drawdown:.2f} ({max_drawdown_pct:.1f}%)")
    print(f"  • Total Pips: {trades_df['profit_pips'].sum():.1f} pips")

    print(f"\n🎯 Assessment:")

    # Profitable?
    if net_profit > 0 and profit_factor > 1.5:
        verdict = "✅ PROFITABLE - Model shows promise!"
    elif net_profit > 0 and profit_factor > 1.0:
        verdict = "⚠️  MARGINALLY PROFITABLE - Needs improvement"
    else:
        verdict = "❌ NOT PROFITABLE - Do not use with real money"

    print(f"  {verdict}")

    # Win rate assessment
    if win_rate >= 50:
        print(f"  ✅ Win rate {win_rate:.1f}% is acceptable")
    else:
        print(f"  ❌ Win rate {win_rate:.1f}% is below 50% (needs >50%)")

    # Profit factor assessment
    if profit_factor >= 1.5:
        print(f"  ✅ Profit factor {profit_factor:.2f} is good")
    elif profit_factor >= 1.0:
        print(f"  ⚠️  Profit factor {profit_factor:.2f} is marginal (needs >1.5)")
    else:
        print(f"  ❌ Profit factor {profit_factor:.2f} is losing (needs >1.5)")

    # Drawdown assessment
    if max_drawdown_pct < 20:
        print(f"  ✅ Drawdown {max_drawdown_pct:.1f}% is acceptable")
    else:
        print(f"  ❌ Drawdown {max_drawdown_pct:.1f}% is too high (needs <20%)")

    print("\n" + "="*70)
    print("NEXT STEPS")
    print("="*70)

    if net_profit > 0 and profit_factor > 1.5:
        print("""
✅ This model passed backtesting!

Next:
  1. Test on DEMO account for 30 days
  2. Monitor with MLPerformanceTracker
  3. Verify live results match backtest
  4. If demo is profitable, consider small real account

WARNING: Backtest != Live Performance
- Live trading has additional slippage
- Market conditions change
- Psychological pressure affects execution
        """)
    else:
        print("""
❌ This model FAILED backtesting!

Options:
  1. Adjust confidence threshold (higher = fewer trades)
  2. Retrain with different features
  3. Try ensemble of multiple models
  4. Use different exit strategy (not fixed 5 candles)
  5. Add filters (trend, volatility, time of day)

DO NOT use this model with real money.
        """)

    # Show sample trades
    print("\n" + "="*70)
    print("SAMPLE TRADES (First 10)")
    print("="*70)
    print(f"\n{'Time':<20} {'Type':>6} {'Entry':>10} {'Exit':>10} {'Pips':>8} {'P/L':>10}")
    print("-"*70)
    for _, trade in trades_df.head(10).iterrows():
        print(f"{str(trade['entry_time'])[:19]:<20} {trade['type']:>6} "
              f"${trade['entry_price']:>9.2f} ${trade['exit_price']:>9.2f} "
              f"{trade['profit_pips']:>7.1f} ${trade['profit_usd']:>9.2f}")


if __name__ == '__main__':
    print("\n" + "#"*70)
    print("# ML Model Backtesting Suite")
    print("#"*70)

    # Test Gradient Boosting with 85% threshold
    print("\n" + "="*70)
    print("TEST 1: Gradient Boosting (85% confidence)")
    print("="*70)
    backtest_model(
        model_path='models/model_gradient_boosting_20251212_212847.pkl',
        confidence_threshold=0.85,
        spread_pips=3
    )

    print("\n" + "#"*70)
    print("# Backtesting Complete!")
    print("#"*70 + "\n")
