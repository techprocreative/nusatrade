"""
Quick Production Test - Non-interactive
Run with: PROD_TOKEN=your_token python3 test_production_quick.py
"""

import requests
import json
import os
import sys
from datetime import datetime


BACKEND_URL = "https://nusatrade.onrender.com"


def test_strategies_endpoint(token):
    """Test /api/v1/strategies endpoint"""
    print("\n" + "=" * 80)
    print("  📋 Testing GET /api/v1/strategies")
    print("=" * 80)

    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/strategies", headers=headers, timeout=10)

        print(f"Status: {response.status_code}")

        if response.status_code == 401:
            print("❌ Authentication failed - token invalid or expired")
            return False

        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False

        data = response.json()

        print(f"✅ Success - Returned {len(data)} strategies\n")

        # Analyze strategies
        presets = [s for s in data if s.get('strategy_type') == 'preset']
        user_strats = [s for s in data if s.get('strategy_type') != 'preset']

        print(f"📦 Public Templates: {len(presets)}")
        for s in presets:
            print(f"   ✓ {s.get('symbol', 'N/A'):8} | {s.get('name', 'N/A')[:60]}")

        if user_strats:
            print(f"\n👤 User Strategies: {len(user_strats)}")
            for s in user_strats[:3]:
                print(f"   - {s.get('name', 'N/A')} ({s.get('symbol', 'N/A')})")

        if len(presets) >= 4:
            print(f"\n✅ PASS - Found {len(presets)}/4 public templates")
            return True
        else:
            print(f"\n❌ FAIL - Only {len(presets)}/4 public templates found")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_strategies_for_model(token, symbol="XAUUSD"):
    """Test /api/v1/ml/strategies/for-model/{symbol} endpoint"""
    print("\n" + "=" * 80)
    print(f"  🎯 Testing GET /api/v1/ml/strategies/for-model/{symbol}")
    print("=" * 80)

    headers = {"Authorization": f"Bearer {token}"}
    url = f"{BACKEND_URL}/api/v1/ml/strategies/for-model/{symbol}"

    try:
        response = requests.get(url, headers=headers, timeout=10)

        print(f"URL: {url}")
        print(f"Status: {response.status_code}")

        if response.status_code == 401:
            print("❌ Authentication failed")
            return False

        if response.status_code != 200:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False

        data = response.json()

        print(f"\n📊 Response Structure:")
        print(f"   Symbol: {data.get('symbol', 'N/A')}")
        print(f"   Count: {data.get('count', 0)}")

        strategies = data.get('strategies', [])
        print(f"   Strategies: {len(strategies)}\n")

        if len(strategies) == 0:
            print("❌ EMPTY - No strategies returned!")
            print("\nThis is the problem! Backend query is not finding strategies.")
            print("\nPossible causes:")
            print("1. Render deployment not complete")
            print("2. Database missing templates")
            print("3. Query logic issue in production")
            return False

        print(f"📦 Strategies for {symbol}:")
        for s in strategies:
            stype = s.get('strategy_type', 'unknown')
            badge = "🌟" if stype == 'preset' else "👤"
            print(f"   {badge} {s.get('name', 'N/A')}")
            print(f"      Type: {stype}, Active: {s.get('is_active', False)}")

        if len(strategies) >= 1:
            print(f"\n✅ PASS - Found {len(strategies)} strategy/strategies for {symbol}")
            return True
        else:
            print(f"\n❌ FAIL - No strategies for {symbol}")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run production tests"""
    print("\n" + "=" * 80)
    print("  🧪 PRODUCTION API QUICK TEST")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("  Backend: " + BACKEND_URL)
    print("=" * 80)

    # Get token from environment
    token = os.environ.get('PROD_TOKEN')

    if not token:
        print("\n❌ ERROR: No token provided")
        print("Usage: PROD_TOKEN=your_token python3 test_production_quick.py")
        print("\nTo get your token:")
        print("1. Open: https://nusatrade-beta.vercel.app")
        print("2. Login to your account")
        print("3. Open browser console (F12)")
        print("4. Run: localStorage.getItem('token')")
        print("5. Copy the token (without quotes)")
        return False

    print(f"\n✅ Token found (length: {len(token)})")

    # Test 1: List strategies
    result1 = test_strategies_endpoint(token)

    # Test 2: Strategies for XAUUSD
    result2 = test_strategies_for_model(token, "XAUUSD")

    # Test 3: Try other symbols
    print("\n" + "=" * 80)
    print("  🔍 Testing Other Symbols")
    print("=" * 80)
    for symbol in ["EURUSD", "GBPUSD", "USDJPY"]:
        test_strategies_for_model(token, symbol)

    # Summary
    print("\n" + "=" * 80)
    print("  📊 DIAGNOSTIC SUMMARY")
    print("=" * 80)

    if result1 and result2:
        print("✅ All tests passed - strategies are being returned correctly")
        print("\nIf modal still shows empty, the issue is in frontend:")
        print("1. Clear browser cache (Ctrl+Shift+R)")
        print("2. Check browser console for errors")
        print("3. Verify Vercel deployed latest frontend code")
    elif result1 and not result2:
        print("⚠️  /strategies works but /ml/strategies/for-model/{symbol} fails")
        print("\nThis means:")
        print("1. Backend deployed but has a bug in symbol-specific endpoint")
        print("2. Or Render deployed old code (check Render dashboard)")
    elif not result1:
        print("❌ Backend not returning strategies at all")
        print("\nThis means:")
        print("1. Database missing public templates")
        print("2. Or Render deployed old code without fixes")
        print("3. Check Render deployment logs")
    else:
        print("⚠️  Mixed results - further investigation needed")

    print("=" * 80 + "\n")

    return result1 and result2


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user.")
        sys.exit(1)
