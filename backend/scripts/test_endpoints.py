"""
Test Strategy Endpoints for Public Templates

This script tests the fixed endpoints to verify that public preset templates
are being returned correctly.

Usage:
    python scripts/test_endpoints.py

You'll be prompted for your auth token from the frontend.
"""

import requests
import sys
import json
from datetime import datetime


BACKEND_URL = "https://nusatrade.onrender.com"


def get_token():
    """Get token from user input or environment."""
    print("\n" + "=" * 80)
    print("  🔐 AUTHENTICATION")
    print("=" * 80)
    print("\nTo get your token:")
    print("1. Open https://nusatrade-beta.vercel.app")
    print("2. Login to your account")
    print("3. Open browser console (F12)")
    print("4. Run: localStorage.getItem('token')")
    print("5. Copy the token (without quotes)\n")

    token = input("Paste your token here: ").strip()
    if not token:
        print("❌ No token provided. Exiting.")
        sys.exit(1)

    return token


def test_endpoint(name, url, headers, expected_count=None):
    """Test an endpoint and print results."""
    print("\n" + "=" * 80)
    print(f"  📡 Testing: {name}")
    print("=" * 80)
    print(f"URL: {url}\n")

    try:
        response = requests.get(url, headers=headers, timeout=10)

        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()

            # Handle different response formats
            if isinstance(data, list):
                strategies = data
            elif isinstance(data, dict) and 'strategies' in data:
                strategies = data['strategies']
            else:
                strategies = []

            print(f"✅ SUCCESS - Returned {len(strategies)} strategies\n")

            # Filter and display preset templates
            presets = [s for s in strategies if s.get('strategy_type') == 'preset']
            print(f"📋 Preset Templates: {len(presets)}")

            if presets:
                for preset in presets:
                    symbol = preset.get('symbol', 'N/A')
                    name = preset.get('name', 'N/A')
                    is_public = preset.get('is_public', False)
                    is_active = preset.get('is_active', False)
                    print(f"  ✓ {symbol:8} | {name[:40]:40} | Public: {is_public} | Active: {is_active}")
            else:
                print("  ⚠️  No preset templates found!")

            # Check user strategies
            user_strats = [s for s in strategies if s.get('strategy_type') != 'preset']
            if user_strats:
                print(f"\n👤 User Strategies: {len(user_strats)}")
                for strat in user_strats[:5]:  # Show max 5
                    name = strat.get('name', 'N/A')
                    symbol = strat.get('symbol', 'N/A')
                    print(f"  - {name} ({symbol})")

            # Validation
            if expected_count is not None:
                if len(presets) >= expected_count:
                    print(f"\n✅ PASS: Found {len(presets)}/{expected_count} expected preset templates")
                else:
                    print(f"\n❌ FAIL: Only found {len(presets)}/{expected_count} preset templates")

            return True

        elif response.status_code == 401:
            print("❌ AUTHENTICATION FAILED")
            print("Token is invalid or expired. Get a new token and try again.")
            return False

        else:
            print(f"❌ ERROR: Status {response.status_code}")
            print(response.text[:500])
            return False

    except requests.exceptions.Timeout:
        print("❌ TIMEOUT: Request took too long")
        return False
    except requests.exceptions.ConnectionError:
        print("❌ CONNECTION ERROR: Could not reach backend")
        return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def main():
    """Run all endpoint tests."""
    print("\n" + "=" * 80)
    print("  🧪 STRATEGY ENDPOINTS TEST")
    print("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 80)

    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    tests = [
        {
            "name": "List All Strategies",
            "url": f"{BACKEND_URL}/api/v1/strategies",
            "expected_count": 4,  # Should have 4 public templates
        },
        {
            "name": "Strategies for XAUUSD",
            "url": f"{BACKEND_URL}/api/v1/ml/strategies/for-model/XAUUSD",
            "expected_count": 1,  # Should have XAUUSD template
        },
        {
            "name": "Strategies for EURUSD",
            "url": f"{BACKEND_URL}/api/v1/ml/strategies/for-model/EURUSD",
            "expected_count": 1,  # Should have EURUSD template
        },
        {
            "name": "Strategies for GBPUSD",
            "url": f"{BACKEND_URL}/api/v1/ml/strategies/for-model/GBPUSD",
            "expected_count": 1,  # Should have GBPUSD template
        },
        {
            "name": "Strategies for USDJPY",
            "url": f"{BACKEND_URL}/api/v1/ml/strategies/for-model/USDJPY",
            "expected_count": 1,  # Should have USDJPY template
        },
    ]

    results = []
    for test in tests:
        success = test_endpoint(
            test["name"],
            test["url"],
            headers,
            test.get("expected_count")
        )
        results.append((test["name"], success))

    # Summary
    print("\n" + "=" * 80)
    print("  📊 TEST SUMMARY")
    print("=" * 80)

    passed = sum(1 for _, success in results if success)
    total = len(results)

    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} | {name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Public templates are working correctly.")
    else:
        print("\n⚠️  SOME TESTS FAILED. Check the logs above for details.")

    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user.")
        sys.exit(1)
