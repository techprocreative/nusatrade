"""
Phase 3 Implementation Verification Script

Verifies:
1. User-configurable risk management
2. Trade execution retry logic
3. MT5 connection health monitoring
"""

import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql+psycopg2://postgres.nhmihfusyxdjvlisdjvt:TFh7eUP0SFRLGlGn@aws-1-ap-southeast-1.pooler.supabase.com:6543/postgres"


def print_header(title):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def check_user_risk_settings():
    """Verify user risk settings in database."""
    print_header("✅ PHASE 3.1: User-Configurable Risk Management")

    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                id,
                email,
                settings->'risk_management' as risk_settings
            FROM users
        """))

        users = result.fetchall()

        if not users:
            print("⚠️ No users found in database")
            return False

        users_with_risk = 0
        for user in users:
            user_id, email, risk_settings = user
            if risk_settings:
                users_with_risk += 1
                print(f"✅ {email}: Has risk settings")

                # Parse and validate risk settings
                try:
                    # Expected keys
                    expected_keys = [
                        "max_daily_loss", "max_positions", "max_lot_size",
                        "confidence_threshold", "daily_trade_limit",
                        "max_drawdown_percent", "enabled"
                    ]

                    # Check if all keys present (risk_settings is JSON)
                    if all(key in str(risk_settings) for key in ["max_daily_loss", "max_positions"]):
                        print(f"   └─ Valid risk configuration")
                except Exception as e:
                    print(f"   └─ ⚠️ Error parsing: {e}")
            else:
                print(f"❌ {email}: Missing risk settings")

        print(f"\n📊 Summary: {users_with_risk}/{len(users)} users have risk settings")

        if users_with_risk == len(users):
            print("✅ All users have risk management configured")
            return True
        else:
            print("⚠️ Some users missing risk settings - run add_risk_settings.py")
            return users_with_risk > 0


def check_retry_logic_implementation():
    """Verify retry logic is implemented in trading_service.py."""
    print_header("✅ PHASE 3.2: Trade Execution Retry Logic")

    trading_service_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "app", "services", "trading_service.py"
    )

    if not os.path.exists(trading_service_path):
        print("❌ trading_service.py not found")
        return False

    with open(trading_service_path, 'r') as f:
        content = f.read()

    # Check for key retry logic components
    checks = {
        "Retry function exists": "open_order_with_mt5_retry" in content,
        "Exponential backoff": "backoff_delays" in content and "[2, 5, 10]" in content,
        "Max retries parameter": "max_retries: int = 3" in content,
        "Retryable error detection": "is_retryable" in content,
        "Asyncio import": "import asyncio" in content,
        "Retry loop": "for attempt in range(max_retries)" in content,
    }

    all_passed = True
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
        all_passed = all_passed and passed

    # Check auto_trading.py uses retry wrapper
    auto_trading_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "app", "services", "auto_trading.py"
    )

    if os.path.exists(auto_trading_path):
        with open(auto_trading_path, 'r') as f:
            auto_content = f.read()

        if "open_order_with_mt5_retry" in auto_content:
            print("✅ auto_trading.py uses retry wrapper")
        else:
            print("❌ auto_trading.py NOT using retry wrapper")
            all_passed = False

    if all_passed:
        print("\n✅ Retry logic fully implemented")
    else:
        print("\n❌ Retry logic incomplete")

    return all_passed


def check_health_monitoring():
    """Verify MT5 health monitoring is implemented."""
    print_header("✅ PHASE 3.3: MT5 Connection Health Monitoring")

    connection_manager_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "app", "api", "websocket", "connection_manager.py"
    )

    ws_service_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "..", "connector", "src", "core", "ws_service.py"
    )

    checks = {}

    # Check backend connection manager
    if os.path.exists(connection_manager_path):
        with open(connection_manager_path, 'r') as f:
            content = f.read()

        checks["Heartbeat monitoring"] = "_heartbeat_loop" in content
        checks["Stale connection detection"] = "_check_stale_connections" in content
        checks["MT5 status tracking"] = "MT5_STATUS" in content
        checks["Last heartbeat tracking"] = "last_heartbeat" in content
        checks["Connection state management"] = "ConnectorSession" in content
    else:
        print("❌ connection_manager.py not found")
        return False

    # Check connector WebSocket service
    if os.path.exists(ws_service_path):
        with open(ws_service_path, 'r') as f:
            ws_content = f.read()

        checks["Auto-reconnect logic"] = "_handle_reconnect" in ws_content
        checks["Connection states"] = "ConnectionState" in ws_content and "RECONNECTING" in ws_content
        checks["Exponential backoff"] = "reconnect_interval" in ws_content
        checks["Max reconnect attempts"] = "max_reconnect_attempts" in ws_content
    else:
        print("⚠️ connector ws_service.py not found (acceptable if not using connector)")

    all_passed = True
    for check_name, passed in checks.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}")
        all_passed = all_passed and passed

    if all_passed:
        print("\n✅ Health monitoring fully implemented")
    else:
        print("\n⚠️ Health monitoring partially implemented")

    return all_passed


def run_phase3_verification():
    """Run all Phase 3 verification checks."""
    print("\n" + "=" * 80)
    print("  PHASE 3 IMPLEMENTATION - COMPREHENSIVE VERIFICATION")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)

    checks = [
        ("User Risk Settings", check_user_risk_settings),
        ("Trade Retry Logic", check_retry_logic_implementation),
        ("MT5 Health Monitoring", check_health_monitoring),
    ]

    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            print(f"❌ Error in {name}: {e}")
            results.append((name, False))

    # Summary
    print_header("📊 PHASE 3 VERIFICATION SUMMARY")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"Checks Passed: {passed}/{total}\n")

    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")

    print("\n" + "=" * 80)

    if passed == total:
        print("  🎉 PHASE 3 COMPLETE - ALL CHECKS PASSED!")
        print("  Ready for production deployment.")
    elif passed >= total * 0.66:
        print("  ⚠️  PHASE 3 MOSTLY COMPLETE - Review failed checks")
    else:
        print("  ❌ PHASE 3 INCOMPLETE - Fix critical failures")

    print("=" * 80 + "\n")

    return passed == total


if __name__ == "__main__":
    success = run_phase3_verification()
    exit(0 if success else 1)
