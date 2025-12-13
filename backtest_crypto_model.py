#!/usr/bin/env python3
"""
Backtest Crypto-Optimized Models with Crypto-Specific Filters

Applies crypto trading rules:
- Only trade during strong trends (ADX > 25)
- Require volume confirmation
- Avoid extreme volatility
- Wider TP/SL for crypto volatility

Usage:
    python3 backtest_crypto_model.py --symbol BTCUSD
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
import pickle

# Import crypto features
sys.path.insert(0, 'backend/app/ml')
from crypto_features import CryptoFeatureEngineer


def backtest_crypto_model(
    symbol='BTCUSD',
    model_path=None,
    confidence_threshold=0.60,  # Lower for crypto (more volatile)
    apply_crypto_filters=True,
):
    """Backtest crypto model with crypto-specific filters."""

    print("=" * 70)
    print(f"BACKTESTING CRYPTO-OPTIMIZED MODEL: {symbol}")
    print("=" * 70)
    print(f"\nSymbol: {symbol}")
    print(f"Confidence Threshold: {confidence_threshold:.0%}")
    print(f"Crypto Filters: {'ENABLED' if apply_crypto_filters else 'DISABLED'}")

    # Find model
    if model_path is None:
        crypto_dir = Path(f"models/{symbol.lower()}/crypto-optimized")
        if crypto_dir.exists():
            models = list(crypto_dir.glob("model_crypto_*.pkl"))
            if models:
                model_path = max(models, key=lambda p: p.stat().st_mtime)

    if not model_path or not Path(model_path).exists():
        raise FileNotFoundError(f"No crypto model found for {symbol}")

    print(f"\n📦 Loading crypto-optimized model: {model_path}")

    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)

    model = model_data['model']
    scaler = model_data['scaler']
    feature_columns = model_data['feature_columns']

    print(f"   Strategy: {model_data.get('strategy', 'Unknown')}")
    print(f"   Trained: {model_data.get('trained_at', 'Unknown')}")
    print(f"   Accuracy: {model_data.get('accuracy', 0):.1%}")
    print(f"   TP/SL: {model_data.get('profit_target_atr', 0)}x / {model_data.get('stop_loss_atr', 0)}x ATR")

    # Load data
    data_path = f"ohlcv/{symbol.lower().replace('usd', '')}/{symbol.lower()}_1h_clean.csv"
    print(f"\n📊 Loading data: {data_path}")

    df = pd.read_csv(data_path)
    print(f"   Loaded {len(df):,} candles")

    # Build crypto features
    print("\n🔧 Building crypto features...")
    engineer = CryptoFeatureEngineer()
    df_featured = engineer.build_crypto_features(df)
    df_clean = df_featured.dropna()

    # Use test data (last 20%)
    split_idx = int(len(df_clean) * 0.8)
    df_test = df_clean.iloc[split_idx:].copy()

    print(f"   Backtest period: {df_test['timestamp'].iloc[0]} to {df_test['timestamp'].iloc[-1]}")
    print(f"   Test samples: {len(df_test):,}")

    # Make predictions
    print("\n🤖 Generating predictions...")
    X_test = df_test[feature_columns]
    X_scaled = scaler.transform(X_test)

    predictions = model.predict(X_scaled)
    probabilities = model.predict_proba(X_scaled)

    df_test['prediction'] = predictions
    df_test['confidence'] = probabilities.max(axis=1)

    # Initial signals based on confidence
    df_test['signal'] = 'HOLD'
    df_test.loc[(df_test['prediction'] == 1) & (df_test['confidence'] >= confidence_threshold), 'signal'] = 'SELL'
    df_test.loc[(df_test['prediction'] == 2) & (df_test['confidence'] >= confidence_threshold), 'signal'] = 'BUY'

    if apply_crypto_filters:
        print("\n🔷 Applying crypto-specific filters...")

        initial_signals = (df_test['signal'] != 'HOLD').sum()

        # Filter 1: Strong trend required (ADX > 25)
        weak_trend = df_test['strong_trend'] == 0
        df_test.loc[weak_trend, 'signal'] = 'HOLD'
        after_trend = (df_test['signal'] != 'HOLD').sum()
        print(f"   • Trend filter (ADX > 25): {initial_signals} → {after_trend} signals")

        # Filter 2: Volume confirmation (above average)
        min_vol_ratio = model_data.get('min_volume_ratio', 1.3)
        low_volume = df_test['volume_surge'] < min_vol_ratio
        df_test.loc[low_volume & (df_test['signal'] != 'HOLD'), 'signal'] = 'HOLD'
        after_volume = (df_test['signal'] != 'HOLD').sum()
        print(f"   • Volume filter (>{min_vol_ratio}x avg): {after_trend} → {after_volume} signals")

        # Filter 3: Avoid extreme volatility
        extreme_vol = df_test['normal_volatility'] == 0
        df_test.loc[extreme_vol & (df_test['signal'] != 'HOLD'), 'signal'] = 'HOLD'
        after_vol = (df_test['signal'] != 'HOLD').sum()
        print(f"   • Volatility filter (normal range): {after_volume} → {after_vol} signals")

        # Filter 4: Trend alignment (optional but powerful)
        # For BUY: require bullish alignment
        # For SELL: require bearish alignment
        buy_no_alignment = (df_test['signal'] == 'BUY') & (df_test['bullish_alignment'] == 0)
        sell_no_alignment = (df_test['signal'] == 'SELL') & (df_test['bearish_alignment'] == 0)
        df_test.loc[buy_no_alignment | sell_no_alignment, 'signal'] = 'HOLD'
        final_signals = (df_test['signal'] != 'HOLD').sum()
        print(f"   • EMA alignment filter: {after_vol} → {final_signals} signals")

        print(f"\n   📉 Filter efficiency: {initial_signals} → {final_signals} ({final_signals/initial_signals*100 if initial_signals > 0 else 0:.1f}% pass rate)")

    signal_counts = df_test['signal'].value_counts()
    print(f"\n   Final Signal Distribution:")
    print(f"   • HOLD: {signal_counts.get('HOLD', 0):,} ({signal_counts.get('HOLD', 0)/len(df_test):.1%})")
    print(f"   • SELL: {signal_counts.get('SELL', 0):,} ({signal_counts.get('SELL', 0)/len(df_test):.1%})")
    print(f"   • BUY:  {signal_counts.get('BUY', 0):,} ({signal_counts.get('BUY', 0)/len(df_test):.1%})")

    # Simulate trades
    print("\n💹 Simulating trades with crypto parameters...")

    trades = []
    initial_balance = 10000.0
    balance = initial_balance
    position = None

    profit_target_atr = model_data.get('profit_target_atr', 2.5)
    stop_loss_atr = model_data.get('stop_loss_atr', 1.5)

    for idx, row in df_test.iterrows():
        # Check open position
        if position:
            if position['type'] == 'BUY':
                if row['high'] >= position['tp']:
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

        # Enter new position
        if position is None and row['signal'] in ['BUY', 'SELL']:
            atr = row['atr']

            if pd.notna(atr):
                entry_price = row['close']

                if row['signal'] == 'BUY':
                    sl = entry_price - (atr * stop_loss_atr)
                    tp = entry_price + (atr * profit_target_atr)

                    position = {
                        'type': 'BUY',
                        'entry_price': entry_price,
                        'entry_time': row['timestamp'],
                        'sl': sl,
                        'tp': tp
                    }

                elif row['signal'] == 'SELL':
                    sl = entry_price + (atr * stop_loss_atr)
                    tp = entry_price - (atr * profit_target_atr)

                    position = {
                        'type': 'SELL',
                        'entry_price': entry_price,
                        'entry_time': row['timestamp'],
                        'sl': sl,
                        'tp': tp
                    }

    # Close open position
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
    print("CRYPTO BACKTEST RESULTS")
    print("=" * 70)

    if not trades:
        print("\n⚠️  NO TRADES GENERATED")
        print("   Crypto filters may be too strict - consider adjusting")
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

    rr_ratio = avg_win / avg_loss if avg_loss > 0 else 0

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
    print(f"   Risk/Reward:     1:{rr_ratio:.2f}")

    # Crypto profitability assessment (adjusted targets)
    print("\n" + "=" * 70)
    print("CRYPTO PROFITABILITY ASSESSMENT")
    print("=" * 70)

    is_profitable = profit_factor > 1.3 and win_rate > 50 and rr_ratio > 1.5

    if is_profitable:
        print("\n✅ CRYPTO MODEL IS PROFITABLE!")
        print(f"   ✓ Profit Factor: {profit_factor:.2f} > 1.3 (crypto target)")
        print(f"   ✓ Win Rate: {win_rate:.1f}% > 50% (crypto target)")
        print(f"   ✓ Risk/Reward: 1:{rr_ratio:.2f} > 1:1.5")
        print("\n🎯 Ready for DEMO testing (60 days minimum)")
        print("   Test with 0.01 lots first!")
    else:
        print("\n⚠️  MODEL NEEDS FURTHER OPTIMIZATION")
        reasons = []
        if profit_factor <= 1.3:
            print(f"   • Profit Factor: {profit_factor:.2f} ≤ 1.3")
            reasons.append("profit_factor")
        if win_rate <= 50:
            print(f"   • Win Rate: {win_rate:.1f}% ≤ 50%")
            reasons.append("win_rate")
        if rr_ratio <= 1.5:
            print(f"   • Risk/Reward: 1:{rr_ratio:.2f} ≤ 1:1.5")
            reasons.append("risk_reward")

        print("\n💡 Crypto-Specific Suggestions:")
        if 'win_rate' in reasons:
            print("   • Lower confidence threshold (current: {:.0f}%)".format(confidence_threshold * 100))
            print("   • Relax trend filter (ADX > 20 instead of 25)")
        if 'profit_factor' in reasons or 'risk_reward' in reasons:
            print("   • Increase TP/SL ratio (try 3:1.5 instead of 2.5:1.5)")
            print("   • Add trailing stop for crypto trends")

    results = {
        'symbol': symbol,
        'total_trades': total_trades,
        'winning_trades': winning_trades,
        'win_rate': win_rate,
        'profit_factor': profit_factor,
        'net_profit': net_profit,
        'roi': roi,
        'rr_ratio': rr_ratio,
        'is_profitable': is_profitable,
    }

    return results


if __name__ == '__main__':
    print("\n" + "#" * 70)
    print("# Crypto-Optimized Model Backtesting")
    print("# Symbol: BTCUSD")
    print(f"# Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("#" * 70)

    try:
        results = backtest_crypto_model(
            symbol='BTCUSD',
            confidence_threshold=0.60,  # Lower for crypto
            apply_crypto_filters=True,
        )

        print("\n" + "#" * 70)
        print("# Backtesting Complete!")
        print("#" * 70 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
