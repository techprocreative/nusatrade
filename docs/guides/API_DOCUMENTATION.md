# 📚 Forex AI Platform - API Documentation

Complete REST API documentation for Forex AI Platform.

**Base URL**: `https://api.forexai.com/api/v1`

**Interactive Docs**: [https://api.forexai.com/docs](https://api.forexai.com/docs) (Swagger UI)

---

## 🔐 Authentication

All endpoints (except auth) require JWT token in header:

```http
Authorization: Bearer <your_jwt_token>
```

### Obtain Token

**POST** `/auth/login`

```json
{
  "email": "user@example.com",
  "password": "your_password"
}
```

**Response 200**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

**Token expires in**: 30 minutes (refresh with `/auth/refresh`)

---

## 📋 API Endpoints

### Authentication

#### Register User
`POST /auth/register`

**Request**:
```json
{
  "email": "newuser@example.com",
  "password": "SecurePass123!",
  "full_name": "John Doe"
}
```

**Response 201**:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "newuser@example.com",
  "full_name": "John Doe",
  "created_at": "2025-12-08T10:00:00Z"
}
```

---

#### Login
`POST /auth/login`

For users **without** 2FA.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!"
}
```

**Response 200**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

**Error 403** (if 2FA enabled):
```json
{
  "detail": "2FA is enabled. Please use /auth/login-2fa endpoint with TOTP code."
}
```

---

#### Login with 2FA
`POST /auth/login-2fa`

For users **with** 2FA enabled.

**Request**:
```json
{
  "email": "user@example.com",
  "password": "SecurePass123!",
  "totp_token": "123456"
}
```

**Response 200**: Same as `/auth/login`

---

#### Logout
`POST /auth/logout`

**Response 200**:
```json
{
  "status": "logged_out"
}
```

---

#### Refresh Token
`POST /auth/refresh`

**Request**:
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response 200**:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer"
}
```

---

### Two-Factor Authentication (2FA)

#### Get 2FA Status
`GET /totp/status`

**Response 200**:
```json
{
  "enabled": false
}
```

---

#### Setup 2FA
`POST /totp/setup`

**Response 200**:
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANS...",
  "uri": "otpauth://totp/ForexAI:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Forex+AI+Platform"
}
```

**Next step**: Scan QR code with authenticator app (Google Authenticator, Authy, etc.)

---

#### Verify and Enable 2FA
`POST /totp/verify`

**Request**:
```json
{
  "token": "123456"
}
```

**Response 200**:
```json
{
  "enabled": true
}
```

---

#### Disable 2FA
`POST /totp/disable`

**Request**:
```json
{
  "password": "SecurePass123!",
  "totp_token": "123456"
}
```

**Response 200**:
```json
{
  "enabled": false
}
```

---

### User Management

#### Get Current User
`GET /users/me`

**Response 200**:
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "email": "user@example.com",
  "full_name": "John Doe",
  "role": "trader",
  "subscription_tier": "free",
  "totp_enabled": false,
  "created_at": "2025-12-01T10:00:00Z"
}
```

---

### Trading

#### Place Order
`POST /trading/orders`

**Request**:
```json
{
  "symbol": "EURUSD",
  "order_type": "BUY",
  "lot_size": 0.1,
  "price": 1.1000,
  "stop_loss": 1.0950,
  "take_profit": 1.1100
}
```

**Response 201**:
```json
{
  "id": "order_123",
  "symbol": "EURUSD",
  "trade_type": "BUY",
  "lot_size": "0.1",
  "entry_price": "1.1000",
  "stop_loss": "1.0950",
  "take_profit": "1.1100",
  "status": "open",
  "created_at": "2025-12-08T12:00:00Z"
}
```

---

#### Close Position
`PUT /trading/orders/{order_id}/close`

**Request**:
```json
{
  "close_price": 1.1050
}
```

**Response 200**:
```json
{
  "id": "order_123",
  "close_price": "1.1050",
  "profit": "50.00",
  "status": "closed",
  "closed_at": "2025-12-08T13:00:00Z"
}
```

---

#### List Open Positions
`GET /trading/positions`

**Response 200**:
```json
[
  {
    "id": "order_123",
    "symbol": "EURUSD",
    "trade_type": "BUY",
    "lot_size": "0.1",
    "entry_price": "1.1000",
    "current_price": "1.1050",
    "profit": "50.00",
    "open_time": "2025-12-08T12:00:00Z"
  }
]
```

---

#### Trade History
`GET /trading/history?limit=50&offset=0`

**Query Parameters**:
- `limit`: Number of records (default 50, max 100)
- `offset`: Pagination offset

**Response 200**:
```json
[
  {
    "id": "order_123",
    "symbol": "EURUSD",
    "trade_type": "BUY",
    "lot_size": "0.1",
    "entry_price": "1.1000",
    "close_price": "1.1050",
    "profit": "50.00",
    "open_time": "2025-12-08T12:00:00Z",
    "close_time": "2025-12-08T13:00:00Z"
  }
]
```

---

#### Calculate Position Size
`POST /trading/position-size/calculate`

**Request**:
```json
{
  "account_balance": 10000.0,
  "risk_percent": 2.0,
  "entry_price": 1.1000,
  "stop_loss": 1.0950,
  "symbol": "EURUSD"
}
```

**Response 200**:
```json
{
  "lot_size": "0.4",
  "risk_amount": "200.00",
  "stop_loss_pips": "50"
}
```

---

### Backtesting

#### Create Backtest
`POST /backtest/sessions`

**Request**:
```json
{
  "strategy_name": "MA Crossover",
  "symbol": "EURUSD",
  "timeframe": "H1",
  "start_date": "2024-01-01",
  "end_date": "2024-12-01",
  "initial_balance": 10000,
  "parameters": {
    "fast_period": 10,
    "slow_period": 30
  }
}
```

**Response 202**:
```json
{
  "session_id": "backtest_123",
  "status": "running",
  "created_at": "2025-12-08T14:00:00Z"
}
```

---

#### Get Backtest Results
`GET /backtest/sessions/{session_id}/results`

**Response 200**:
```json
{
  "session_id": "backtest_123",
  "status": "completed",
  "metrics": {
    "total_trades": 150,
    "winning_trades": 95,
    "losing_trades": 55,
    "win_rate": 63.33,
    "profit_factor": 1.85,
    "sharpe_ratio": 1.42,
    "max_drawdown": 12.5,
    "total_return": 25.8
  },
  "equity_curve": [...],
  "trades": [...]
}
```

---

### ML Bots

#### Create ML Model
`POST /ml/models`

**Request**:
```json
{
  "name": "EURUSD Predictor",
  "symbol": "EURUSD",
  "model_type": "random_forest",
  "parameters": {
    "n_estimators": 100,
    "max_depth": 10
  }
}
```

**Response 201**:
```json
{
  "model_id": "model_123",
  "name": "EURUSD Predictor",
  "status": "created",
  "created_at": "2025-12-08T15:00:00Z"
}
```

---

#### Train Model
`POST /ml/models/{model_id}/train`

**Request**:
```json
{
  "start_date": "2024-01-01",
  "end_date": "2024-11-01",
  "features": ["ma_10", "ma_30", "rsi", "macd"]
}
```

**Response 202**:
```json
{
  "model_id": "model_123",
  "status": "training",
  "estimated_time": "5 minutes"
}
```

---

#### Get Model Status
`GET /ml/models/{model_id}`

**Response 200**:
```json
{
  "model_id": "model_123",
  "name": "EURUSD Predictor",
  "status": "trained",
  "accuracy": 0.72,
  "precision": 0.68,
  "recall": 0.75,
  "f1_score": 0.71,
  "training_samples": 10000,
  "trained_at": "2025-12-08T15:10:00Z"
}
```

---

#### Activate Bot
`POST /ml/models/{model_id}/activate`

**Response 200**:
```json
{
  "model_id": "model_123",
  "status": "active",
  "activated_at": "2025-12-08T15:30:00Z"
}
```

---

#### Deactivate Bot
`POST /ml/models/{model_id}/deactivate`

**Response 200**:
```json
{
  "model_id": "model_123",
  "status": "inactive"
}
```

---

### AI Supervisor

#### Create Chat Conversation
`POST /ai/conversations`

**Response 201**:
```json
{
  "conversation_id": "conv_123",
  "created_at": "2025-12-08T16:00:00Z"
}
```

---

#### Send Message
`POST /ai/conversations/{conversation_id}/messages`

**Request**:
```json
{
  "message": "What's the market outlook for EURUSD today?"
}
```

**Response 200**:
```json
{
  "response": "Based on recent data, EURUSD shows bullish momentum. Key levels to watch are 1.1050 (resistance) and 1.0950 (support)...",
  "timestamp": "2025-12-08T16:01:00Z"
}
```

---

#### Get Market Analysis
`POST /ai/analyze/market`

**Request**:
```json
{
  "symbol": "EURUSD",
  "timeframe": "D1"
}
```

**Response 200**:
```json
{
  "symbol": "EURUSD",
  "trend": "bullish",
  "strength": 0.75,
  "support_levels": [1.0950, 1.0900, 1.0850],
  "resistance_levels": [1.1050, 1.1100, 1.1150],
  "recommendation": "Consider long positions with stop below 1.0950",
  "confidence": 0.68
}
```

---

## ⚠️ Error Responses

### Standard Error Format

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-12-08T10:00:00Z"
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 202 | Accepted (async task) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (no/invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found |
| 422 | Unprocessable Entity |
| 429 | Rate Limit Exceeded |
| 500 | Internal Server Error |

---

## 🚦 Rate Limits

| Endpoint Category | Per Minute | Per Hour |
|-------------------|------------|----------|
| Auth | 5 | 50 |
| Trading | 30 | 500 |
| Data/Query | 60 | 1000 |
| ML/AI | 10 | 100 |

**Rate limit headers**:
```
X-RateLimit-Limit: 60
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1733673600
```

**Exceeded response**:
```json
{
  "detail": "Rate limit exceeded. Maximum 60 requests per minute.",
  "retry_after": 60
}
```

---

## 🔌 WebSocket API

### Connect to WebSocket

```javascript
const ws = new WebSocket('wss://api.forexai.com/connector/ws');

ws.onopen = () => {
  // Authenticate
  ws.send(JSON.stringify({
    type: 'authenticate',
    token: 'your_jwt_token'
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
};
```

### Message Types

#### Price Update
```json
{
  "type": "price_update",
  "symbol": "EURUSD",
  "bid": 1.1050,
  "ask": 1.1052,
  "timestamp": "2025-12-08T16:30:00Z"
}
```

#### Trade Execution
```json
{
  "type": "trade_executed",
  "order_id": "order_123",
  "status": "filled",
  "fill_price": 1.1051
}
```

#### Account Update
```json
{
  "type": "account_update",
  "balance": 10250.00,
  "equity": 10300.00,
  "margin": 500.00
}
```

---

## 📦 SDK Examples

### Python

```python
import requests

# Login
response = requests.post(
    'https://api.forexai.com/api/v1/auth/login',
    json={'email': 'user@example.com', 'password': 'pass'}
)
token = response.json()['access_token']

# Place order
headers = {'Authorization': f'Bearer {token}'}
order = requests.post(
    'https://api.forexai.com/api/v1/trading/orders',
    json={
        'symbol': 'EURUSD',
        'order_type': 'BUY',
        'lot_size': 0.1,
        'price': 1.1000
    },
    headers=headers
)
print(order.json())
```

### JavaScript

```javascript
// Login
const response = await fetch('https://api.forexai.com/api/v1/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'user@example.com',
    password: 'pass'
  })
});
const { access_token } = await response.json();

// Place order
const order = await fetch('https://api.forexai.com/api/v1/trading/orders', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${access_token}`
  },
  body: JSON.stringify({
    symbol: 'EURUSD',
    order_type: 'BUY',
    lot_size: 0.1,
    price: 1.1000
  })
});
console.log(await order.json());
```

---

## 🔒 Security Best Practices

1. **Never expose your token**
   - Don't commit tokens to git
   - Don't log tokens
   - Use environment variables

2. **Token expiration**
   - Access tokens expire in 30 minutes
   - Refresh before expiry
   - Handle 401 errors gracefully

3. **HTTPS only**
   - Always use `https://` (never `http://`)
   - Verify SSL certificates

4. **Rate limiting**
   - Implement exponential backoff
   - Cache responses when possible
   - Monitor rate limit headers

5. **Enable 2FA**
   - Highly recommended for trading accounts
   - Protect against credential theft

---

## 📞 Support

- **Interactive Docs**: [https://api.forexai.com/docs](https://api.forexai.com/docs)
- **Email**: api-support@forexai.com
- **Discord**: [discord.gg/forexai](https://discord.gg/forexai)
- **GitHub**: [github.com/forexai/api-issues](https://github.com/forexai/api-issues)

---

*API Documentation v1.0.0*  
*Last Updated: December 2025*  
*© 2025 Forex AI Platform*
