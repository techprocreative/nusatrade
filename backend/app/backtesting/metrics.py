"""Performance metrics calculation for backtesting results."""

import math
from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd
import numpy as np


@dataclass
class BacktestMetrics:
    """Container for all backtest performance metrics."""
    
    # Basic stats
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    break_even_trades: int = 0
    
    # Profit/Loss
    net_profit: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    
    # Ratios
    win_rate: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    
    # Averages
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_trade: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    
    # Drawdown
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    avg_drawdown: float = 0.0
    max_drawdown_duration: int = 0  # in bars
    
    # Risk-adjusted returns
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Time-based
    total_bars: int = 0
    bars_in_market: int = 0
    market_exposure: float = 0.0
    
    # Equity curve
    equity_curve: List[float] = None
    drawdown_curve: List[float] = None
    
    def __post_init__(self):
        if self.equity_curve is None:
            self.equity_curve = []
        if self.drawdown_curve is None:
            self.drawdown_curve = []

    def to_dict(self) -> Dict:
        """Convert metrics to dictionary."""
        return {
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "net_profit": round(self.net_profit, 2),
            "gross_profit": round(self.gross_profit, 2),
            "gross_loss": round(self.gross_loss, 2),
            "win_rate": round(self.win_rate, 2),
            "profit_factor": round(self.profit_factor, 2),
            "expectancy": round(self.expectancy, 2),
            "avg_win": round(self.avg_win, 2),
            "avg_loss": round(self.avg_loss, 2),
            "avg_trade": round(self.avg_trade, 2),
            "largest_win": round(self.largest_win, 2),
            "largest_loss": round(self.largest_loss, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "max_drawdown_pct": round(self.max_drawdown_pct, 2),
            "sharpe_ratio": round(self.sharpe_ratio, 2),
            "sortino_ratio": round(self.sortino_ratio, 2),
            "calmar_ratio": round(self.calmar_ratio, 2),
            "market_exposure": round(self.market_exposure, 2),
        }


def calculate_metrics(
    trades: List[Dict],
    equity_curve: List[float],
    initial_balance: float,
    risk_free_rate: float = 0.02,
) -> BacktestMetrics:
    """Calculate all performance metrics from backtest results."""
    
    metrics = BacktestMetrics()
    
    if not trades:
        metrics.equity_curve = [initial_balance]
        return metrics
    
    # Basic trade counts
    profits = [t.get("profit", 0) for t in trades]
    metrics.total_trades = len(trades)
    metrics.winning_trades = sum(1 for p in profits if p > 0)
    metrics.losing_trades = sum(1 for p in profits if p < 0)
    metrics.break_even_trades = sum(1 for p in profits if p == 0)
    
    # Profit/Loss calculations
    metrics.net_profit = sum(profits)
    metrics.gross_profit = sum(p for p in profits if p > 0)
    metrics.gross_loss = abs(sum(p for p in profits if p < 0))
    
    # Win rate
    if metrics.total_trades > 0:
        metrics.win_rate = (metrics.winning_trades / metrics.total_trades) * 100
    
    # Profit factor
    if metrics.gross_loss > 0:
        metrics.profit_factor = metrics.gross_profit / metrics.gross_loss
    elif metrics.gross_profit > 0:
        metrics.profit_factor = float("inf")
    
    # Averages
    winning_profits = [p for p in profits if p > 0]
    losing_profits = [p for p in profits if p < 0]
    
    if winning_profits:
        metrics.avg_win = sum(winning_profits) / len(winning_profits)
        metrics.largest_win = max(winning_profits)
    
    if losing_profits:
        metrics.avg_loss = abs(sum(losing_profits) / len(losing_profits))
        metrics.largest_loss = abs(min(losing_profits))
    
    if metrics.total_trades > 0:
        metrics.avg_trade = metrics.net_profit / metrics.total_trades
    
    # Expectancy
    if metrics.total_trades > 0:
        metrics.expectancy = (
            (metrics.win_rate / 100) * metrics.avg_win -
            ((100 - metrics.win_rate) / 100) * metrics.avg_loss
        )
    
    # Equity curve and drawdown
    if equity_curve:
        metrics.equity_curve = equity_curve
        metrics.drawdown_curve, metrics.max_drawdown, metrics.max_drawdown_pct = \
            _calculate_drawdown(equity_curve)
        metrics.avg_drawdown = sum(metrics.drawdown_curve) / len(metrics.drawdown_curve) if metrics.drawdown_curve else 0
    
    # Risk-adjusted ratios
    if equity_curve and len(equity_curve) > 1:
        returns = _calculate_returns(equity_curve)
        metrics.sharpe_ratio = _calculate_sharpe(returns, risk_free_rate)
        metrics.sortino_ratio = _calculate_sortino(returns, risk_free_rate)
        
        if metrics.max_drawdown_pct > 0:
            total_return = (equity_curve[-1] - equity_curve[0]) / equity_curve[0] * 100
            metrics.calmar_ratio = total_return / metrics.max_drawdown_pct
    
    # Market exposure
    total_bars = len(equity_curve) if equity_curve else 0
    bars_in_market = sum(t.get("bars_held", 1) for t in trades)
    if total_bars > 0:
        metrics.market_exposure = (bars_in_market / total_bars) * 100
    
    metrics.total_bars = total_bars
    metrics.bars_in_market = bars_in_market
    
    return metrics


def _calculate_drawdown(equity_curve: List[float]) -> tuple:
    """Calculate drawdown curve and max drawdown."""
    if not equity_curve:
        return [], 0.0, 0.0
    
    peak = equity_curve[0]
    drawdown_curve = []
    max_dd = 0.0
    max_dd_pct = 0.0
    
    for equity in equity_curve:
        if equity > peak:
            peak = equity
        
        dd = peak - equity
        dd_pct = (dd / peak * 100) if peak > 0 else 0
        
        drawdown_curve.append(dd)
        
        if dd > max_dd:
            max_dd = dd
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct
    
    return drawdown_curve, max_dd, max_dd_pct


def _calculate_returns(equity_curve: List[float]) -> List[float]:
    """Calculate period returns from equity curve."""
    returns = []
    for i in range(1, len(equity_curve)):
        if equity_curve[i - 1] != 0:
            ret = (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
            returns.append(ret)
    return returns


def _calculate_sharpe(returns: List[float], risk_free_rate: float = 0.02) -> float:
    """Calculate Sharpe ratio."""
    if not returns or len(returns) < 2:
        return 0.0
    
    # Annualize assuming daily returns
    periods_per_year = 252
    excess_returns = [r - (risk_free_rate / periods_per_year) for r in returns]
    
    mean_return = np.mean(excess_returns)
    std_return = np.std(excess_returns, ddof=1)
    
    if std_return == 0:
        return 0.0
    
    return (mean_return / std_return) * math.sqrt(periods_per_year)


def _calculate_sortino(returns: List[float], risk_free_rate: float = 0.02) -> float:
    """Calculate Sortino ratio (uses downside deviation)."""
    if not returns or len(returns) < 2:
        return 0.0
    
    periods_per_year = 252
    target_return = risk_free_rate / periods_per_year
    
    mean_return = np.mean(returns)
    downside_returns = [min(0, r - target_return) for r in returns]
    downside_std = np.std(downside_returns, ddof=1)
    
    if downside_std == 0:
        return 0.0
    
    return ((mean_return - target_return) / downside_std) * math.sqrt(periods_per_year)
