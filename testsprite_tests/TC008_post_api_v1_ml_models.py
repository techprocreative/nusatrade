import requests

BASE_URL = "http://localhost:8000/api/v1"
LOGIN_URL = f"{BASE_URL}/auth/login"
ML_MODELS_URL = f"{BASE_URL}/ml/models"
USERNAME = "testuser"
PASSWORD = "testpassword"


def get_jwt_token():
    try:
        response = requests.post(
            LOGIN_URL,
            json={"username": USERNAME, "password": PASSWORD},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token") or data.get("token") or data.get("accessToken")
        assert token, "JWT token not found in login response"
        return token
    except requests.RequestException as e:
        raise AssertionError(f"Login request failed: {e}")
    except (ValueError, AssertionError) as e:
        raise AssertionError(f"Login response invalid: {e}")


def test_post_api_v1_ml_models():
    token = get_jwt_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Define minimal valid payload for creating an ML model configuration
    model_payload = {
        "name": "Test Model TC008",
        "model_type": "random_forest",
        "symbol": "EURUSD",
        "timeframe": "1h",
        "config": {
            "n_estimators": 100,
            "max_depth": 5,
            "random_state": 42
        }
    }

    model_id = None
    try:
        # Create ML model configuration
        response = requests.post(
            ML_MODELS_URL,
            json=model_payload,
            headers=headers,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        # Validate response contains expected fields and matches input
        assert "id" in data and isinstance(data["id"], (str, int)), "Missing or invalid model id"
        model_id = str(data["id"])
        assert data.get("name") == model_payload["name"], "Model name mismatch"
        assert data.get("model_type") == model_payload["model_type"], "Model type mismatch"
        assert data.get("symbol") == model_payload["symbol"], "Symbol mismatch"
        assert data.get("timeframe") == model_payload["timeframe"], "Timeframe mismatch"
        assert isinstance(data.get("config"), dict), "Config missing or invalid"
        # Optionally check config keys
        for key in model_payload["config"]:
            assert data["config"].get(key) == model_payload["config"][key], f"Config value mismatch for {key}"

        # Verify the model is stored correctly by fetching the list and confirming presence
        list_resp = requests.get(ML_MODELS_URL, headers=headers, timeout=30)
        list_resp.raise_for_status()
        models_list = list_resp.json()
        assert any(str(m.get("id")) == model_id for m in models_list), "Created model not found in models list"

    except requests.RequestException as e:
        raise AssertionError(f"Request failed: {e}")
    except (ValueError, AssertionError) as e:
        raise AssertionError(f"Validation failed: {e}")
    finally:
        # Cleanup: delete the created model if possible
        if model_id:
            try:
                del_url = f"{ML_MODELS_URL}/{model_id}"
                del_resp = requests.delete(del_url, headers=headers, timeout=30)
                # It's acceptable if delete is not supported; do not fail test for delete failure
                if del_resp.status_code not in (204, 200, 202, 404):
                    print(f"Warning: unexpected status code on model delete: {del_resp.status_code}")
            except requests.RequestException:
                print("Warning: exception during cleanup while deleting model")

test_post_api_v1_ml_models()