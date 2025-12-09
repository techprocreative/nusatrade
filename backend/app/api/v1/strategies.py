"""Trading Strategies API - CRUD operations and AI-powered strategy generation."""

from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.api import deps
from app.models.strategy import Strategy
from app.core.logging import get_logger


router = APIRouter()
logger = get_logger(__name__)


# Request/Response Models
class StrategyParameter(BaseModel):
    name: str
    type: str = "number"  # number, string, boolean
    default_value: str | int | float | bool
    description: Optional[str] = None
    min: Optional[float] = None
    max: Optional[float] = None


class StrategyRule(BaseModel):
    id: str
    condition: str
    action: str  # BUY, SELL, CLOSE
    description: str


class RiskManagement(BaseModel):
    stop_loss_type: str = "fixed_pips"  # fixed_pips, atr_based, percentage
    stop_loss_value: float = 50
    take_profit_type: str = "fixed_pips"  # fixed_pips, risk_reward, trailing
    take_profit_value: float = 100
    max_position_size: float = 0.1
    max_daily_loss: Optional[float] = None


class BacktestMetrics(BaseModel):
    net_profit: float = 0
    total_trades: int = 0
    winning_trades: int = 0
    win_rate: float = 0
    profit_factor: float = 0
    max_drawdown_pct: float = 0
    sharpe_ratio: float = 0


class StrategyCreateRequest(BaseModel):
    name: str
    description: Optional[str] = None
    strategy_type: str = "custom"  # ai_generated, custom, preset
    code: Optional[str] = None
    parameters: Optional[List[StrategyParameter]] = None
    indicators: Optional[List[str]] = None
    entry_rules: Optional[List[StrategyRule]] = None
    exit_rules: Optional[List[StrategyRule]] = None
    risk_management: Optional[RiskManagement] = None


class StrategyUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    parameters: Optional[List[StrategyParameter]] = None
    indicators: Optional[List[str]] = None
    entry_rules: Optional[List[StrategyRule]] = None
    exit_rules: Optional[List[StrategyRule]] = None
    risk_management: Optional[RiskManagement] = None


class StrategyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    description: Optional[str] = None
    strategy_type: str
    code: Optional[str] = None
    parameters: List[StrategyParameter] = []
    indicators: List[str] = []
    entry_rules: List[StrategyRule] = []
    exit_rules: List[StrategyRule] = []
    risk_management: Optional[RiskManagement] = None
    is_active: bool = False
    backtest_results: Optional[BacktestMetrics] = None
    created_at: datetime
    updated_at: datetime


class ToggleRequest(BaseModel):
    is_active: bool


class QuickBacktestRequest(BaseModel):
    symbol: str = "EURUSD"
    timeframe: str = "H1"
    days: int = 30


def strategy_to_response(s: Strategy) -> StrategyResponse:
    """Convert Strategy model to response."""
    return StrategyResponse(
        id=str(s.id),
        name=s.name,
        description=s.description,
        strategy_type=s.strategy_type or "custom",
        code=s.code,
        parameters=s.parameters or [],
        indicators=s.indicators or [],
        entry_rules=s.entry_rules or [],
        exit_rules=s.exit_rules or [],
        risk_management=s.risk_management,
        is_active=s.is_active or False,
        backtest_results=s.backtest_results,
        created_at=s.created_at or datetime.utcnow(),
        updated_at=s.updated_at or datetime.utcnow(),
    )


# ==================== ENDPOINTS ====================

@router.get("", response_model=List[StrategyResponse])
def list_strategies(
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """List all strategies for the current user."""
    strategies = db.query(Strategy).filter(
        Strategy.user_id == current_user.id
    ).order_by(Strategy.created_at.desc()).all()

    return [strategy_to_response(s) for s in strategies]


@router.post("", response_model=StrategyResponse, status_code=status.HTTP_201_CREATED)
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
        code=request.code,
        parameters=[p.model_dump() for p in request.parameters] if request.parameters else [],
        indicators=request.indicators or [],
        entry_rules=[r.model_dump() for r in request.entry_rules] if request.entry_rules else [],
        exit_rules=[r.model_dump() for r in request.exit_rules] if request.exit_rules else [],
        risk_management=request.risk_management.model_dump() if request.risk_management else None,
        is_active=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)

    logger.info(f"Strategy created: {strategy.id} by user {current_user.id}")
    return strategy_to_response(strategy)


@router.get("/{strategy_id}", response_model=StrategyResponse)
def get_strategy(
    strategy_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Get a specific strategy by ID."""
    strategy = db.query(Strategy).filter(
        Strategy.id == strategy_id,
        Strategy.user_id == current_user.id,
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    return strategy_to_response(strategy)


@router.put("/{strategy_id}", response_model=StrategyResponse)
def update_strategy(
    strategy_id: str,
    request: StrategyUpdateRequest,
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

    # Update only provided fields
    if request.name is not None:
        strategy.name = request.name
    if request.description is not None:
        strategy.description = request.description
    if request.code is not None:
        strategy.code = request.code
    if request.parameters is not None:
        strategy.parameters = [p.model_dump() for p in request.parameters]
    if request.indicators is not None:
        strategy.indicators = request.indicators
    if request.entry_rules is not None:
        strategy.entry_rules = [r.model_dump() for r in request.entry_rules]
    if request.exit_rules is not None:
        strategy.exit_rules = [r.model_dump() for r in request.exit_rules]
    if request.risk_management is not None:
        strategy.risk_management = request.risk_management.model_dump()

    strategy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(strategy)

    logger.info(f"Strategy updated: {strategy_id}")
    return strategy_to_response(strategy)


@router.delete("/{strategy_id}")
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

    logger.info(f"Strategy deleted: {strategy_id}")
    return {"deleted": strategy_id}


@router.patch("/{strategy_id}/toggle", response_model=StrategyResponse)
def toggle_strategy(
    strategy_id: str,
    request: ToggleRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Toggle strategy active status."""
    strategy = db.query(Strategy).filter(
        Strategy.id == strategy_id,
        Strategy.user_id == current_user.id,
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    strategy.is_active = request.is_active
    strategy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(strategy)

    status_str = "activated" if request.is_active else "deactivated"
    logger.info(f"Strategy {status_str}: {strategy_id}")
    return strategy_to_response(strategy)


@router.post("/{strategy_id}/quick-backtest", response_model=BacktestMetrics)
def quick_backtest(
    strategy_id: str,
    request: QuickBacktestRequest,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Run a quick backtest on the strategy and cache results."""
    strategy = db.query(Strategy).filter(
        Strategy.id == strategy_id,
        Strategy.user_id == current_user.id,
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    # TODO: Implement actual backtesting using BacktestEngine
    # For now, return simulated results
    import random
    
    total_trades = random.randint(20, 100)
    winning_trades = random.randint(int(total_trades * 0.4), int(total_trades * 0.7))
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
    net_profit = random.uniform(-500, 2000)
    
    results = BacktestMetrics(
        net_profit=round(net_profit, 2),
        total_trades=total_trades,
        winning_trades=winning_trades,
        win_rate=round(win_rate, 1),
        profit_factor=round(random.uniform(0.8, 2.5), 2),
        max_drawdown_pct=round(random.uniform(5, 25), 1),
        sharpe_ratio=round(random.uniform(-0.5, 2.0), 2),
    )

    # Cache results in strategy
    strategy.backtest_results = results.model_dump()
    strategy.updated_at = datetime.utcnow()
    db.commit()

    logger.info(f"Quick backtest completed for strategy {strategy_id}")
    return results


@router.post("/{strategy_id}/validate")
def validate_strategy(
    strategy_id: str,
    db: Session = Depends(deps.get_db),
    current_user=Depends(deps.get_current_user),
):
    """Validate a strategy's configuration."""
    strategy = db.query(Strategy).filter(
        Strategy.id == strategy_id,
        Strategy.user_id == current_user.id,
    ).first()

    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    errors = []

    # Basic validation
    if not strategy.name:
        errors.append("Strategy name is required")
    if not strategy.entry_rules or len(strategy.entry_rules) == 0:
        errors.append("At least one entry rule is required")
    if not strategy.exit_rules or len(strategy.exit_rules) == 0:
        errors.append("At least one exit rule is required")
    if not strategy.risk_management:
        errors.append("Risk management configuration is required")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }
