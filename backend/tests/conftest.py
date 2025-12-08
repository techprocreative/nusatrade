"""Pytest configuration and shared fixtures."""

import os
import sys
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker, Session

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.main import app as fastapi_app
from app.core.database import Base
from app.api import deps
import app.models  # noqa: F401


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db() -> Generator[Session, None, None]:
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db: Session) -> TestClient:
    """Create test client with database override."""
    def override_get_db():
        try:
            yield db
        finally:
            pass
    
    fastapi_app.dependency_overrides[deps.get_db] = override_get_db
    
    # Disable rate limiting for tests
    import os
    os.environ["TESTING"] = "1"
    
    return TestClient(fastapi_app)


@pytest.fixture(scope="function")
def test_user(client: TestClient) -> dict:
    """Create a test user and return credentials."""
    user_data = {
        "email": "testuser@example.com",
        "password": "TestPass123!",
        "full_name": "Test User"
    }
    
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 201
    
    return user_data


@pytest.fixture(scope="function")
def auth_headers(client: TestClient, test_user: dict) -> dict:
    """Get authentication headers for test user."""
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user["email"],
            "password": test_user["password"]
        }
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def test_user_with_token(client: TestClient, test_user: dict, auth_headers: dict) -> tuple:
    """Return test user data and auth headers."""
    return test_user, auth_headers
