"""User settings API tests."""

import pytest
from fastapi.testclient import TestClient


def test_get_user_settings(client: TestClient, auth_headers: dict):
    """Test getting user settings defaults."""
    response = client.get("/api/v1/users/settings", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    
    # Check default settings are returned
    assert "defaultLotSize" in data
    assert "maxLotSize" in data
    assert "theme" in data
    assert "timezone" in data


def test_update_user_settings(client: TestClient, auth_headers: dict):
    """Test updating user settings."""
    response = client.put(
        "/api/v1/users/settings",
        json={
            "defaultLotSize": "0.5",
            "maxLotSize": "2.0",
            "riskPerTrade": "3",
            "theme": "light",
            "timezone": "Asia/Singapore"
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Settings updated successfully"
    
    # Verify settings were saved
    get_response = client.get("/api/v1/users/settings", headers=auth_headers)
    settings = get_response.json()
    assert settings["defaultLotSize"] == "0.5"
    assert settings["theme"] == "light"


def test_update_notifications_settings(client: TestClient, auth_headers: dict):
    """Test updating notification preferences."""
    response = client.put(
        "/api/v1/users/settings",
        json={
            "emailNotifications": False,
            "tradeAlerts": True,
            "dailySummary": True
        },
        headers=auth_headers
    )
    assert response.status_code == 200
    
    # Verify
    get_response = client.get("/api/v1/users/settings", headers=auth_headers)
    settings = get_response.json()
    assert settings["emailNotifications"] is False
    assert settings["tradeAlerts"] is True
    assert settings["dailySummary"] is True


def test_partial_settings_update(client: TestClient, auth_headers: dict):
    """Test that partial updates don't reset other settings."""
    # Set initial settings
    client.put(
        "/api/v1/users/settings",
        json={
            "defaultLotSize": "0.1",
            "theme": "dark"
        },
        headers=auth_headers
    )
    
    # Update only one setting
    client.put(
        "/api/v1/users/settings",
        json={"language": "id"},
        headers=auth_headers
    )
    
    # Verify original settings are preserved
    get_response = client.get("/api/v1/users/settings", headers=auth_headers)
    settings = get_response.json()
    assert settings["defaultLotSize"] == "0.1"
    assert settings["theme"] == "dark"
    assert settings["language"] == "id"


def test_settings_unauthorized(client: TestClient):
    """Test settings access without authentication fails."""
    response = client.get("/api/v1/users/settings")
    assert response.status_code == 401
    
    response = client.put(
        "/api/v1/users/settings",
        json={"theme": "light"}
    )
    assert response.status_code == 401


def test_update_profile(client: TestClient, auth_headers: dict, test_user: dict):
    """Test updating user profile name."""
    response = client.put(
        "/api/v1/users/me",
        params={"full_name": "Updated Name"},
        headers=auth_headers
    )
    assert response.status_code == 200
    
    # Verify profile was updated
    get_response = client.get("/api/v1/users/me", headers=auth_headers)
    assert get_response.json()["full_name"] == "Updated Name"
