"""Basic auth test - using conftest fixtures."""

from fastapi.testclient import TestClient


def test_register_and_login(client: TestClient):
    """Test user registration and login flow."""
    res = client.post("/api/v1/auth/register", json={
        "email": "user@example.com",
        "password": "Secret123!",
        "full_name": "Test User"
    })
    assert res.status_code == 201
    
    token_res = client.post("/api/v1/auth/login", json={
        "email": "user@example.com",
        "password": "Secret123!"
    })
    assert token_res.status_code == 200
    access_token = token_res.json().get("access_token")
    assert access_token
    
    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {access_token}"})
    assert me.status_code == 200
    assert me.json()["email"] == "user@example.com"
