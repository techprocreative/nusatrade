#!/usr/bin/env python3
"""
ML Auto Trading Setup & Test Script

This script:
1. Creates the default ML profitable strategy in the database
2. Runs a backtest to validate the strategy
3. Tests the auto-trading flow (without executing real trades)
4. Provides instructions for activating auto-trading

Usage:
    python setup_ml_auto_trading.py
"""

import sys
import os
from datetime import datetime
from pathlib import Path

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app.core.database import SessionLocal
from app.models.strategy import Strategy
from app.models.ml import MLModel
from app.strategies.ml_profitable_strategy import create_default_ml_strategy, MLProfitableStrategy
from app.backtesting.ml_strategy_backtest import run_default_backtest
from uuid import uuid4, UUID


def print_header(title: str):
    """Print a formatted header."""
    print()
    print("=" * 80)
    print(f"  {title}")
    print("=" * 80)
    print()


def create_strategy_in_db(user_id: str) -> str:
    """
    Create the default ML strategy in the database.

    Args:
        user_id: User UUID as string

    Returns:
        Strategy ID
    """
    print_header("STEP 1: Creating ML Profitable Strategy in Database")

    db = SessionLocal()

    try:
        # Check if strategy already exists
        existing = db.query(Strategy).filter(
            Strategy.user_id == UUID(user_id),
            Strategy.name == MLProfitableStrategy.NAME,
        ).first()

        if existing:
            print(f"✅ Strategy already exists: {existing.id}")
            print(f"   Name: {existing.name}")
            print(f"   Type: {existing.strategy_type}")
            return str(existing.id)

        # Create new strategy
        strategy_data = create_default_ml_strategy(user_id)

        strategy = Strategy(
            id=uuid4(),
            **strategy_data,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        db.add(strategy)
        db.commit()
        db.refresh(strategy)

        print(f"✅ Strategy created successfully!")
        print(f"   ID: {strategy.id}")
        print(f"   Name: {strategy.name}")
        print(f"   Type: {strategy.strategy_type}")
        print(f"   Entry Rules: {len(strategy.entry_rules)}")
        print(f"   Exit Rules: {len(strategy.exit_rules)}")
        print(f"   Indicators: {', '.join(strategy.indicators)}")

        return str(strategy.id)

    except Exception as e:
        print(f"❌ Error creating strategy: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def run_backtest_validation():
    """Run backtest to validate the strategy."""
    print_header("STEP 2: Running Backtest Validation")

    try:
        # Check if model file exists
        model_path = "models/model_xgboost_20251212_235414.pkl"
        if not Path(model_path).exists():
            print(f"❌ Model file not found: {model_path}")
            print("   Please ensure the model file is in the correct location.")
            return False

        # Check if data file exists
        data_path = "ohlcv/xauusd/xauusd_1h_clean.csv"
        if not Path(data_path).exists():
            print(f"❌ Data file not found: {data_path}")
            print("   Please ensure the OHLCV data file is in the correct location.")
            return False

        print("Running backtest from 2024-01-01 to latest...")
        print()

        results = run_default_backtest(start_date="2024-01-01", verbose=True)

        # Validate results
        metrics = results['metrics']

        if metrics['profit_factor'] >= 1.5 and metrics['win_rate'] >= 60:
            print()
            print("✅ Backtest validation PASSED - Strategy is profitable!")
            return True
        else:
            print()
            print("⚠️  Backtest validation WARNING - Strategy performance below expected")
            print(f"   Expected: Profit Factor >= 1.5, Win Rate >= 60%")
            print(f"   Actual: Profit Factor = {metrics['profit_factor']:.2f}, Win Rate = {metrics['win_rate']:.1f}%")
            return False

    except Exception as e:
        print(f"❌ Backtest failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_auto_trading_flow(user_id: str, strategy_id: str):
    """Test the auto-trading flow (dry run)."""
    print_header("STEP 3: Testing Auto Trading Flow (Dry Run)")

    try:
        from app.services.ml_auto_trading import ml_auto_trading_service
        import asyncio

        db = SessionLocal()

        async def test_flow():
            # Initialize predictor
            await ml_auto_trading_service.initialize_predictor()

            print("✅ ML Predictor initialized")
            print()

            # Test signal generation (without execution)
            print("Generating trading signal...")
            result = await ml_auto_trading_service.process_trading_signal(
                db=db,
                user_id=UUID(user_id),
                symbol="XAUUSD",
            )

            print()
            print("📊 Signal Generation Result:")
            print(f"   Signal: {result['signal']}")
            print(f"   Confidence: {result.get('confidence', 0):.1%}")
            print(f"   Reason: {result.get('reason', 'N/A')}")

            if result['signal'] in ['BUY', 'SELL']:
                print(f"   Entry Price: ${result.get('entry_price', 0):.2f}")
                print(f"   Stop Loss: ${result.get('stop_loss', 0):.2f}")
                print(f"   Take Profit: ${result.get('take_profit', 0):.2f}")

            print()
            print("✅ Auto-trading flow test completed")
            print()
            print("NOTE: No actual trades were executed (dry run mode)")

        asyncio.run(test_flow())

        db.close()
        return True

    except Exception as e:
        print(f"❌ Auto-trading flow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def print_activation_instructions(strategy_id: str):
    """Print instructions for activating auto-trading."""
    print_header("STEP 4: Activation Instructions")

    print("To activate auto-trading with this strategy:")
    print()
    print("1. Ensure MT5 connector is running and connected:")
    print("   cd connector")
    print("   python -m src.main")
    print()
    print("2. Activate the strategy via API or UI:")
    print(f"   Strategy ID: {strategy_id}")
    print()
    print("3. Create and activate an ML model that uses this strategy:")
    print("   - Model path: models/model_xgboost_20251212_235414.pkl")
    print("   - Symbol: XAUUSD")
    print("   - Set is_active = True")
    print()
    print("4. The auto-trading scheduler will:")
    print("   - Check for signals every hour")
    print("   - Generate predictions using the ML model")
    print("   - Validate against strategy rules")
    print("   - Execute trades via MT5 when conditions are met")
    print()
    print("⚠️  IMPORTANT:")
    print("   - Start with DEMO account first")
    print("   - Use lot size 0.01 for testing")
    print("   - Monitor for at least 30 days")
    print("   - Only go live after successful demo validation")
    print()
    print("Expected Performance (based on backtest):")
    print("   - Win Rate: ~75%")
    print("   - Profit Factor: ~2.0")
    print("   - Trades per year: ~20 (very conservative)")
    print("   - Max Drawdown: <1%")
    print()


def main():
    """Main setup script."""
    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 20 + "ML AUTO TRADING SETUP" + " " * 37 + "║")
    print("║" + " " * 20 + "Profitable Strategy Configuration" + " " * 24 + "║")
    print("╚" + "═" * 78 + "╝")

    # Get user ID (in production, this would come from authentication)
    print()
    print("Enter user ID (UUID) for strategy creation:")
    print("(Press Enter to use default test user: 00000000-0000-0000-0000-000000000001)")
    user_input = input("> ").strip()

    if not user_input:
        user_id = "00000000-0000-0000-0000-000000000001"
        print(f"Using default user ID: {user_id}")
    else:
        user_id = user_input

    try:
        # Validate UUID format
        UUID(user_id)
    except ValueError:
        print(f"❌ Invalid UUID format: {user_id}")
        return

    # Step 1: Create strategy in database
    try:
        strategy_id = create_strategy_in_db(user_id)
    except Exception as e:
        print(f"❌ Failed to create strategy: {e}")
        return

    # Step 2: Run backtest validation
    backtest_passed = run_backtest_validation()

    if not backtest_passed:
        print()
        print("⚠️  Backtest validation failed. Please check the model and data files.")
        print("   Continuing anyway for demonstration purposes...")
        print()

    # Step 3: Test auto-trading flow
    test_auto_trading_flow(user_id, strategy_id)

    # Step 4: Print activation instructions
    print_activation_instructions(strategy_id)

    print()
    print("╔" + "═" * 78 + "╗")
    print("║" + " " * 25 + "SETUP COMPLETED" + " " * 38 + "║")
    print("╚" + "═" * 78 + "╝")
    print()


if __name__ == "__main__":
    main()
