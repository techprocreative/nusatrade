import requests

BASE_URL = "http://localhost:8000/api/v1"
LOGIN_URL = f"{BASE_URL}/auth/login"
ML_MODELS_URL = f"{BASE_URL}/ml/models"
TIMEOUT = 30

TEST_USER = {
    "username": "testuser",
    "password": "testpassword"
}

def authenticate():
    try:
        resp = requests.post(LOGIN_URL, json=TEST_USER, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        token = data.get("access_token") or data.get("token") or data.get("jwt")
        if not token:
            # In case token key is different or nested, fallback:
            # Might adjust based on actual response structure
            token = data.get("access_token", None)
        assert token is not None, "Authentication token not found in response"
        return token
    except requests.RequestException as e:
        raise RuntimeError(f"Authentication failed: {e}")

def test_get_api_v1_ml_models():
    token = authenticate()
    headers = {
        "Authorization": f"Bearer {token}"
    }
    try:
        response = requests.get(ML_MODELS_URL, headers=headers, timeout=TIMEOUT)
        response.raise_for_status()
    except requests.RequestException as e:
        raise AssertionError(f"GET {ML_MODELS_URL} failed: {e}")

    try:
        models = response.json()
    except ValueError:
        raise AssertionError("Response is not a valid JSON")

    assert isinstance(models, list), "Response should be a list of models"

    # Verify each model has correct configuration fields based on PRD
    # PRD fields for ML model config: name, model_type, symbol, timeframe, config (object)
    # Some fields might be missing if no models exist, handle gracefully
    for model in models:
        assert isinstance(model, dict), "Each model entry should be a dictionary"
        for key in ["name", "model_type", "symbol", "timeframe", "config"]:
            assert key in model, f"Model missing required field '{key}'"
        assert isinstance(model["name"], str), "'name' should be a string"
        assert isinstance(model["model_type"], str), "'model_type' should be a string"
        assert isinstance(model["symbol"], str), "'symbol' should be a string"
        assert isinstance(model["timeframe"], str), "'timeframe' should be a string"
        assert isinstance(model["config"], dict), "'config' should be an object/dictionary"

test_get_api_v1_ml_models()