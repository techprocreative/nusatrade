import requests

BASE_URL = "http://localhost:8000/api/v1"
LOGIN_URL = f"{BASE_URL}/auth/login"
AI_CHAT_URL = f"{BASE_URL}/ai/chat"
TIMEOUT = 30

TEST_USER = {
    "email": "testuser@example.com",
    "password": "testpassword"
}

def test_post_api_v1_ai_chat():
    # Authenticate and get JWT token
    try:
        login_resp = requests.post(
            LOGIN_URL,
            json={"email": TEST_USER["email"], "password": TEST_USER["password"]},
            timeout=TIMEOUT
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        token = login_resp.json().get("access_token") or login_resp.json().get("token") or login_resp.json().get("accessToken")
        assert token, "No access token returned on login"
        headers = {"Authorization": f"Bearer {token}"}
    except requests.RequestException as e:
        assert False, f"Login request failed: {e}"

    # Initialize conversation_id as None to start new conversation
    conversation_id = None
    messages = [
        "Hello AI supervisor, can you provide a daily market summary?",
        "What is your recommendation for EURUSD today?",
        "Please analyze the recent volatility in USDJPY."
    ]

    try:
        for msg in messages:
            payload = {
                "message": msg,
                "conversation_id": conversation_id if conversation_id else "",
                "context_type": "trading_supervision"
            }
            try:
                chat_resp = requests.post(
                    AI_CHAT_URL,
                    json=payload,
                    headers=headers,
                    timeout=TIMEOUT
                )
                assert chat_resp.status_code == 200, f"Chat request failed: {chat_resp.text}"
                data = chat_resp.json()
                assert "reply" in data and isinstance(data["reply"], str) and data["reply"], "Reply missing or empty in response"
                assert "conversation_id" in data and isinstance(data["conversation_id"], str) and data["conversation_id"], "Conversation ID missing or empty in response"
                assert "tokens_used" in data and isinstance(data["tokens_used"], int) and data["tokens_used"] > 0, "Tokens used missing, not int, or <= 0"
                conversation_id = data["conversation_id"]
            except requests.RequestException as e:
                assert False, f"Chat request exception: {e}"
    finally:
        # No resource to clean up for conversation-based chat test
        pass

test_post_api_v1_ai_chat()
