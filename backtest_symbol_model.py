#!/usr/bin/env python3
"""
Backtest Symbol-Specific ML Models

Comprehensive backtesting for symbol-specific models to validate profitability.

Usage:
    python3 backtest_symbol_model.py --symbol BTCUSD
    python3 backtest_symbol_model.py --symbol XAUUSD --confidence 0.70
"""

import sys
import os
import argparse
from pathlib import Path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import pandas as pd
import numpy as np
from datetime import datetime
import pickle

# Import feature engineer
sys.path.insert(0, 'backend/app/ml')
from improved_features import ImprovedFeatureEngineer


def backtest_symbol_model(
    symbol: str,
    model_path: str = None,
    confidence_threshold: float = 0.70,
    days: int = None,  # None = all test data
):
    """Backtest a symbol-specific model.

    Args:
        symbol: Trading symbol
        model_path: Path to model file (auto-detect if None)
        confidence_threshold: Minimum confidence for trades
        days: Number of recent days to backtest (None = all)

    Returns:
        dict with backtest results
    """

    print("=" * 70)
    print(f"BACKTESTING {symbol} ML MODEL")
    print("=" * 70)
    print(f"\nSymbol: {symbol}")
    print(f"Confidence Threshold: {confidence_threshold:.0%}")
    print(f"Days to backtest: {days if days else 'All test data'}")

    # Find model file if not specified
    if model_path is None:
        symbol_lower = symbol.lower()
        staging_dir = Path(f"models/{symbol_lower}/staging")
        production_dir = Path(f"models/{symbol_lower}/production")

        # Try production first, then staging
        model_files = []
        if production_dir.exists():
            model_files = list(production_dir.glob("model_*.pkl"))

        if not model_files and staging_dir.exists():
            model_files = list(staging_dir.glob("model_*.pkl"))

        if not model_files:
            raise FileNotFoundError(
                f"No model found for {symbol}. "
                f"Please train the model first: python3 train_symbol_model.py --symbol {symbol}"
            )

        # Use most recent model
        model_path = max(model_files, key=lambda p: p.stat().st_mtime)

    print(f"\n📦 Loading model: {model_path}")

    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)

    model = model_data['model']
    scaler = model_data['scaler']
    feature_columns = model_data['feature_columns']
    spread_pips = model_data.get('spread_pips', 3.0)

    print(f"   Symbol: {model_data.get('symbol', 'Unknown')}")
    print(f"   Trained: {model_data.get('trained_at', 'Unknown')}")
    print(f"   Accuracy: {model_data.get('accuracy', 0):.1%}")

    # Load data
    data_paths = {
        'XAUUSD': 'ohlcv/xauusd/xauusd_1h_clean.csv',
        'BTCUSD': 'ohlcv/btc/btcusd_1h_clean.csv',
        'EURUSD': 'ohlcv/eurusd/eurusd_1h_clean.csv',
    }

    data_path = data_paths.get(symbol)
    if not data_path or not Path(data_path).exists():
        raise FileNotFoundError(f"Data file not found for {symbol}: {data_path}")

    print(f"\n📊 Loading data from: {data_path}")
    df = pd.read_csv(data_path)
    print(f"   Loaded {len(df):,} candles")

    # Build features
    print("\n🔧 Building features...")
    engineer = ImprovedFeatureEngineer()
    df_featured = engineer.build_features(df)
    df_clean = df_featured.dropna()

    print(f"   Clean samples: {len(df_clean):,}")

    # Use test data only (last 20%)
    split_idx = int(len(df_clean) * 0.8)
    df_test = df_clean.iloc[split_idx:].copy()

    # Optionally limit to recent days
    if days:
        df_test['timestamp'] = pd.to_datetime(df_test['timestamp'])
        cutoff_date = df_test['timestamp'].max() - pd.Timedelta(days=days)
        df_test = df_test[df_test['timestamp'] >= cutoff_date]

    print(f"   Backtest period: {df_test['timestamp'].iloc[0]} to {df_test['timestamp'].iloc[-1]}")
    print(f"   Test samples: {len(df_test):,}")

    # Make predictions
    print("\n🤖 Generating predictions...")
    X_test = df_test[feature_columns]
    X_scaled = scaler.transform(X_test)

    predictions = model.predict(X_scaled)
    probabilities = model.predict_proba(X_scaled)

    # Add predictions to dataframe
    df_test['prediction'] = predictions
    df_test['confidence'] = probabilities.max(axis=1)

    # Filter by confidence threshold
    df_test['signal'] = 'HOLD'
    df_test.loc[(df_test['prediction'] == 1) & (df_test['confidence'] >= confidence_threshold), 'signal'] = 'SELL'
    df_test.loc[(df_test['prediction'] == 2) & (df_test['confidence'] >= confidence_threshold), 'signal'] = 'BUY'

    signal_counts = df_test['signal'].value_counts()
    print(f"\n   Signal Distribution:")
    print(f"   • HOLD: {signal_counts.get('HOLD', 0):,} ({signal_counts.get('HOLD', 0)/len(df_test):.1%})")
    print(f"   • SELL: {signal_counts.get('SELL', 0):,} ({signal_counts.get('SELL', 0)/len(df_test):.1%})")
    print(f"   • BUY:  {signal_counts.get('BUY', 0):,} ({signal_counts.get('BUY', 0)/len(df_test):.1%})")

    # Simulate trades
    print("\n💹 Simulating trades...")

    trades = []
    initial_balance = 10000.0
    balance = initial_balance
    position = None  # {'type': 'BUY'/'SELL', 'entry_price': float, 'entry_time': timestamp, 'sl': float, 'tp': float}

    for idx, row in df_test.iterrows():
        # Check if we have an open position
        if position:
            # Check TP/SL
            if position['type'] == 'BUY':
                if row['high'] >= position['tp']:
                    # TP hit
                    pnl = position['tp'] - position['entry_price']
                    pnl_pct = (pnl / position['entry_price']) * 100
                    balance += pnl

                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'type': 'BUY',
                        'entry_price': position['entry_price'],
                        'exit_price': position['tp'],
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'outcome': 'WIN',
                        'exit_reason': 'TP'
                    })
                    position = None

                elif row['low'] <= position['sl']:
                    # SL hit
                    pnl = position['sl'] - position['entry_price']
                    pnl_pct = (pnl / position['entry_price']) * 100
                    balance += pnl

                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'type': 'BUY',
                        'entry_price': position['entry_price'],
                        'exit_price': position['sl'],
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'outcome': 'LOSS',
                        'exit_reason': 'SL'
                    })
                    position = None

            elif position['type'] == 'SELL':
                if row['low'] <= position['tp']:
                    # TP hit
                    pnl = position['entry_price'] - position['tp']
                    pnl_pct = (pnl / position['entry_price']) * 100
                    balance += pnl

                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'type': 'SELL',
                        'entry_price': position['entry_price'],
                        'exit_price': position['tp'],
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'outcome': 'WIN',
                        'exit_reason': 'TP'
                    })
                    position = None

                elif row['high'] >= position['sl']:
                    # SL hit
                    pnl = position['entry_price'] - position['sl']
                    pnl_pct = (pnl / position['entry_price']) * 100
                    balance += pnl

                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': row['timestamp'],
                        'type': 'SELL',
                        'entry_price': position['entry_price'],
                        'exit_price': position['sl'],
                        'pnl': pnl,
                        'pnl_pct': pnl_pct,
                        'outcome': 'LOSS',
                        'exit_reason': 'SL'
                    })
                    position = None

        # Enter new position if signal present
        if position is None and row['signal'] in ['BUY', 'SELL']:
            atr = row['atr']

            if pd.notna(atr):
                entry_price = row['close']

                if row['signal'] == 'BUY':
                    sl = entry_price - (atr * model_data.get('stop_loss_atr', 0.8))
                    tp = entry_price + (atr * model_data.get('profit_target_atr', 1.2))

                    position = {
                        'type': 'BUY',
                        'entry_price': entry_price,
                        'entry_time': row['timestamp'],
                        'sl': sl,
                        'tp': tp
                    }

                elif row['signal'] == 'SELL':
                    sl = entry_price + (atr * model_data.get('stop_loss_atr', 0.8))
                    tp = entry_price - (atr * model_data.get('profit_target_atr', 1.2))

                    position = {
                        'type': 'SELL',
                        'entry_price': entry_price,
                        'entry_time': row['timestamp'],
                        'sl': sl,
                        'tp': tp
                    }

    # Close any open position at end
    if position:
        last_row = df_test.iloc[-1]
        exit_price = last_row['close']

        if position['type'] == 'BUY':
            pnl = exit_price - position['entry_price']
        else:
            pnl = position['entry_price'] - exit_price

        pnl_pct = (pnl / position['entry_price']) * 100
        balance += pnl

        trades.append({
            'entry_time': position['entry_time'],
            'exit_time': last_row['timestamp'],
            'type': position['type'],
            'entry_price': position['entry_price'],
            'exit_price': exit_price,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
            'outcome': 'WIN' if pnl > 0 else 'LOSS',
            'exit_reason': 'CLOSE'
        })

    # Calculate metrics
    print("\n" + "=" * 70)
    print("BACKTEST RESULTS")
    print("=" * 70)

    if not trades:
        print("\n⚠️  NO TRADES GENERATED")
        print("   Try lowering confidence threshold or adjusting model parameters")
        return {'total_trades': 0}

    df_trades = pd.DataFrame(trades)

    total_trades = len(df_trades)
    winning_trades = len(df_trades[df_trades['outcome'] == 'WIN'])
    losing_trades = len(df_trades[df_trades['outcome'] == 'LOSS'])

    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

    total_profit = df_trades[df_trades['pnl'] > 0]['pnl'].sum()
    total_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].sum())

    profit_factor = (total_profit / total_loss) if total_loss > 0 else 0

    net_profit = balance - initial_balance
    roi = (net_profit / initial_balance) * 100

    avg_win = df_trades[df_trades['pnl'] > 0]['pnl'].mean() if winning_trades > 0 else 0
    avg_loss = abs(df_trades[df_trades['pnl'] < 0]['pnl'].mean()) if losing_trades > 0 else 0

    print(f"\n📊 Trading Performance:")
    print(f"   Initial Balance: ${initial_balance:,.2f}")
    print(f"   Final Balance:   ${balance:,.2f}")
    print(f"   Net Profit:      ${net_profit:,.2f}")
    print(f"   ROI:             {roi:.2f}%")

    print(f"\n🎯 Trade Statistics:")
    print(f"   Total Trades:    {total_trades}")
    print(f"   Winning Trades:  {winning_trades}")
    print(f"   Losing Trades:   {losing_trades}")
    print(f"   Win Rate:        {win_rate:.1f}%")
    print(f"   Profit Factor:   {profit_factor:.2f}")

    print(f"\n💰 Trade Metrics:")
    print(f"   Total Profit:    ${total_profit:,.2f}")
    print(f"   Total Loss:      ${total_loss:,.2f}")
    print(f"   Avg Win:         ${avg_win:,.2f}")
    print(f"   Avg Loss:        ${avg_loss:,.2f}")
    print(f"   Risk/Reward:     1:{(avg_win/avg_loss if avg_loss > 0 else 0):.2f}")

    # Profitability assessment
    print("\n" + "=" * 70)
    print("PROFITABILITY ASSESSMENT")
    print("=" * 70)

    is_profitable = profit_factor > 1.5 and win_rate > 60

    if is_profitable:
        print("\n✅ MODEL IS PROFITABLE!")
        print(f"   ✓ Profit Factor: {profit_factor:.2f} > 1.5")
        print(f"   ✓ Win Rate: {win_rate:.1f}% > 60%")
        print("\n🎯 Ready for production deployment")
    else:
        print("\n❌ MODEL NEEDS IMPROVEMENT")
        if profit_factor <= 1.5:
            print(f"   ✗ Profit Factor: {profit_factor:.2f} ≤ 1.5")
        if win_rate <= 60:
            print(f"   ✗ Win Rate: {win_rate:.1f}% ≤ 60%")
        print("\n💡 Suggestions:")
        print("   • Adjust TP/SL ratio")
        print("   • Increase confidence threshold")
        print("   • Add more filters")
        print("   • Retrain with different parameters")

    results = {
        'symbol': symbol,
        'model_path': str(model_path),
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'losing_trades': losing_trades,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'net_profit': net_profit,
        'roi': roi,
        'is_profitable': is_profitable,
        'trades': trades
    }

    return results


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Backtest symbol-specific ML trading model'
    )
    parser.add_argument(
        '--symbol',
        type=str,
        required=True,
        help='Trading symbol to backtest'
    )
    parser.add_argument(
        '--model',
        type=str,
        default=None,
        help='Path to model file (auto-detect if not specified)'
    )
    parser.add_argument(
        '--confidence',
        type=float,
        default=0.70,
        help='Confidence threshold (default: 0.70)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=None,
        help='Number of recent days to backtest (default: all test data)'
    )

    args = parser.parse_args()

    print("\n" + "#" * 70)
    print(f"# Symbol-Specific Model Backtesting")
    print(f"# Symbol: {args.symbol}")
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#" * 70)

    try:
        results = backtest_symbol_model(
            symbol=args.symbol,
            model_path=args.model,
            confidence_threshold=args.confidence,
            days=args.days,
        )

        print("\n" + "#" * 70)
        print("# Backtesting Complete!")
        print("#" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
