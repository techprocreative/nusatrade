"""Backtesting API - Strategy management, backtest execution, and results."""

from datetime import datetime, date
from decimal import Decimal
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api import deps
from app.models.backtest import BacktestSession, BacktestResult
from app.models.strategy import Strategy
from app.backtesting.engine import BacktestEngine, BacktestConfig
from app.backtesting.data_manager import DataManager
from app.backtesting.metrics import calculate_metrics
from app.core.logging import get_logger


logger = get_logger(__name__)

router = APIRouter()


# Request/Response Models
class StrategyCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    strategy_type: str = "ma_crossover"  # ma_crossover, rsi, macd, custom
    config: Optional[dict] = None
    is_public: bool = False


class StrategyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    description: Optional[str]
    strategy_type: str
    config: Optional[dict]
    is_public: bool
    created_at: datetime


class BacktestRunRequest(BaseModel):
    strategy_id: str
    symbol: str = "EURUSD"
    timeframe: str = "H1"
    start_date: str  # YYYY-MM-DD
    end_date: str  # YYYY-MM-DD
    initial_balance: float = 10000.0
    commission: float = 0.0
    slippage: float = 0.0001


class BacktestResultResponse(BaseModel):
    session_id: str
    status: str
    net_profit: Optional[float]
    total_trades: Optional[int]
    win_rate: Optional[float]
    profit_factor: Optional[float]
    max_drawdown_pct: Optional[float]
    sharpe_ratio: Optional[float]
    created_at: datetime


class SessionResponse(BaseModel):
    id: str
    strategy_id: str
    symbol: str
    timeframe: str
    start_date: date
    end_date: date
    initial_balance: float
    status: str
    created_at: datetime
    result: Optional[BacktestResultResponse] = None


# Strategy Endpoints
@router.get("/strategies", response_model=List[StrategyResponse])
def list_strategies(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
    include_public: bool = True,
):
    """List strategies for current user and optionally public ones."""
    query = db.query(Strategy).filter(
        (Strategy.user_id == current_user.id) |
        (Strategy.is_public == True if include_public else False)
    )
    strategies = query.all()

    return [
        StrategyResponse(
            id=str(s.id),
            name=s.name,
            description=s.description,
            strategy_type=s.strategy_type or "custom",
            config=s.config,
            is_public=s.is_public or False,
            created_at=s.created_at or datetime.utcnow(),
        )
        for s in strategies
    ]


@router.post("/strategies", response_model=StrategyResponse)
def create_strategy(
    request: StrategyCreateRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Create a new trading strategy."""
    strategy = Strategy(
        id=uuid4(),
        user_id=current_user.id,
        name=request.name,
        description=request.description,
        strategy_type=request.strategy_type,
        config=request.config or {},
        is_public=request.is_public,
        created_at=datetime.utcnow(),
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)

    return StrategyResponse(
        id=str(strategy.id),
        name=strategy.name,
        description=strategy.description,
        strategy_type=strategy.strategy_type,
        config=strategy.config,
        is_public=strategy.is_public,
        created_at=strategy.created_at,
    )


@router.get("/strategies/{strategy_id}", response_model=StrategyResponse)
def get_strategy(
    strategy_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Get a specific strategy."""
    strategy = db.query(Strategy).filter(
        Strategy.id == strategy_id,
        (Strategy.user_id == current_user.id) | (Strategy.is_public == True),
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    return StrategyResponse(
        id=str(strategy.id),
        name=strategy.name,
        description=strategy.description,
        strategy_type=strategy.strategy_type or "custom",
        config=strategy.config,
        is_public=strategy.is_public or False,
        created_at=strategy.created_at or datetime.utcnow(),
    )


@router.put("/strategies/{strategy_id}", response_model=StrategyResponse)
def update_strategy(
    strategy_id: str,
    request: StrategyCreateRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Update a strategy."""
    strategy = db.query(Strategy).filter(
        Strategy.id == strategy_id,
        Strategy.user_id == current_user.id,
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    strategy.name = request.name
    strategy.description = request.description
    strategy.strategy_type = request.strategy_type
    strategy.config = request.config or {}
    strategy.is_public = request.is_public
    strategy.updated_at = datetime.utcnow()
    db.commit()

    return StrategyResponse(
        id=str(strategy.id),
        name=strategy.name,
        description=strategy.description,
        strategy_type=strategy.strategy_type,
        config=strategy.config,
        is_public=strategy.is_public,
        created_at=strategy.created_at or datetime.utcnow(),
    )


@router.delete("/strategies/{strategy_id}")
def delete_strategy(
    strategy_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Delete a strategy."""
    strategy = db.query(Strategy).filter(
        Strategy.id == strategy_id,
        Strategy.user_id == current_user.id,
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    db.delete(strategy)
    db.commit()

    return {"deleted": strategy_id}


# Backtest Execution Endpoints
@router.post("/run", response_model=BacktestResultResponse)
def run_backtest(
    request: BacktestRunRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Run a backtest synchronously and return results."""
    # Verify strategy exists
    strategy = db.query(Strategy).filter(
        Strategy.id == request.strategy_id,
        (Strategy.user_id == current_user.id) | (Strategy.is_public == True),
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # Create session
    session = BacktestSession(
        id=uuid4(),
        user_id=current_user.id,
        strategy_id=strategy.id,
        symbol=request.symbol,
        timeframe=request.timeframe,
        start_date=datetime.strptime(request.start_date, "%Y-%m-%d").date(),
        end_date=datetime.strptime(request.end_date, "%Y-%m-%d").date(),
        initial_balance=Decimal(str(request.initial_balance)),
        config={
            "commission": request.commission,
            "slippage": request.slippage,
        },
        status="running",
        created_at=datetime.utcnow(),
    )
    db.add(session)
    db.commit()

    try:
        # Try to load data from database cache or download from yfinance
        import pandas as pd
        import numpy as np
        
        data_manager = DataManager(
            symbol=request.symbol,
            timeframe=request.timeframe,
            start_date=datetime.strptime(request.start_date, "%Y-%m-%d"),
            end_date=datetime.strptime(request.end_date, "%Y-%m-%d"),
        )
        
        try:
            # Use load_or_download: checks DB first, downloads from yfinance if not cached
            df = data_manager.load_or_download(db)
            logger.info(f"Loaded {len(df)} candles for {request.symbol} {request.timeframe}")
        except Exception as data_error:
            # Fallback to sample data if both DB and yfinance fail
            logger.warning(f"Failed to load data: {data_error}. Using sample data.")
            n_bars = 500
            dates = pd.date_range(start=request.start_date, end=request.end_date, periods=n_bars)
            base_price = 1.0850 if "USD" in request.symbol else 100.0
            
            np.random.seed(42)
            returns = np.random.randn(n_bars) * 0.001
            close_prices = base_price * np.exp(np.cumsum(returns))
            
            df = pd.DataFrame({
                "timestamp": dates,
                "open": close_prices * (1 + np.random.randn(n_bars) * 0.0005),
                "high": close_prices * (1 + abs(np.random.randn(n_bars) * 0.001)),
                "low": close_prices * (1 - abs(np.random.randn(n_bars) * 0.001)),
                "close": close_prices,
                "volume": np.random.randint(1000, 10000, n_bars),
            })

        # Create backtest config
        config = BacktestConfig(
            initial_balance=request.initial_balance,
            commission=request.commission,
            slippage=request.slippage,
        )

        # Create strategy instance based on type
        from app.backtesting.strategies.ma_crossover import MACrossoverStrategy, RSIStrategy
        
        if strategy.strategy_type == "rsi":
            bt_strategy = RSIStrategy(**(strategy.config or {}))
        else:
            bt_strategy = MACrossoverStrategy(**(strategy.config or {}))

        # Run backtest
        engine = BacktestEngine(config)
        result_data = engine.run(df, bt_strategy)

        # Calculate metrics
        metrics = calculate_metrics(result_data["trades"], result_data["equity_curve"])

        # Save result
        result = BacktestResult(
            id=uuid4(),
            session_id=session.id,
            net_profit=Decimal(str(metrics.net_profit)),
            total_trades=metrics.total_trades,
            winning_trades=metrics.winning_trades,
            losing_trades=metrics.losing_trades,
            win_rate=Decimal(str(metrics.win_rate)),
            profit_factor=Decimal(str(metrics.profit_factor)) if metrics.profit_factor else None,
            max_drawdown=Decimal(str(metrics.max_drawdown)),
            max_drawdown_pct=Decimal(str(metrics.max_drawdown_pct)),
            sharpe_ratio=Decimal(str(metrics.sharpe_ratio)) if metrics.sharpe_ratio else None,
            sortino_ratio=Decimal(str(metrics.sortino_ratio)) if metrics.sortino_ratio else None,
            calmar_ratio=Decimal(str(metrics.calmar_ratio)) if metrics.calmar_ratio else None,
            expectancy=Decimal(str(metrics.expectancy)) if metrics.expectancy else None,
            avg_win=Decimal(str(metrics.avg_win)) if metrics.avg_win else None,
            avg_loss=Decimal(str(metrics.avg_loss)) if metrics.avg_loss else None,
            equity_curve=result_data["equity_curve"],
            trades=[
                {
                    "symbol": t.symbol,
                    "order_type": t.order_type.value,
                    "entry_price": t.entry_price,
                    "exit_price": t.exit_price,
                    "profit": t.profit,
                }
                for t in result_data["trades"][:100]  # Limit stored trades
            ],
            created_at=datetime.utcnow(),
        )
        db.add(result)

        session.status = "completed"
        db.commit()

        return BacktestResultResponse(
            session_id=str(session.id),
            status="completed",
            net_profit=metrics.net_profit,
            total_trades=metrics.total_trades,
            win_rate=metrics.win_rate,
            profit_factor=metrics.profit_factor,
            max_drawdown_pct=metrics.max_drawdown_pct,
            sharpe_ratio=metrics.sharpe_ratio,
            created_at=session.created_at,
        )

    except Exception as e:
        session.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Backtest failed: {str(e)}")


@router.get("/sessions", response_model=List[SessionResponse])
def list_sessions(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
    limit: int = 20,
):
    """List backtest sessions for current user."""
    sessions = db.query(BacktestSession).filter(
        BacktestSession.user_id == current_user.id
    ).order_by(BacktestSession.created_at.desc()).limit(limit).all()

    result = []
    for s in sessions:
        # Get result if exists
        bt_result = db.query(BacktestResult).filter(
            BacktestResult.session_id == s.id
        ).first()

        result_response = None
        if bt_result:
            result_response = BacktestResultResponse(
                session_id=str(s.id),
                status=s.status or "unknown",
                net_profit=float(bt_result.net_profit) if bt_result.net_profit else None,
                total_trades=bt_result.total_trades,
                win_rate=float(bt_result.win_rate) if bt_result.win_rate else None,
                profit_factor=float(bt_result.profit_factor) if bt_result.profit_factor else None,
                max_drawdown_pct=float(bt_result.max_drawdown_pct) if bt_result.max_drawdown_pct else None,
                sharpe_ratio=float(bt_result.sharpe_ratio) if bt_result.sharpe_ratio else None,
                created_at=bt_result.created_at or datetime.utcnow(),
            )

        result.append(SessionResponse(
            id=str(s.id),
            strategy_id=str(s.strategy_id),
            symbol=s.symbol or "UNKNOWN",
            timeframe=s.timeframe or "H1",
            start_date=s.start_date or date.today(),
            end_date=s.end_date or date.today(),
            initial_balance=float(s.initial_balance) if s.initial_balance else 10000,
            status=s.status or "unknown",
            created_at=s.created_at or datetime.utcnow(),
            result=result_response,
        ))

    return result


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Get a specific backtest session with results."""
    session = db.query(BacktestSession).filter(
        BacktestSession.id == session_id,
        BacktestSession.user_id == current_user.id,
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Get result
    bt_result = db.query(BacktestResult).filter(
        BacktestResult.session_id == session.id
    ).first()

    result_response = None
    if bt_result:
        result_response = BacktestResultResponse(
            session_id=str(session.id),
            status=session.status or "unknown",
            net_profit=float(bt_result.net_profit) if bt_result.net_profit else None,
            total_trades=bt_result.total_trades,
            win_rate=float(bt_result.win_rate) if bt_result.win_rate else None,
            profit_factor=float(bt_result.profit_factor) if bt_result.profit_factor else None,
            max_drawdown_pct=float(bt_result.max_drawdown_pct) if bt_result.max_drawdown_pct else None,
            sharpe_ratio=float(bt_result.sharpe_ratio) if bt_result.sharpe_ratio else None,
            created_at=bt_result.created_at or datetime.utcnow(),
        )

    return SessionResponse(
        id=str(session.id),
        strategy_id=str(session.strategy_id),
        symbol=session.symbol or "UNKNOWN",
        timeframe=session.timeframe or "H1",
        start_date=session.start_date or date.today(),
        end_date=session.end_date or date.today(),
        initial_balance=float(session.initial_balance) if session.initial_balance else 10000,
        status=session.status or "unknown",
        created_at=session.created_at or datetime.utcnow(),
        result=result_response,
    )


@router.get("/sessions/{session_id}/trades")
def get_session_trades(
    session_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Get trades from a backtest session."""
    session = db.query(BacktestSession).filter(
        BacktestSession.id == session_id,
        BacktestSession.user_id == current_user.id,
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    result = db.query(BacktestResult).filter(
        BacktestResult.session_id == session_id
    ).first()

    if not result:
        return {"trades": [], "equity_curve": []}

    return {
        "trades": result.trades or [],
        "equity_curve": result.equity_curve or [],
    }


@router.post("/optimize")
def run_optimization(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Run strategy parameter optimization (placeholder for advanced feature)."""
    return {
        "status": "not_implemented",
        "message": "Strategy optimization coming soon. Use manual parameter tuning via backtest runs.",
    }
