import requests

BASE_URL = "http://localhost:8000/api/v1"
LOGIN_URL = f"{BASE_URL}/auth/login"
GENERATE_STRATEGY_URL = f"{BASE_URL}/ai/generate-strategy"
TIMEOUT = 30

TEST_USER_CREDS = {
    "username": "testuser",
    "password": "testpassword"
}

def authenticate():
    try:
        resp = requests.post(LOGIN_URL, json=TEST_USER_CREDS, timeout=TIMEOUT)
        resp.raise_for_status()
        token = resp.json().get("access_token") or resp.json().get("token") or resp.json().get("accessToken")
        assert token, "JWT access token not found in login response"
        return token
    except requests.RequestException as e:
        raise Exception(f"Authentication failed: {e}")

def test_post_api_v1_ai_generate_strategy():
    token = authenticate()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    payload = {
        "prompt": "Generate a forex trading strategy focusing on EURUSD with moving average crossovers and stop loss risk management.",
        "symbol": "EURUSD",
        "timeframe": "1H",
        "risk_profile": "moderate",
        "preferred_indicators": ["SMA", "EMA", "RSI"]
    }
    try:
        response = requests.post(GENERATE_STRATEGY_URL, json=payload, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
        data = response.json()

        # Validate response schema keys presence
        assert "strategy" in data, "Missing 'strategy' in response"
        assert isinstance(data["strategy"], dict), "'strategy' should be an object"
        assert "explanation" in data, "Missing 'explanation' in response"
        assert isinstance(data["explanation"], str), "'explanation' should be a string"
        assert "warnings" in data, "Missing 'warnings' in response"
        assert isinstance(data["warnings"], list), "'warnings' should be a list"
        assert "suggested_improvements" in data, "Missing 'suggested_improvements' in response"
        assert isinstance(data["suggested_improvements"], list), "'suggested_improvements' should be a list"

        # Additional content checks (basic)
        strategy = data["strategy"]
        expected_keys = ["code", "parameters", "entry_rules", "exit_rules", "indicators", "risk_management"]
        assert any(k in strategy for k in expected_keys), "Strategy object missing expected keys"

    except requests.HTTPError as e:
        raise AssertionError(f"HTTP error occurred: {e} - Response content: {response.text}")
    except requests.RequestException as e:
        raise AssertionError(f"Request exception occurred: {e}")


test_post_api_v1_ai_generate_strategy()
