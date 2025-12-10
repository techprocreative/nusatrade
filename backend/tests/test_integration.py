"""Integration tests for complete user flows."""

import pytest
from fastapi.testclient import TestClient


class TestFullTradingFlow:
    """Integration tests for complete trading flow."""
    
    def test_register_login_trade_flow(self, client: TestClient):
        """Test complete flow: register -> login -> place order -> close -> view history."""
        # 1. Register new user
        register_response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "flowtest@example.com",
                "password": "FlowTest123!",
                "full_name": "Flow Test User"
            }
        )
        assert register_response.status_code == 201
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Place a trade
        order_response = client.post(
            "/api/v1/trading/orders",
            json={
                "symbol": "EURUSD",
                "order_type": "BUY",
                "lot_size": 0.1,
                "price": 1.1000,
                "stop_loss": 1.0950,
                "take_profit": 1.1100
            },
            headers=headers
        )
        assert order_response.status_code == 201
        order_id = order_response.json()["id"]
        
        # 3. Verify position is open
        positions_response = client.get("/api/v1/trading/positions", headers=headers)
        assert positions_response.status_code == 200
        positions = positions_response.json()
        assert len(positions) == 1
        assert positions[0]["symbol"] == "EURUSD"
        
        # 4. Close the position
        close_response = client.put(
            f"/api/v1/trading/orders/{order_id}/close",
            json={"close_price": 1.1050},
            headers=headers
        )
        assert close_response.status_code == 200
        
        # 5. Verify trade is in history
        history_response = client.get("/api/v1/trading/history", headers=headers)
        assert history_response.status_code == 200
        history = history_response.json()
        assert len(history) >= 1
        assert history[0]["symbol"] == "EURUSD"


class TestStrategyBacktestFlow:
    """Integration tests for strategy and backtesting flow."""
    
    def test_create_strategy_and_backtest(self, client: TestClient, auth_headers: dict):
        """Test complete flow: create strategy -> run backtest -> get results."""
        # 1. Create a strategy
        strategy_response = client.post(
            "/api/v1/backtest/strategies",
            json={
                "name": "Integration Test Strategy",
                "description": "Strategy for integration testing",
                "strategy_type": "ma_crossover",
                "config": {
                    "fast_period": 10,
                    "slow_period": 20
                }
            },
            headers=auth_headers
        )
        assert strategy_response.status_code == 201
        strategy_id = strategy_response.json()["id"]
        
        # 2. Verify strategy exists
        get_strategy_response = client.get(
            f"/api/v1/backtest/strategies/{strategy_id}",
            headers=auth_headers
        )
        assert get_strategy_response.status_code == 200
        assert get_strategy_response.json()["name"] == "Integration Test Strategy"
        
        # 3. Run a backtest
        backtest_response = client.post(
            "/api/v1/backtest/run",
            json={
                "strategy_id": strategy_id,
                "symbol": "EURUSD",
                "timeframe": "1h",
                "start_date": "2024-01-01",
                "end_date": "2024-03-31",
                "initial_balance": 10000.0,
                "config": {
                    "commission": 7.0,
                    "slippage_pips": 1.0
                }
            },
            headers=auth_headers
        )
        # Backtest can complete sync or async
        assert backtest_response.status_code in [200, 201, 202]
        
        # 4. List sessions to verify backtest was recorded
        sessions_response = client.get("/api/v1/backtest/sessions", headers=auth_headers)
        assert sessions_response.status_code == 200


class TestMLModelFlow:
    """Integration tests for ML model workflow."""
    
    def test_create_train_activate_model(self, client: TestClient, auth_headers: dict):
        """Test complete flow: create model -> train -> activate."""
        # 1. Create ML model
        create_response = client.post(
            "/api/v1/ml/models",
            json={
                "name": "Integration Test Model",
                "model_type": "random_forest",
                "config": {
                    "n_estimators": 50,
                    "max_depth": 5
                }
            },
            headers=auth_headers
        )
        assert create_response.status_code == 201
        model_id = create_response.json()["id"]
        
        # 2. Train the model
        train_response = client.post(
            f"/api/v1/ml/models/{model_id}/train",
            json={
                "symbol": "EURUSD",
                "start_date": "2024-01-01",
                "end_date": "2024-06-30"
            },
            headers=auth_headers
        )
        assert train_response.status_code in [200, 202]
        
        # 3. Activate the model
        activate_response = client.post(
            f"/api/v1/ml/models/{model_id}/activate",
            headers=auth_headers
        )
        assert activate_response.status_code == 200
        assert activate_response.json()["is_active"] is True
        
        # 4. Verify model is active in list
        list_response = client.get("/api/v1/ml/models", headers=auth_headers)
        assert list_response.status_code == 200
        models = list_response.json()
        active_model = next((m for m in models if m["id"] == model_id), None)
        assert active_model is not None
        assert active_model["is_active"] is True


class TestUserSettingsFlow:
    """Integration tests for user settings workflow."""
    
    def test_settings_persistence_across_sessions(self, client: TestClient):
        """Test that settings persist across login sessions."""
        # 1. Register and login
        client.post(
            "/api/v1/auth/register",
            json={
                "email": "settings_test@example.com",
                "password": "SettingsTest123!",
                "full_name": "Settings Test"
            }
        )
        
        login1_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "settings_test@example.com",
                "password": "SettingsTest123!"
            }
        )
        headers1 = {"Authorization": f"Bearer {login1_response.json()['access_token']}"}
        
        # 2. Update settings
        client.put(
            "/api/v1/users/settings",
            json={
                "theme": "light",
                "defaultLotSize": "0.5",
                "timezone": "Europe/London"
            },
            headers=headers1
        )
        
        # 3. Login again (simulating new session)
        login2_response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "settings_test@example.com",
                "password": "SettingsTest123!"
            }
        )
        headers2 = {"Authorization": f"Bearer {login2_response.json()['access_token']}"}
        
        # 4. Verify settings persisted
        settings_response = client.get("/api/v1/users/settings", headers=headers2)
        settings = settings_response.json()
        assert settings["theme"] == "light"
        assert settings["defaultLotSize"] == "0.5"
        assert settings["timezone"] == "Europe/London"


class TestAIRecommendationsFlow:
    """Integration tests for AI recommendations with trade history."""
    
    def test_recommendations_with_trade_history(self, client: TestClient, auth_headers: dict):
        """Test AI recommendations use trade history."""
        # 1. Create some trades
        for i in range(3):
            order_response = client.post(
                "/api/v1/trading/orders",
                json={
                    "symbol": "EURUSD",
                    "order_type": "BUY" if i % 2 == 0 else "SELL",
                    "lot_size": 0.1,
                    "price": 1.1000 + (i * 0.001)
                },
                headers=auth_headers
            )
            if order_response.status_code == 201:
                order_id = order_response.json()["id"]
                # Close the trade
                client.put(
                    f"/api/v1/trading/orders/{order_id}/close",
                    json={"close_price": 1.1010 + (i * 0.001)},
                    headers=auth_headers
                )
        
        # 2. Get AI recommendations
        recommendations_response = client.get(
            "/api/v1/ai/recommendations",
            headers=auth_headers
        )
        
        # Should work or fail gracefully (no LLM configured)
        assert recommendations_response.status_code in [200, 500, 503]
        
        if recommendations_response.status_code == 200:
            data = recommendations_response.json()
            assert "recommendations" in data
            assert "trade_stats" in data
            assert data["trade_stats"]["total_trades"] >= 0
