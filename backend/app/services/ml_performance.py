"""
ML Model Performance Tracking and Validation.

CRITICAL FOR PROFITABILITY:
This module tracks REAL trading performance (not just accuracy).
Monitors:
- Win rate (% profitable trades)
- Profit factor (gross profit / gross loss)
- Sharpe ratio (risk-adjusted returns)
- Maximum drawdown
- Average trade duration

Triggers model retraining when performance degrades.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.logging import get_logger
from app.models.trade import Trade
from app.models.ml import MLModel

logger = get_logger(__name__)


@dataclass
class ModelPerformanceMetrics:
    """Performance metrics for ML model."""
    model_id: str
    model_name: str

    # Trading metrics
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float  # %

    # Profitability
    gross_profit: float
    gross_loss: float
    net_profit: float
    profit_factor: float  # gross_profit / abs(gross_loss)
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float

    # Risk metrics
    sharpe_ratio: Optional[float]
    max_drawdown: float  # %
    max_consecutive_losses: int

    # Additional metrics
    average_trade_duration_hours: float
    total_pips: float

    # Time period
    period_start: datetime
    period_end: datetime
    days_active: int

    # ML-specific
    average_confidence: float
    confidence_vs_outcome_correlation: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def is_profitable(self) -> bool:
        """Check if model is profitable."""
        return self.net_profit > 0 and self.profit_factor > 1.0

    def needs_retraining(self) -> bool:
        """
        Determine if model needs retraining based on performance degradation.

        Retraining triggers:
        - Win rate < 40%
        - Profit factor < 1.0 (losing money)
        - Max drawdown > 20%
        - Negative net profit over last 20 trades
        """
        if self.total_trades < 20:
            return False  # Not enough data

        if self.win_rate < 40.0:
            logger.warning(f"Model {self.model_name}: Win rate {self.win_rate:.1f}% < 40%")
            return True

        if self.profit_factor < 1.0:
            logger.warning(f"Model {self.model_name}: Profit factor {self.profit_factor:.2f} < 1.0")
            return True

        if self.max_drawdown > 20.0:
            logger.warning(f"Model {self.model_name}: Max drawdown {self.max_drawdown:.1f}% > 20%")
            return True

        if self.net_profit < 0:
            logger.warning(f"Model {self.model_name}: Net profit ${self.net_profit:.2f} < 0")
            return True

        return False


class MLPerformanceTracker:
    """Track ML model performance on REAL trades."""

    def __init__(self, db: Session):
        self.db = db

    def calculate_performance(
        self,
        model_id: str,
        days_back: int = 30,
        min_trades: int = 10,
    ) -> Optional[ModelPerformanceMetrics]:
        """
        Calculate performance metrics for ML model based on actual trades.

        Args:
            model_id: ML model UUID
            days_back: How many days of history to analyze
            min_trades: Minimum trades required for analysis

        Returns:
            ModelPerformanceMetrics or None if insufficient data
        """
        # Get model
        model = self.db.query(MLModel).filter(MLModel.id == model_id).first()
        if not model:
            logger.error(f"Model {model_id} not found")
            return None

        # Get trades executed by this model
        period_start = datetime.utcnow() - timedelta(days=days_back)

        trades = self.db.query(Trade).filter(
            Trade.ml_model_id == model_id,
            Trade.source == "auto_trading",
            Trade.close_time.isnot(None),  # Only closed trades
            Trade.open_time >= period_start,
        ).all()

        if len(trades) < min_trades:
            logger.info(f"Model {model.name}: Insufficient trades ({len(trades)} < {min_trades})")
            return None

        # Calculate metrics
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if float(t.profit or 0) > 0)
        losing_trades = sum(1 for t in trades if float(t.profit or 0) < 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0

        profits = [float(t.profit or 0) for t in trades]
        gross_profit = sum(p for p in profits if p > 0)
        gross_loss = sum(p for p in profits if p < 0)
        net_profit = sum(profits)

        profit_factor = (gross_profit / abs(gross_loss)) if gross_loss != 0 else 0

        wins = [p for p in profits if p > 0]
        losses = [p for p in profits if p < 0]
        average_win = np.mean(wins) if wins else 0
        average_loss = np.mean(losses) if losses else 0
        largest_win = max(wins) if wins else 0
        largest_loss = min(losses) if losses else 0

        # Sharpe ratio (simplified: daily returns / std dev)
        sharpe_ratio = self._calculate_sharpe_ratio(profits)

        # Max drawdown
        max_drawdown = self._calculate_max_drawdown(profits)

        # Max consecutive losses
        max_consecutive_losses = self._calculate_max_consecutive_losses(profits)

        # Average trade duration
        durations = []
        for trade in trades:
            if trade.close_time and trade.open_time:
                duration = (trade.close_time - trade.open_time).total_seconds() / 3600
                durations.append(duration)
        average_duration = np.mean(durations) if durations else 0

        # Calculate pips (simplified - assumes standard lot)
        total_pips = sum(self._calculate_pips(t) for t in trades)

        # ML-specific: confidence vs outcome
        confidences = []
        outcomes = []
        for trade in trades:
            # Get prediction that generated this trade
            from app.models.ml import MLPrediction
            prediction = self.db.query(MLPrediction).filter(
                MLPrediction.model_id == model_id,
                MLPrediction.created_at <= trade.open_time,
                MLPrediction.created_at >= trade.open_time - timedelta(minutes=5),
            ).first()

            if prediction and prediction.prediction:
                conf = prediction.prediction.get("confidence", 0)
                confidences.append(conf)
                outcomes.append(1 if float(trade.profit or 0) > 0 else 0)

        average_confidence = np.mean(confidences) if confidences else 0

        # Correlation between confidence and outcome
        if len(confidences) >= 10:
            correlation = np.corrcoef(confidences, outcomes)[0, 1]
        else:
            correlation = 0

        period_end = datetime.utcnow()
        days_active = (period_end - period_start).days

        metrics = ModelPerformanceMetrics(
            model_id=str(model_id),
            model_name=model.name,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=round(win_rate, 2),
            gross_profit=round(gross_profit, 2),
            gross_loss=round(gross_loss, 2),
            net_profit=round(net_profit, 2),
            profit_factor=round(profit_factor, 2),
            average_win=round(average_win, 2),
            average_loss=round(average_loss, 2),
            largest_win=round(largest_win, 2),
            largest_loss=round(largest_loss, 2),
            sharpe_ratio=round(sharpe_ratio, 2) if sharpe_ratio else None,
            max_drawdown=round(max_drawdown, 2),
            max_consecutive_losses=max_consecutive_losses,
            average_trade_duration_hours=round(average_duration, 2),
            total_pips=round(total_pips, 1),
            period_start=period_start,
            period_end=period_end,
            days_active=days_active,
            average_confidence=round(average_confidence, 4),
            confidence_vs_outcome_correlation=round(correlation, 4),
        )

        # Log performance summary
        logger.info(
            f"Model {model.name} performance ({days_back}d): "
            f"Win Rate={metrics.win_rate:.1f}%, "
            f"Profit Factor={metrics.profit_factor:.2f}, "
            f"Net Profit=${metrics.net_profit:.2f}, "
            f"Sharpe={metrics.sharpe_ratio}, "
            f"Drawdown={metrics.max_drawdown:.1f}%"
        )

        # Check if needs retraining
        if metrics.needs_retraining():
            logger.warning(f"⚠️ Model {model.name} needs retraining!")

        return metrics

    def _calculate_sharpe_ratio(self, profits: List[float]) -> Optional[float]:
        """Calculate Sharpe ratio (annualized)."""
        if len(profits) < 10:
            return None

        returns = np.array(profits)
        mean_return = np.mean(returns)
        std_return = np.std(returns)

        if std_return == 0:
            return None

        # Simplified Sharpe (assuming daily data, annualize with sqrt(252))
        sharpe = (mean_return / std_return) * np.sqrt(252)
        return sharpe

    def _calculate_max_drawdown(self, profits: List[float]) -> float:
        """Calculate maximum drawdown percentage."""
        if not profits:
            return 0

        cumulative = np.cumsum(profits)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = running_max - cumulative

        max_dd = np.max(drawdown)

        # Convert to percentage of peak
        if len(running_max) > 0 and running_max[-1] > 0:
            max_dd_pct = (max_dd / running_max[-1]) * 100
        else:
            max_dd_pct = 0

        return max_dd_pct

    def _calculate_max_consecutive_losses(self, profits: List[float]) -> int:
        """Calculate maximum consecutive losing trades."""
        if not profits:
            return 0

        max_consecutive = 0
        current_consecutive = 0

        for profit in profits:
            if profit < 0:
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        return max_consecutive

    def _calculate_pips(self, trade: Trade) -> float:
        """Calculate profit in pips (simplified)."""
        if not trade.close_price or not trade.open_price:
            return 0

        price_diff = float(trade.close_price) - float(trade.open_price)

        if trade.trade_type == "SELL":
            price_diff = -price_diff

        # Convert to pips (assuming 4-decimal pairs like EURUSD)
        pips = price_diff * 10000

        return pips

    def get_all_models_performance(
        self,
        days_back: int = 30,
        min_trades: int = 10,
    ) -> List[ModelPerformanceMetrics]:
        """Get performance for all active models."""
        active_models = self.db.query(MLModel).filter(
            MLModel.is_active == True,
            MLModel.file_path.isnot(None),
        ).all()

        results = []
        for model in active_models:
            metrics = self.calculate_performance(
                model_id=model.id,
                days_back=days_back,
                min_trades=min_trades,
            )
            if metrics:
                results.append(metrics)

        # Sort by profit factor (best first)
        results.sort(key=lambda x: x.profit_factor, reverse=True)

        return results

    def get_performance_summary(self, days_back: int = 30) -> Dict[str, Any]:
        """Get summary of all models' performance."""
        all_metrics = self.get_all_models_performance(days_back=days_back)

        if not all_metrics:
            return {
                "total_models": 0,
                "profitable_models": 0,
                "models_needing_retraining": 0,
                "average_win_rate": 0,
                "average_profit_factor": 0,
                "total_net_profit": 0,
            }

        summary = {
            "total_models": len(all_metrics),
            "profitable_models": sum(1 for m in all_metrics if m.is_profitable()),
            "models_needing_retraining": sum(1 for m in all_metrics if m.needs_retraining()),
            "average_win_rate": round(np.mean([m.win_rate for m in all_metrics]), 2),
            "average_profit_factor": round(np.mean([m.profit_factor for m in all_metrics]), 2),
            "total_net_profit": round(sum(m.net_profit for m in all_metrics), 2),
            "best_model": all_metrics[0].model_name if all_metrics else None,
            "best_profit_factor": all_metrics[0].profit_factor if all_metrics else 0,
        }

        return summary
