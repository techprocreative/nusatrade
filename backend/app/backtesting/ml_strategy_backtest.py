"""
ML Strategy Backtesting - Default backtest configuration for profitable ML model.

This module provides a complete backtesting setup for the ML profitable strategy,
ensuring the strategy can be validated before live deployment.
"""

import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from pathlib import Path

import pandas as pd
import numpy as np
import pickle

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from app.core.logging import get_logger
from app.ml.improved_features import ImprovedFeatureEngineer

logger = get_logger(__name__)


class MLStrategyBacktest:
    """
    Complete backtesting setup for ML profitable strategy.

    Validates the strategy performance using historical data
    before deploying to live trading.
    """

    def __init__(
        self,
        model_path: str = "models/model_xgboost_20251212_235414.pkl",
        data_path: str = "ohlcv/xauusd/xauusd_1h_clean.csv",
        initial_balance: float = 10000.0,
        lot_size: float = 0.01,
    ):
        """
        Initialize backtest.

        Args:
            model_path: Path to trained ML model
            data_path: Path to historical OHLCV data
            initial_balance: Starting balance for backtest
            lot_size: Lot size per trade
        """
        self.model_path = model_path
        self.data_path = data_path
        self.initial_balance = initial_balance
        self.lot_size = lot_size

        # Strategy configuration (matches profitable config)
        self.confidence_threshold = 0.70
        self.use_session_filter = True
        self.use_volatility_filter = True
        self.use_trend_filter = False

        # Risk management
        self.stop_loss_atr = 1.2
        self.take_profit_atr = 0.8
        self.max_holding_hours = 8
        self.spread_pips = 3.0  # Realistic spread

        # Load model and data
        self.model = None
        self.scaler = None
        self.feature_columns = None
        self.df = None

        self._load_model()
        self._load_data()

    def _load_model(self):
        """Load the trained ML model."""
        if not Path(self.model_path).exists():
            logger.error(f"Model file not found: {self.model_path}")
            return

        try:
            with open(self.model_path, 'rb') as f:
                model_data = pickle.load(f)

            self.model = model_data['model']
            self.scaler = model_data['scaler']
            self.feature_columns = model_data['feature_columns']

            logger.info(f"✅ Model loaded: {self.model_path}")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")

    def _load_data(self):
        """Load historical OHLCV data."""
        if not Path(self.data_path).exists():
            logger.error(f"Data file not found: {self.data_path}")
            return

        try:
            self.df = pd.read_csv(self.data_path)
            self.df['timestamp'] = pd.to_datetime(self.df['timestamp'])

            logger.info(f"✅ Data loaded: {len(self.df)} candles from {self.df['timestamp'].min()} to {self.df['timestamp'].max()}")
        except Exception as e:
            logger.error(f"Failed to load data: {e}")

    def run_backtest(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run backtest on historical data.

        Args:
            start_date: Start date for backtest (YYYY-MM-DD), defaults to 2024-01-01
            end_date: End date for backtest (YYYY-MM-DD), defaults to latest

        Returns:
            Dict with backtest results and metrics
        """
        if self.model is None or self.df is None:
            logger.error("Model or data not loaded")
            return self._empty_results()

        # Filter date range
        df = self.df.copy()

        if start_date:
            df = df[df['timestamp'] >= pd.to_datetime(start_date)]
        else:
            # Default: last 1 year
            df = df[df['timestamp'] >= (datetime.now() - timedelta(days=365))]

        if end_date:
            df = df[df['timestamp'] <= pd.to_datetime(end_date)]

        logger.info(f"Backtesting from {df['timestamp'].min()} to {df['timestamp'].max()}")

        # Build features
        engineer = ImprovedFeatureEngineer()
        df = engineer.build_features(df)
        df = df.dropna()

        if len(df) == 0:
            logger.error("No data after feature engineering")
            return self._empty_results()

        # Run backtest simulation
        trades = []
        equity_curve = [self.initial_balance]
        balance = self.initial_balance
        position = None  # Current position

        for i in range(100, len(df)):  # Start after warmup period
            current_time = df.iloc[i]['timestamp']
            current_price = df.iloc[i]['close']

            # Check if we have an open position
            if position:
                # Check exit conditions
                should_exit, exit_reason = self._check_exit(position, df.iloc[i], current_time)

                if should_exit:
                    # Close position
                    pnl = self._calculate_pnl(position, current_price)
                    balance += pnl

                    position['exit_time'] = current_time
                    position['exit_price'] = current_price
                    position['pnl'] = pnl
                    position['exit_reason'] = exit_reason

                    trades.append(position)
                    position = None

                    logger.debug(f"Position closed: {exit_reason}, PnL: ${pnl:.2f}")

            # If no position, check entry conditions
            if position is None:
                signal = self._get_signal(df.iloc[i:i+1])

                if signal['signal'] in ['BUY', 'SELL']:
                    # Open new position
                    position = {
                        'entry_time': current_time,
                        'entry_price': signal['entry_price'],
                        'direction': signal['signal'],
                        'stop_loss': signal['sl_price'],
                        'take_profit': signal['tp_price'],
                        'lot_size': self.lot_size,
                        'confidence': signal['confidence'],
                    }

                    logger.debug(f"Position opened: {signal['signal']} @ ${signal['entry_price']:.2f}, SL: ${signal['sl_price']:.2f}, TP: ${signal['tp_price']:.2f}")

            # Update equity curve
            equity_curve.append(balance)

        # Close any remaining position at end
        if position:
            pnl = self._calculate_pnl(position, df.iloc[-1]['close'])
            balance += pnl
            position['exit_time'] = df.iloc[-1]['timestamp']
            position['exit_price'] = df.iloc[-1]['close']
            position['pnl'] = pnl
            position['exit_reason'] = 'backtest_end'
            trades.append(position)

        # Calculate metrics
        metrics = self._calculate_metrics(trades, equity_curve, balance)

        logger.info(f"Backtest complete: {metrics['total_trades']} trades, Win Rate: {metrics['win_rate']:.1f}%, Profit Factor: {metrics['profit_factor']:.2f}")

        return {
            'trades': trades,
            'equity_curve': equity_curve,
            'metrics': metrics,
            'config': {
                'initial_balance': self.initial_balance,
                'final_balance': balance,
                'start_date': df['timestamp'].min().isoformat(),
                'end_date': df['timestamp'].max().isoformat(),
            }
        }

    def _get_signal(self, row: pd.DataFrame) -> Dict[str, Any]:
        """
        Get trading signal from ML model.

        Applies all filters (confidence, session, volatility).
        """
        # Build feature vector
        X = row[self.feature_columns]
        X_scaled = self.scaler.transform(X)

        # Predict
        pred_class = self.model.predict(X_scaled)[0]
        pred_proba = self.model.predict_proba(X_scaled)[0]
        confidence = float(pred_proba[pred_class])

        # Check filters
        if pred_class == 0:  # HOLD
            return {'signal': 'HOLD', 'confidence': 0.0}

        if confidence < self.confidence_threshold:
            return {'signal': 'HOLD', 'confidence': confidence, 'reason': 'low_confidence'}

        # Session filter
        if self.use_session_filter:
            hour = int(row['hour'].values[0])
            if not ((8 <= hour < 16) or (13 <= hour < 21)):
                return {'signal': 'HOLD', 'confidence': confidence, 'reason': 'outside_session'}

        # Volatility filter
        if self.use_volatility_filter:
            vol_low = float(row['vol_regime_low'].values[0])
            vol_high = float(row['vol_regime_high'].values[0])

            if vol_low == 1 or vol_high == 1:
                return {'signal': 'HOLD', 'confidence': confidence, 'reason': 'extreme_volatility'}

        # All filters passed - generate signal
        signal = "SELL" if pred_class == 1 else "BUY"
        close_price = float(row['close'].values[0])
        atr = float(row['atr'].values[0])

        # Calculate entry, SL, TP
        spread_cost = self.spread_pips / 10000 * close_price

        if signal == "BUY":
            entry_price = close_price + spread_cost
            tp_price = entry_price + (atr * self.take_profit_atr)
            sl_price = entry_price - (atr * self.stop_loss_atr)
        else:  # SELL
            entry_price = close_price - spread_cost
            tp_price = entry_price - (atr * self.take_profit_atr)
            sl_price = entry_price + (atr * self.stop_loss_atr)

        return {
            'signal': signal,
            'confidence': confidence,
            'entry_price': entry_price,
            'tp_price': tp_price,
            'sl_price': sl_price,
        }

    def _check_exit(self, position: Dict, current_bar: pd.Series, current_time: datetime) -> tuple:
        """Check if position should be exited."""
        current_price = current_bar['close']

        # Check stop loss
        if position['direction'] == 'BUY':
            if current_price <= position['stop_loss']:
                return True, 'stop_loss'
            if current_price >= position['take_profit']:
                return True, 'take_profit'
        else:  # SELL
            if current_price >= position['stop_loss']:
                return True, 'stop_loss'
            if current_price <= position['take_profit']:
                return True, 'take_profit'

        # Check max holding time
        holding_hours = (current_time - position['entry_time']).total_seconds() / 3600
        if holding_hours >= self.max_holding_hours:
            return True, 'max_holding_time'

        return False, None

    def _calculate_pnl(self, position: Dict, exit_price: float) -> float:
        """Calculate PnL for a position."""
        lot_size = position['lot_size']
        entry = position['entry_price']

        if position['direction'] == 'BUY':
            pnl = (exit_price - entry) * 100000 * lot_size  # 1 pip = 0.0001 for Gold
        else:  # SELL
            pnl = (entry - exit_price) * 100000 * lot_size

        return pnl

    def _calculate_metrics(self, trades: List[Dict], equity_curve: List[float], final_balance: float) -> Dict[str, Any]:
        """Calculate backtest metrics."""
        if len(trades) == 0:
            return self._empty_metrics()

        # Separate winning and losing trades
        winning_trades = [t for t in trades if t['pnl'] > 0]
        losing_trades = [t for t in trades if t['pnl'] < 0]

        total_wins = sum(t['pnl'] for t in winning_trades)
        total_losses = abs(sum(t['pnl'] for t in losing_trades))

        # Calculate metrics
        total_trades = len(trades)
        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0

        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0
        avg_win = (total_wins / win_count) if win_count > 0 else 0
        avg_loss = (total_losses / loss_count) if loss_count > 0 else 0

        net_profit = final_balance - self.initial_balance

        # Drawdown
        equity_array = np.array(equity_curve)
        running_max = np.maximum.accumulate(equity_array)
        drawdown = (equity_array - running_max) / running_max * 100
        max_drawdown = abs(drawdown.min())

        # Count TP/SL hits
        tp_hits = len([t for t in trades if t['exit_reason'] == 'take_profit'])
        sl_hits = len([t for t in trades if t['exit_reason'] == 'stop_loss'])
        tp_rate = (tp_hits / total_trades * 100) if total_trades > 0 else 0

        return {
            'net_profit': round(net_profit, 2),
            'total_trades': total_trades,
            'winning_trades': win_count,
            'losing_trades': loss_count,
            'win_rate': round(win_rate, 1),
            'profit_factor': round(profit_factor, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'max_drawdown': round(max_drawdown, 2),
            'tp_hit_rate': round(tp_rate, 1),
            'tp_hits': tp_hits,
            'sl_hits': sl_hits,
        }

    def _empty_results(self) -> Dict[str, Any]:
        """Return empty results structure."""
        return {
            'trades': [],
            'equity_curve': [self.initial_balance],
            'metrics': self._empty_metrics(),
            'config': {},
        }

    def _empty_metrics(self) -> Dict[str, Any]:
        """Return empty metrics structure."""
        return {
            'net_profit': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'max_drawdown': 0.0,
            'tp_hit_rate': 0.0,
            'tp_hits': 0,
            'sl_hits': 0,
        }


def run_default_backtest(
    start_date: str = "2024-01-01",
    end_date: Optional[str] = None,
    verbose: bool = True,
) -> Dict[str, Any]:
    """
    Run default backtest for ML profitable strategy.

    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD), defaults to latest
        verbose: Print results to console

    Returns:
        Backtest results with trades, equity curve, and metrics
    """
    backtest = MLStrategyBacktest()
    results = backtest.run_backtest(start_date=start_date, end_date=end_date)

    if verbose:
        print("=" * 70)
        print("ML PROFITABLE STRATEGY - BACKTEST RESULTS")
        print("=" * 70)
        print()
        print(f"Period: {results['config'].get('start_date', 'N/A')} to {results['config'].get('end_date', 'N/A')}")
        print(f"Initial Balance: ${results['config']['initial_balance']:,.2f}")
        print(f"Final Balance: ${results['config']['final_balance']:,.2f}")
        print()
        print("📊 Performance Metrics:")
        metrics = results['metrics']
        print(f"  • Total Trades: {metrics['total_trades']}")
        print(f"  • Winning Trades: {metrics['winning_trades']}")
        print(f"  • Losing Trades: {metrics['losing_trades']}")
        print(f"  • Win Rate: {metrics['win_rate']:.1f}%")
        print(f"  • Profit Factor: {metrics['profit_factor']:.2f}")
        print(f"  • Net Profit: ${metrics['net_profit']:.2f}")
        print(f"  • Avg Win: ${metrics['avg_win']:.2f}")
        print(f"  • Avg Loss: ${metrics['avg_loss']:.2f}")
        print(f"  • Max Drawdown: {metrics['max_drawdown']:.2f}%")
        print(f"  • TP Hit Rate: {metrics['tp_hit_rate']:.1f}%")
        print()

        if metrics['profit_factor'] >= 1.5 and metrics['win_rate'] >= 60:
            print("✅ STRATEGY IS PROFITABLE AND READY FOR DEPLOYMENT")
        elif metrics['profit_factor'] >= 1.0:
            print("⚠️  STRATEGY IS PROFITABLE BUT NEEDS OPTIMIZATION")
        else:
            print("❌ STRATEGY IS NOT PROFITABLE - DO NOT DEPLOY")

        print("=" * 70)

    return results


if __name__ == "__main__":
    # Run backtest
    results = run_default_backtest(start_date="2024-01-01", verbose=True)
