"""ML Bot tests."""

import pytest
from fastapi.testclient import TestClient


def test_list_ml_models_empty(client: TestClient, auth_headers: dict):
    """Test listing ML models when none exist."""
    response = client.get("/api/v1/ml/models", headers=auth_headers)
    assert response.status_code == 200
    assert response.json() == []


def test_create_ml_model(client: TestClient, auth_headers: dict):
    """Test creating a new ML model."""
    response = client.post(
        "/api/v1/ml/models",
        json={
            "name": "Test Model",
            "model_type": "random_forest",
            "config": {
                "n_estimators": 100,
                "max_depth": 10,
                "lookahead": 5,
                "threshold": 0.0005
            }
        },
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Model"
    assert data["model_type"] == "random_forest"
    assert "id" in data


def test_get_ml_model(client: TestClient, auth_headers: dict):
    """Test getting ML model details."""
    # Create a model
    create_response = client.post(
        "/api/v1/ml/models",
        json={
            "name": "Test Model",
            "model_type": "gradient_boosting",
            "config": {}
        },
        headers=auth_headers
    )
    model_id = create_response.json()["id"]
    
    # Get the model
    response = client.get(f"/api/v1/ml/models/{model_id}", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["id"] == model_id


def test_train_ml_model(client: TestClient, auth_headers: dict):
    """Test training an ML model."""
    # Create a model
    create_response = client.post(
        "/api/v1/ml/models",
        json={
            "name": "Trainable Model",
            "model_type": "random_forest",
            "config": {
                "n_estimators": 50,
                "max_depth": 5
            }
        },
        headers=auth_headers
    )
    model_id = create_response.json()["id"]
    
    # Train it (will use sample data since we don't have real historical data)
    response = client.post(
        f"/api/v1/ml/models/{model_id}/train",
        json={
            "symbol": "EURUSD",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        },
        headers=auth_headers
    )
    
    # Training is async, so we check if it was accepted
    assert response.status_code in [200, 202]


def test_activate_ml_model(client: TestClient, auth_headers: dict):
    """Test activating an ML model."""
    # Create a model
    create_response = client.post(
        "/api/v1/ml/models",
        json={
            "name": "Model to Activate",
            "model_type": "random_forest",
            "config": {}
        },
        headers=auth_headers
    )
    model_id = create_response.json()["id"]
    
    # Activate it
    response = client.post(
        f"/api/v1/ml/models/{model_id}/activate",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is True


def test_deactivate_ml_model(client: TestClient, auth_headers: dict):
    """Test deactivating an ML model."""
    # Create and activate a model
    create_response = client.post(
        "/api/v1/ml/models",
        json={
            "name": "Model to Deactivate",
            "model_type": "random_forest",
            "config": {}
        },
        headers=auth_headers
    )
    model_id = create_response.json()["id"]
    
    client.post(f"/api/v1/ml/models/{model_id}/activate", headers=auth_headers)
    
    # Deactivate it
    response = client.post(
        f"/api/v1/ml/models/{model_id}/deactivate",
        headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_delete_ml_model(client: TestClient, auth_headers: dict):
    """Test deleting an ML model."""
    # Create a model
    create_response = client.post(
        "/api/v1/ml/models",
        json={
            "name": "Model to Delete",
            "model_type": "random_forest",
            "config": {}
        },
        headers=auth_headers
    )
    model_id = create_response.json()["id"]
    
    # Delete it
    response = client.delete(
        f"/api/v1/ml/models/{model_id}",
        headers=auth_headers
    )
    assert response.status_code == 200
    
    # Verify it's gone
    get_response = client.get(
        f"/api/v1/ml/models/{model_id}",
        headers=auth_headers
    )
    assert get_response.status_code == 404


def test_get_model_predictions(client: TestClient, auth_headers: dict):
    """Test getting model predictions."""
    # Create and train a model (will use dummy data)
    create_response = client.post(
        "/api/v1/ml/models",
        json={
            "name": "Prediction Model",
            "model_type": "random_forest",
            "config": {}
        },
        headers=auth_headers
    )
    model_id = create_response.json()["id"]
    
    # Try to train it first
    client.post(
        f"/api/v1/ml/models/{model_id}/train",
        json={
            "symbol": "EURUSD",
            "start_date": "2024-01-01",
            "end_date": "2024-12-31"
        },
        headers=auth_headers
    )
    
    # Get predictions
    response = client.get(
        f"/api/v1/ml/models/{model_id}/predictions",
        headers=auth_headers
    )
    
    # Should work or say no data available
    assert response.status_code in [200, 404]


def test_only_owner_can_access_model(client: TestClient, auth_headers: dict):
    """Test that only model owner can access it."""
    # Create a model
    create_response = client.post(
        "/api/v1/ml/models",
        json={
            "name": "Private Model",
            "model_type": "random_forest",
            "config": {}
        },
        headers=auth_headers
    )
    model_id = create_response.json()["id"]
    
    # Create another user
    client.post(
        "/api/v1/auth/register",
        json={
            "email": "otheruser@example.com",
            "password": "OtherPass123!",
            "full_name": "Other User"
        }
    )
    
    # Login as other user
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "otheruser@example.com",
            "password": "OtherPass123!"
        }
    )
    other_headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
    
    # Try to access first user's model
    response = client.get(
        f"/api/v1/ml/models/{model_id}",
        headers=other_headers
    )
    assert response.status_code == 404  # Should not find it
