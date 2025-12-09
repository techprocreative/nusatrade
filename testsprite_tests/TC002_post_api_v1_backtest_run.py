import requests

BASE_URL = "http://localhost:8000/api/v1"
LOGIN_ENDPOINT = f"{BASE_URL}/auth/login"
AI_GENERATE_STRATEGY_ENDPOINT = f"{BASE_URL}/ai/generate-strategy"
BACKTEST_RUN_ENDPOINT = f"{BASE_URL}/backtest/run"
BACKTEST_SESSIONS_ENDPOINT = f"{BASE_URL}/backtest/sessions"

TEST_USER_CREDENTIALS = {
    "username": "testuser",
    "password": "testpassword"
}

def login_and_get_token():
    try:
        resp = requests.post(LOGIN_ENDPOINT, json=TEST_USER_CREDENTIALS, timeout=30)
        resp.raise_for_status()
        token = resp.json().get("access_token") or resp.json().get("token") or resp.json().get("accessToken")
        assert token, "No token found in login response"
        return token
    except requests.RequestException as e:
        raise RuntimeError(f"Login request failed: {e}")
    except AssertionError as ae:
        raise RuntimeError(str(ae))

def create_strategy(auth_header):
    # Use a fixed prompt and parameters for strategy generation
    payload = {
        "prompt": "Generate a simple moving average crossover strategy",
        "symbol": "EURUSD",
        "timeframe": "1h",
        "risk_profile": "medium",
        "preferred_indicators": ["SMA", "EMA"]
    }
    try:
        resp = requests.post(AI_GENERATE_STRATEGY_ENDPOINT, json=payload, headers=auth_header, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        # Validate required fields in the response
        assert isinstance(data, dict), "Response is not a JSON object"
        assert "strategy" in data and isinstance(data["strategy"], dict), "Missing or invalid strategy in response"
        assert "explanation" in data and isinstance(data["explanation"], str), "Missing or invalid explanation"
        assert "warnings" in data and isinstance(data["warnings"], list), "Missing or invalid warnings"
        assert "suggested_improvements" in data and isinstance(data["suggested_improvements"], list), "Missing or invalid suggested improvements"
        # Strategy object must contain at least an id or code to identify it for backtesting
        # The PRD does not explicitly give a strategy_id field; assuming "id" field inside strategy object
        strategy_id = data["strategy"].get("id")
        if not strategy_id:
            # Sometimes maybe strategy code or name? We require an ID for backtesting
            # If no ID, check if there's "code" or generate a synthetic ID (less likely)
            raise RuntimeError("No strategy_id found in generated strategy")
        return strategy_id
    except requests.RequestException as e:
        raise RuntimeError(f"Strategy generation request failed: {e}")
    except AssertionError as ae:
        raise RuntimeError(str(ae))

def delete_backtest_session(session_id, auth_header):
    # The PRD does not specify DELETE endpoint for backtest sessions
    # So no delete implementation available, skipping cleanup of backtest session
    pass

def test_post_api_v1_backtest_run():
    token = login_and_get_token()
    auth_header = {"Authorization": f"Bearer {token}"}
    strategy_id = None
    session_id = None
    try:
        # Create strategy for backtesting
        strategy_id = create_strategy(auth_header)

        backtest_payload = {
            "strategy_id": strategy_id,
            "symbol": "EURUSD",
            "timeframe": "1h",
            "start_date": "2022-01-01",
            "end_date": "2022-03-01",
            "initial_balance": 10000.0,
            "commission": 0.0002,
            "slippage": 0.0001
        }
        resp = requests.post(BACKTEST_RUN_ENDPOINT, json=backtest_payload, headers=auth_header, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        assert isinstance(data, dict), "Backtest run response is not a JSON object"

        # Validate presence and types of required performance metrics and session info
        required_fields = {
            "session_id": str,
            "status": str,
            "net_profit": (int, float),
            "total_trades": int,
            "win_rate": (int, float),
            "profit_factor": (int, float),
            "max_drawdown_pct": (int, float),
            "sharpe_ratio": (int, float)
        }
        for field, ftype in required_fields.items():
            assert field in data, f"Missing field '{field}' in backtest response"
            assert isinstance(data[field], ftype), f"Field '{field}' is not of type {ftype}"

        session_id = data["session_id"]

        # Check that status is a string and non-empty
        assert isinstance(data["status"], str) and len(data["status"].strip()) > 0, f"Invalid backtest status: {data['status']}"

        # Validate metrics are within reasonable ranges
        assert data["net_profit"] != 0, "Net profit should not be zero"
        assert 0 <= data["win_rate"] <= 1, "Win rate should be between 0 and 1"
        assert data["sharpe_ratio"] > -10 and data["sharpe_ratio"] < 10, "Sharpe ratio out of expected range"

    finally:
        # Cleanup not explicitly supported for backtest sessions, so omitted
        pass

test_post_api_v1_backtest_run()