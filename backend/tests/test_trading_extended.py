"""Extended trading tests."""

import pytest
from fastapi.testclient import TestClient


def test_place_buy_order(client: TestClient, auth_headers: dict):
    """Test placing a BUY order."""
    response = client.post(
        "/api/v1/trading/orders",
        json={
            "symbol": "EURUSD",
            "order_type": "BUY",
            "lot_size": 0.1,
            "price": 1.1000,
            "stop_loss": 1.0950,
            "take_profit": 1.1100
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["symbol"] == "EURUSD"
    assert data["trade_type"] == "BUY"
    assert float(data["lot_size"]) == 0.1


def test_place_sell_order(client: TestClient, auth_headers: dict):
    """Test placing a SELL order."""
    response = client.post(
        "/api/v1/trading/orders",
        json={
            "symbol": "GBPUSD",
            "order_type": "SELL",
            "lot_size": 0.2,
            "price": 1.2500
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["symbol"] == "GBPUSD"
    assert data["trade_type"] == "SELL"


def test_place_order_invalid_lot_size(client: TestClient, auth_headers: dict):
    """Test placing order with invalid lot size."""
    response = client.post(
        "/api/v1/trading/orders",
        json={
            "symbol": "EURUSD",
            "order_type": "BUY",
            "lot_size": -0.1,  # Negative lot size
            "price": 1.1000
        },
        headers=auth_headers
    )
    # Could be 400 (validation) or 422 (pydantic)
    assert response.status_code in [400, 422]


def test_place_order_exceeds_max_lots(client: TestClient, auth_headers: dict):
    """Test placing order that exceeds max lot size."""
    response = client.post(
        "/api/v1/trading/orders",
        json={
            "symbol": "EURUSD",
            "order_type": "BUY",
            "lot_size": 100.0,  # Way over limit
            "price": 1.1000
        },
        headers=auth_headers
    )
    assert response.status_code == 400
    detail = response.json()["detail"].lower()
    # Check for "max" or "exceed" in error message
    assert "max" in detail or "exceed" in detail


def test_list_positions(client: TestClient, auth_headers: dict):
    """Test listing open positions."""
    # Open a position first
    client.post(
        "/api/v1/trading/orders",
        json={
            "symbol": "EURUSD",
            "order_type": "BUY",
            "lot_size": 0.1,
            "price": 1.1000
        },
        headers=auth_headers
    )
    
    response = client.get("/api/v1/trading/positions", headers=auth_headers)
    assert response.status_code == 200
    positions = response.json()
    assert len(positions) == 1
    assert positions[0]["symbol"] == "EURUSD"


def test_close_position(client: TestClient, auth_headers: dict):
    """Test closing a position."""
    # Open a position
    order_response = client.post(
        "/api/v1/trading/orders",
        json={
            "symbol": "EURUSD",
            "order_type": "BUY",
            "lot_size": 0.1,
            "price": 1.1000
        },
        headers=auth_headers
    )
    order_id = order_response.json()["id"]
    
    # Close it
    response = client.put(
        f"/api/v1/trading/orders/{order_id}/close",
        json={"close_price": 1.1050},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    # close_price could be float or string
    close_price = data["close_price"]
    assert float(close_price) == 1.105
    assert data["profit"] is not None


def test_close_nonexistent_position(client: TestClient, auth_headers: dict):
    """Test closing non-existent position."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = client.put(
        f"/api/v1/trading/orders/{fake_id}/close",
        json={"close_price": 1.1050},
        headers=auth_headers
    )
    assert response.status_code == 404


def test_trade_history(client: TestClient, auth_headers: dict):
    """Test getting trade history."""
    # Open and close a trade
    order_response = client.post(
        "/api/v1/trading/orders",
        json={
            "symbol": "EURUSD",
            "order_type": "BUY",
            "lot_size": 0.1,
            "price": 1.1000
        },
        headers=auth_headers
    )
    order_id = order_response.json()["id"]
    
    client.put(
        f"/api/v1/trading/orders/{order_id}/close",
        json={"close_price": 1.1050},
        headers=auth_headers
    )
    
    # Get history
    response = client.get("/api/v1/trading/history", headers=auth_headers)
    assert response.status_code == 200
    history = response.json()
    assert len(history) >= 1
    assert history[0]["symbol"] == "EURUSD"


def test_calculate_position_size(client: TestClient, auth_headers: dict):
    """Test position size calculator."""
    response = client.post(
        "/api/v1/trading/position-size/calculate",
        json={
            "account_balance": 10000.0,
            "risk_percent": 2.0,
            "entry_price": 1.1000,
            "stop_loss": 1.0950,
            "symbol": "EURUSD"
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert "lot_size" in data
    assert "risk_amount" in data
    assert "stop_loss_pips" in data
    assert float(data["lot_size"]) > 0


def test_multiple_positions_limit(client: TestClient, auth_headers: dict):
    """Test that max positions limit is enforced."""
    # Try to open many positions
    for i in range(25):  # Max is 20
        response = client.post(
            "/api/v1/trading/orders",
            json={
                "symbol": f"PAIR{i}",
                "order_type": "BUY",
                "lot_size": 0.01,
                "price": 1.0
            },
            headers=auth_headers
        )
        
        if i < 20:
            assert response.status_code == 201
        else:
            # Should fail after 20 positions
            assert response.status_code == 400
            assert "max" in response.json()["detail"].lower()
            break


def test_unauthorized_trading(client: TestClient):
    """Test trading without authentication fails."""
    # Ensure fresh client without auth
    import os
    os.environ["TESTING"] = "1"
    
    response = client.post(
        "/api/v1/trading/orders",
        json={
            "symbol": "EURUSD",
            "order_type": "BUY",
            "lot_size": 0.1,
            "price": 1.1000
        }
    )
    assert response.status_code == 401
