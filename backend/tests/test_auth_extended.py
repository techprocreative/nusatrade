"""Extended authentication tests."""

import pytest
from fastapi.testclient import TestClient


def test_register_success(client: TestClient):
    """Test successful user registration."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "SecurePass123!",
            "full_name": "New User"
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate_email(client: TestClient, test_user: dict):
    """Test registration with duplicate email fails."""
    response = client.post(
        "/api/v1/auth/register",
        json=test_user
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


def test_register_invalid_email(client: TestClient):
    """Test registration with invalid email fails."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "not-an-email",
            "password": "SecurePass123!",
            "full_name": "Test"
        }
    )
    assert response.status_code == 422


def test_register_weak_password(client: TestClient):
    """Test registration with weak password fails."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "123",  # Too short
            "full_name": "Test"
        }
    )
    assert response.status_code == 422


def test_login_success(client: TestClient, test_user: dict):
    """Test successful login."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user["email"],
            "password": test_user["password"]
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client: TestClient, test_user: dict):
    """Test login with wrong password fails."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user["email"],
            "password": "WrongPassword123!"
        }
    )
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_login_nonexistent_user(client: TestClient):
    """Test login with non-existent user fails."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "nonexistent@example.com",
            "password": "SomePassword123!"
        }
    )
    assert response.status_code == 401


def test_get_current_user(client: TestClient, auth_headers: dict, test_user: dict):
    """Test getting current user info."""
    response = client.get("/api/v1/users/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user["email"]
    assert data["full_name"] == test_user["full_name"]
    assert "id" in data


def test_get_current_user_unauthorized(client: TestClient):
    """Test getting current user without auth fails."""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401


def test_get_current_user_invalid_token(client: TestClient):
    """Test getting current user with invalid token fails."""
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": "Bearer invalid_token"}
    )
    assert response.status_code == 401


def test_forgot_password_success(client: TestClient, test_user: dict):
    """Test forgot password request."""
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": test_user["email"]}
    )
    assert response.status_code == 200
    assert "email sent" in response.json()["message"].lower()


def test_forgot_password_nonexistent_email(client: TestClient):
    """Test forgot password with non-existent email still returns success (security)."""
    response = client.post(
        "/api/v1/auth/forgot-password",
        json={"email": "nonexistent@example.com"}
    )
    # Should return 200 even if email doesn't exist (security best practice)
    assert response.status_code == 200


def test_logout_success(client: TestClient, auth_headers: dict):
    """Test logout."""
    response = client.post("/api/v1/auth/logout", headers=auth_headers)
    assert response.status_code == 200
    assert "logged out" in response.json()["message"].lower()


def test_refresh_token(client: TestClient, test_user: dict):
    """Test token refresh."""
    # Login to get tokens
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user["email"],
            "password": test_user["password"]
        }
    )
    refresh_token = login_response.json()["refresh_token"]
    
    # Refresh token
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
