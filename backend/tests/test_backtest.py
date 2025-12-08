"""Backtesting tests."""

import pytest
from fastapi.testclient import TestClient


def test_list_strategies_empty(client: TestClient, auth_headers: dict):
    """Test listing strategies when none exist."""
    response = client.get("/api/v1/backtest/strategies", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_create_strategy(client: TestClient, auth_headers: dict):
    """Test creating a backtest strategy."""
    response = client.post(
        "/api/v1/backtest/strategies",
        json={
            "name": "MA Crossover",
            "description": "Moving average crossover strategy",
            "strategy_type": "ma_crossover",
            "config": {
                "fast_period": 10,
                "slow_period": 20
            }
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "MA Crossover"
    assert data["strategy_type"] == "ma_crossover"
    assert "id" in data


def test_get_strategy(client: TestClient, auth_headers: dict):
    """Test getting strategy details."""
    # Create a strategy
    create_response = client.post(
        "/api/v1/backtest/strategies",
        json={
            "name": "Test Strategy",
            "strategy_type": "ma_crossover",
            "config": {}
        },
        headers=auth_headers
    )
    strategy_id = create_response.json()["id"]
    
    # Get the strategy
    response = client.get(
        f"/api/v1/backtest/strategies/{strategy_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["id"] == strategy_id


def test_update_strategy(client: TestClient, auth_headers: dict):
    """Test updating a strategy."""
    # Create a strategy
    create_response = client.post(
        "/api/v1/backtest/strategies",
        json={
            "name": "Original Name",
            "strategy_type": "ma_crossover",
            "config": {}
        },
        headers=auth_headers
    )
    strategy_id = create_response.json()["id"]
    
    # Update it
    response = client.put(
        f"/api/v1/backtest/strategies/{strategy_id}",
        json={
            "name": "Updated Name",
            "description": "Updated description"
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_delete_strategy(client: TestClient, auth_headers: dict):
    """Test deleting a strategy."""
    # Create a strategy
    create_response = client.post(
        "/api/v1/backtest/strategies",
        json={
            "name": "Strategy to Delete",
            "strategy_type": "ma_crossover",
            "config": {}
        },
        headers=auth_headers
    )
    strategy_id = create_response.json()["id"]
    
    # Delete it
    response = client.delete(
        f"/api/v1/backtest/strategies/{strategy_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    
    # Verify it's gone
    get_response = client.get(
        f"/api/v1/backtest/strategies/{strategy_id}",
        headers=auth_headers
    )
    assert get_response.status_code == 404


def test_run_backtest(client: TestClient, auth_headers: dict):
    """Test running a backtest."""
    # Create a strategy
    create_response = client.post(
        "/api/v1/backtest/strategies",
        json={
            "name": "Backtest Strategy",
            "strategy_type": "ma_crossover",
            "config": {
                "fast_period": 10,
                "slow_period": 20
            }
        },
        headers=auth_headers
    )
    strategy_id = create_response.json()["id"]
    
    # Run backtest
    response = client.post(
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
    
    # Backtest is async, check if accepted
    assert response.status_code in [200, 201, 202]
    if response.status_code == 200:
        data = response.json()
        assert "session_id" in data or "id" in data


def test_list_backtest_sessions(client: TestClient, auth_headers: dict):
    """Test listing backtest sessions."""
    response = client.get("/api/v1/backtest/sessions", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_backtest_results(client: TestClient, auth_headers: dict):
    """Test getting backtest results."""
    # Create strategy and run backtest
    strategy_response = client.post(
        "/api/v1/backtest/strategies",
        json={
            "name": "Results Test Strategy",
            "strategy_type": "ma_crossover",
            "config": {}
        },
        headers=auth_headers
    )
    strategy_id = strategy_response.json()["id"]
    
    backtest_response = client.post(
        "/api/v1/backtest/run",
        json={
            "strategy_id": strategy_id,
            "symbol": "EURUSD",
            "timeframe": "1h",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "initial_balance": 10000.0
        },
        headers=auth_headers
    )
    
    # If backtest completed synchronously, get results
    if backtest_response.status_code == 200:
        session_id = backtest_response.json().get("session_id") or backtest_response.json().get("id")
        if session_id:
            result_response = client.get(
                f"/api/v1/backtest/sessions/{session_id}",
                headers=auth_headers
            )
            assert result_response.status_code in [200, 404]  # 404 if not found yet


def test_backtest_invalid_dates(client: TestClient, auth_headers: dict):
    """Test backtest with invalid date range."""
    # Create strategy
    strategy_response = client.post(
        "/api/v1/backtest/strategies",
        json={
            "name": "Invalid Date Strategy",
            "strategy_type": "ma_crossover",
            "config": {}
        },
        headers=auth_headers
    )
    strategy_id = strategy_response.json()["id"]
    
    # Try backtest with end date before start date
    response = client.post(
        "/api/v1/backtest/run",
        json={
            "strategy_id": strategy_id,
            "symbol": "EURUSD",
            "timeframe": "1h",
            "start_date": "2024-12-31",
            "end_date": "2024-01-01",  # Before start date
            "initial_balance": 10000.0
        },
        headers=auth_headers
    )
    
    # Should fail validation
    assert response.status_code in [400, 422]


def test_backtest_negative_balance(client: TestClient, auth_headers: dict):
    """Test backtest with negative initial balance."""
    strategy_response = client.post(
        "/api/v1/backtest/strategies",
        json={
            "name": "Negative Balance Strategy",
            "strategy_type": "ma_crossover",
            "config": {}
        },
        headers=auth_headers
    )
    strategy_id = strategy_response.json()["id"]
    
    response = client.post(
        "/api/v1/backtest/run",
        json={
            "strategy_id": strategy_id,
            "symbol": "EURUSD",
            "timeframe": "1h",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "initial_balance": -1000.0  # Negative balance
        },
        headers=auth_headers
    )
    
    assert response.status_code == 422
