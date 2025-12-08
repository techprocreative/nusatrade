"""Basic trading test - using conftest fixtures."""

from fastapi.testclient import TestClient


def test_open_and_close_order(client: TestClient, auth_headers: dict):
    """Test opening and closing an order."""
    create_res = client.post(
        "/api/v1/trading/orders",
        json={
            "symbol": "EURUSD",
            "order_type": "BUY",
            "lot_size": 0.1,
            "price": 1.1
        },
        headers=auth_headers,
    )
    assert create_res.status_code == 201, create_res.text
    trade_id = create_res.json()["id"]

    positions = client.get("/api/v1/trading/positions", headers=auth_headers)
    assert positions.status_code == 200
    assert len(positions.json()) == 1

    close_res = client.put(
        f"/api/v1/trading/orders/{trade_id}/close",
        json={"close_price": 1.101},
        headers=auth_headers,
    )
    assert close_res.status_code == 200
    # close_price might be float or string depending on serialization
    close_price = close_res.json()["close_price"]
    assert float(close_price) == 1.101

    positions_after = client.get("/api/v1/trading/positions", headers=auth_headers)
    assert positions_after.status_code == 200
    assert positions_after.json() == []

    history = client.get("/api/v1/trading/history", headers=auth_headers)
    assert history.status_code == 200
    assert len(history.json()) == 1
