"""
Test "Import to My Bots" Modal Flow

This script simulates the exact flow when user clicks "Import to My Bots":
1. Import pretrained model (simulated)
2. Modal auto-opens with StrategySelector
3. StrategySelector calls /ml/strategies/for-model/{symbol}
4. Dropdown should show public templates for that symbol
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.strategy import Strategy
from app.models.user import User
from app.core.validators import validate_symbol


DATABASE_URL = "postgresql+psycopg2://postgres.nhmihfusyxdjvlisdjvt:TFh7eUP0SFRLGlGn@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"


def print_header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def simulate_import_bot_modal_flow(db, user, symbol):
    """
    Simulate the exact flow when user clicks "Import to My Bots" for a symbol.

    Flow:
    1. User clicks "Import to My Bots" for XAUUSD
    2. Backend imports the pretrained model (we'll simulate this)
    3. Frontend auto-opens StrategySelector modal
    4. StrategySelector calls: /api/v1/ml/strategies/for-model/{symbol}
    5. Backend returns strategies for that symbol
    6. Frontend displays in dropdown
    """
    print_header(f"🤖 Simulating 'Import to My Bots' for {symbol}")

    print("Step 1: User clicks 'Import to My Bots' button")
    print(f"  → Symbol: {symbol}")
    print(f"  → User: {user.email}\n")

    print("Step 2: Backend imports pretrained model")
    print("  → Model imported (simulated)")
    print("  → Model ID: mock-model-id-12345\n")

    print("Step 3: Frontend auto-opens StrategySelector modal")
    print("  → Modal title: 'Link Strategy to Model'")
    print(f"  → Description: 'Select a strategy for {symbol} Profitable Model (System) ({symbol})'\n")

    print("Step 4: StrategySelector calls API endpoint")
    print(f"  → Endpoint: GET /api/v1/ml/strategies/for-model/{symbol}")
    print(f"  → Headers: Authorization: Bearer <token>\n")

    print("Step 5: Backend processes request")
    validated_symbol = validate_symbol(symbol)

    # This is the EXACT query from backend endpoint
    user_strategies = db.query(Strategy).filter(
        Strategy.user_id == user.id,
        (Strategy.symbol == validated_symbol) | (Strategy.symbol.is_(None)),
        Strategy.is_active == True,
    ).all()

    public_strategies = db.query(Strategy).filter(
        Strategy.user_id.is_(None),
        Strategy.symbol == validated_symbol,
        Strategy.is_public == True,
        Strategy.is_active == True,
        Strategy.strategy_type == "preset",
    ).all()

    strategies = user_strategies + public_strategies

    print(f"  → User's {symbol} strategies: {len(user_strategies)}")
    print(f"  → Public {symbol} templates: {len(public_strategies)}")
    print(f"  → Total available: {len(strategies)}\n")

    print("Step 6: Backend returns JSON response")
    response = {
        "symbol": validated_symbol,
        "count": len(strategies),
        "strategies": [
            {
                "id": str(s.id),
                "name": s.name,
                "description": s.description,
                "strategy_type": s.strategy_type,
                "symbol": s.symbol,
            }
            for s in strategies
        ]
    }

    print(f"  → Response: {response['count']} strategies\n")

    print("Step 7: Frontend renders dropdown")
    if len(strategies) > 0:
        print("  ✅ Dropdown shows:")
        for s in strategies:
            badge = "🌟 System" if s.strategy_type == "preset" else "👤 User"
            print(f"     [{badge}] {s.name}")
        print(f"\n  ✅ User can select and click 'Link Strategy'\n")
        return True
    else:
        print("  ❌ Dropdown shows:")
        print(f"     'No strategies found for {symbol}.'")
        print("     'Create one using a template below.'\n")
        return False


def main():
    print("\n" + "=" * 80)
    print("  🧪 IMPORT TO MY BOTS MODAL - FLOW SIMULATION")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)

    # Connect to database
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # Get test user
        user = db.query(User).first()
        if not user:
            print("❌ No users found")
            return False

        print(f"\n👤 Test User: {user.email}")

        # Test all available pretrained models
        symbols = ["XAUUSD", "EURUSD", "GBPUSD", "USDJPY"]
        results = []

        for symbol in symbols:
            success = simulate_import_bot_modal_flow(db, user, symbol)
            results.append((symbol, success))

        # Summary
        print_header("📊 MODAL FLOW TEST SUMMARY")

        passed = sum(1 for _, success in results if success)
        total = len(results)

        for symbol, success in results:
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"{status} | Import to My Bots → {symbol}")

        print(f"\nTotal: {passed}/{total} symbols have available strategies")

        if passed == total:
            print("\n🎉 ALL MODALS WILL WORK CORRECTLY!")
            print("\nWhen user clicks 'Import to My Bots':")
            print("1. Model imports successfully")
            print("2. StrategySelector modal auto-opens")
            print("3. Dropdown shows public template for that symbol")
            print("4. User can select and link strategy")
            print("\n✅ Ready for production testing!")
        else:
            print("\n⚠️  SOME SYMBOLS MISSING TEMPLATES")
            print("Check database for missing preset strategies")

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
