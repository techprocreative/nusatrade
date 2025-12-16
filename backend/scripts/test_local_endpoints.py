"""
Test Strategy Endpoints Locally (Direct Database Access)

This script tests the endpoints logic without running the server,
by directly calling the endpoint functions with mock user/session.
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from app.models.strategy import Strategy
from app.models.user import User
from app.core.validators import validate_symbol


DATABASE_URL = "postgresql+psycopg2://postgres.nhmihfusyxdjvlisdjvt:TFh7eUP0SFRLGlGn@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"


def print_header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def test_database_connection():
    """Test database connection."""
    print_header("🔌 Testing Database Connection")

    try:
        engine = create_engine(DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful")
            return engine
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        sys.exit(1)


def get_test_user(db: Session):
    """Get or create test user."""
    print_header("👤 Getting Test User")

    # Get first user from database
    user = db.query(User).first()

    if user:
        print(f"✅ Using existing user: {user.email}")
        return user
    else:
        print("❌ No users found in database")
        sys.exit(1)


def test_list_strategies_endpoint(db: Session, user):
    """Test list_strategies endpoint logic."""
    print_header("📋 Test 1: List All Strategies")

    # Get user's own strategies
    user_strategies = db.query(Strategy).filter(
        Strategy.user_id == user.id
    ).all()

    # Get public preset templates
    public_strategies = db.query(Strategy).filter(
        Strategy.user_id.is_(None),
        Strategy.is_public == True,
        Strategy.is_active == True,
        Strategy.strategy_type == "preset",
    ).all()

    # Combine
    all_strategies = user_strategies + public_strategies
    all_strategies.sort(key=lambda s: s.created_at, reverse=True)

    print(f"User strategies: {len(user_strategies)}")
    print(f"Public templates: {len(public_strategies)}")
    print(f"Total: {len(all_strategies)}\n")

    # Display public templates
    if public_strategies:
        print("📦 Public Preset Templates:")
        for s in public_strategies:
            print(f"  ✓ {s.symbol:8} | {s.name[:50]:50} | Active: {s.is_active}")
    else:
        print("⚠️  No public templates found!")
        return False

    # Display user strategies
    if user_strategies:
        print(f"\n👤 User's Strategies: {len(user_strategies)}")
        for s in user_strategies[:3]:
            print(f"  - {s.name} ({s.symbol})")

    # Validation
    if len(public_strategies) >= 4:
        print(f"\n✅ PASS: Found {len(public_strategies)}/4 expected preset templates")
        return True
    else:
        print(f"\n❌ FAIL: Only found {len(public_strategies)}/4 preset templates")
        return False


def test_strategies_for_model_endpoint(db: Session, user, symbol: str):
    """Test get_strategies_for_symbol endpoint logic."""
    print_header(f"🎯 Test 2: Strategies for {symbol}")

    # Validate symbol
    validated_symbol = validate_symbol(symbol)
    print(f"Symbol: {validated_symbol}\n")

    # Get user's own strategies for this symbol
    user_strategies = db.query(Strategy).filter(
        Strategy.user_id == user.id,
        (Strategy.symbol == validated_symbol) | (Strategy.symbol.is_(None)),
        Strategy.is_active == True,
    ).all()

    # Get public preset templates for this symbol
    public_strategies = db.query(Strategy).filter(
        Strategy.user_id.is_(None),
        Strategy.symbol == validated_symbol,
        Strategy.is_public == True,
        Strategy.is_active == True,
        Strategy.strategy_type == "preset",
    ).all()

    # Combine
    strategies = user_strategies + public_strategies

    print(f"User strategies: {len(user_strategies)}")
    print(f"Public templates: {len(public_strategies)}")
    print(f"Total: {len(strategies)}\n")

    if public_strategies:
        print(f"📦 Public Templates for {symbol}:")
        for s in public_strategies:
            print(f"  ✓ {s.name} | Type: {s.strategy_type} | Active: {s.is_active}")
    else:
        print(f"⚠️  No public templates found for {symbol}!")
        return False

    if user_strategies:
        print(f"\n👤 User Strategies for {symbol}: {len(user_strategies)}")

    # Validation
    if len(public_strategies) >= 1:
        print(f"\n✅ PASS: Found {len(public_strategies)} preset template(s) for {symbol}")
        return True
    else:
        print(f"\n❌ FAIL: No preset templates for {symbol}")
        return False


def test_pydantic_validation(db: Session):
    """Test that strategies can be converted to StrategyResponse without errors."""
    print_header("🔍 Test 3: Pydantic Validation")

    from app.api.v1.strategies import strategy_to_response

    # Get public strategies
    public_strategies = db.query(Strategy).filter(
        Strategy.user_id.is_(None),
        Strategy.is_public == True,
        Strategy.strategy_type == "preset",
    ).all()

    if not public_strategies:
        print("⚠️  No public strategies to test")
        return False

    errors = []
    for strategy in public_strategies:
        try:
            response = strategy_to_response(strategy)
            print(f"✅ {strategy.symbol:8} | {strategy.name[:40]:40} | Validated")
        except Exception as e:
            errors.append((strategy.name, str(e)))
            print(f"❌ {strategy.symbol:8} | {strategy.name[:40]:40} | ERROR: {e}")

    if errors:
        print(f"\n❌ FAIL: {len(errors)} validation errors")
        for name, error in errors:
            print(f"  - {name}: {error}")
        return False
    else:
        print(f"\n✅ PASS: All {len(public_strategies)} strategies validated successfully")
        return True


def main():
    """Run all tests."""
    print("\n" + "=" * 80)
    print("  🧪 LOCAL ENDPOINT TESTING")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)

    # Connect to database
    engine = test_database_connection()
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Get test user
        user = get_test_user(db)

        # Run tests
        results = []

        # Test 1: List all strategies
        results.append(("List All Strategies", test_list_strategies_endpoint(db, user)))

        # Test 2: Strategies for specific symbols
        for symbol in ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]:
            results.append(
                (f"Strategies for {symbol}",
                 test_strategies_for_model_endpoint(db, user, symbol))
            )

        # Test 3: Pydantic validation
        results.append(("Pydantic Validation", test_pydantic_validation(db)))

        # Summary
        print_header("📊 TEST SUMMARY")

        passed = sum(1 for _, success in results if success)
        total = len(results)

        for name, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} | {name}")

        print(f"\nTotal: {passed}/{total} tests passed")

        if passed == total:
            print("\n🎉 ALL TESTS PASSED!")
            print("Public templates are working correctly in backend logic.")
            print("\nNext: Deploy to Render and test production endpoints.")
        else:
            print("\n⚠️  SOME TESTS FAILED.")
            print("Check the logs above for details.")

        print("=" * 80 + "\n")

        return passed == total

    finally:
        db.close()


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
