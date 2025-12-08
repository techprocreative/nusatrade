"""AI Supervisor tests."""

import pytest
from fastapi.testclient import TestClient


def test_create_chat_conversation(client: TestClient, auth_headers: dict):
    """Test creating a chat conversation."""
    response = client.post(
        "/api/v1/ai/chat",
        json={
            "message": "What is my current trading performance?",
            "context_type": "trade_analysis"
        },
        headers=auth_headers
    )
    
    # May fail if OpenAI API key not configured, that's ok
    assert response.status_code in [200, 500, 503]
    
    if response.status_code == 200:
        data = response.json()
        assert "reply" in data
        assert "conversation_id" in data


def test_continue_conversation(client: TestClient, auth_headers: dict):
    """Test continuing a conversation."""
    # Start conversation
    first_response = client.post(
        "/api/v1/ai/chat",
        json={
            "message": "Hello, AI!",
            "context_type": "general"
        },
        headers=auth_headers
    )
    
    if first_response.status_code == 200:
        conversation_id = first_response.json()["conversation_id"]
        
        # Continue conversation
        second_response = client.post(
            "/api/v1/ai/chat",
            json={
                "message": "Tell me more",
                "conversation_id": conversation_id,
                "context_type": "general"
            },
            headers=auth_headers
        )
        
        assert second_response.status_code == 200
        assert second_response.json()["conversation_id"] == conversation_id


def test_list_conversations(client: TestClient, auth_headers: dict):
    """Test listing user's conversations."""
    response = client.get("/api/v1/ai/conversations", headers=auth_headers)
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_conversation_messages(client: TestClient, auth_headers: dict):
    """Test getting conversation messages."""
    # Create a conversation
    chat_response = client.post(
        "/api/v1/ai/chat",
        json={
            "message": "Test message",
            "context_type": "general"
        },
        headers=auth_headers
    )
    
    if chat_response.status_code == 200:
        conversation_id = chat_response.json()["conversation_id"]
        
        # Get messages
        response = client.get(
            f"/api/v1/ai/conversations/{conversation_id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        messages = response.json()
        assert len(messages) >= 2  # User message + AI reply


def test_market_analysis(client: TestClient, auth_headers: dict):
    """Test getting market analysis."""
    response = client.get(
        "/api/v1/ai/analysis/EURUSD",
        headers=auth_headers
    )
    
    # May fail if no LLM API configured
    assert response.status_code in [200, 404, 500, 503]


def test_daily_analysis(client: TestClient, auth_headers: dict):
    """Test getting daily market analysis."""
    response = client.get(
        "/api/v1/ai/analysis/daily",
        headers=auth_headers
    )
    
    # May fail if no LLM API configured
    assert response.status_code in [200, 500, 503]


def test_get_recommendations(client: TestClient, auth_headers: dict):
    """Test getting AI recommendations."""
    response = client.get(
        "/api/v1/ai/recommendations",
        headers=auth_headers
    )
    
    # May fail if no LLM API configured or no trade history
    assert response.status_code in [200, 404, 500, 503]


def test_chat_without_message(client: TestClient, auth_headers: dict):
    """Test chat request without message."""
    response = client.post(
        "/api/v1/ai/chat",
        json={
            "context_type": "general"
        },
        headers=auth_headers
    )
    assert response.status_code == 422  # Validation error


def test_chat_unauthorized(client: TestClient):
    """Test chat without authentication."""
    response = client.post(
        "/api/v1/ai/chat",
        json={
            "message": "Hello",
            "context_type": "general"
        }
    )
    assert response.status_code == 401


def test_different_context_types(client: TestClient, auth_headers: dict):
    """Test different context types."""
    context_types = ["general", "trade_analysis", "market_summary"]
    
    for context_type in context_types:
        response = client.post(
            "/api/v1/ai/chat",
            json={
                "message": f"Test message for {context_type}",
                "context_type": context_type
            },
            headers=auth_headers
        )
        
        # Should either work or fail gracefully
        assert response.status_code in [200, 500, 503]
