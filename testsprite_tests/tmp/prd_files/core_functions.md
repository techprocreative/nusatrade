# NusaTrade - Core Functions PRD

## Overview
NusaTrade is an AI-powered forex trading platform that combines machine learning, backtesting, and LLM-based trading supervision with MetaTrader 5 integration.

## Core Functions to Verify

### CF1: AI Strategy Generation
**Description**: Create trading strategies using AI/LLM based on natural language prompts

**Acceptance Criteria**:
- User can submit a natural language description of a trading strategy
- System generates a complete strategy with entry/exit rules, indicators, and risk management
- Generated strategy includes code, parameters, and explanations
- Response includes warnings and suggested improvements

**API Endpoint**: `POST /api/v1/ai/generate-strategy`

**Input**:
- `prompt`: Strategy description in natural language
- `symbol`: Trading symbol (e.g., "EURUSD")
- `timeframe`: Chart timeframe (e.g., "H1")
- `risk_profile`: conservative, moderate, or aggressive
- `preferred_indicators`: Optional list of indicators

**Expected Output**:
- Complete strategy object with name, description, code, parameters
- Entry and exit rules
- Risk management settings
- Explanation and warnings

---

### CF2: Backtest Strategy
**Description**: Test trading strategies with historical market data

**Acceptance Criteria**:
- User can run backtest on any strategy with specified date range
- System calculates key metrics (net profit, win rate, Sharpe ratio, etc.)
- Equity curve and trade history are returned
- Data can be loaded from yfinance or database cache

**API Endpoint**: `POST /api/v1/backtest/run`

**Input**:
- `strategy_id`: ID of strategy to test
- `symbol`: Trading symbol
- `timeframe`: Chart timeframe
- `start_date`: Backtest start date
- `end_date`: Backtest end date
- `initial_balance`: Starting capital
- `commission`: Trading commission
- `slippage`: Price slippage

**Expected Output**:
- Net profit/loss
- Total trades, winning/losing trades
- Win rate, profit factor
- Max drawdown
- Sharpe ratio, Sortino ratio
- Equity curve data

---

### CF3: MT5 Connector Integration
**Description**: Connect Windows connector app with the platform via WebSocket

**Acceptance Criteria**:
- Connector app can authenticate with JWT token
- WebSocket connection is established and maintained
- Connection status is tracked and visible
- Trade commands can be sent from dashboard to connector
- Real-time updates are pushed to dashboard clients

**WebSocket Endpoints**:
- `WS /connector/ws` - For connector apps
- `WS /connector/client` - For dashboard clients

**Message Types**:
- `TRADE_COMMAND`: Execute trade on MT5
- `CONNECTIONS_STATUS`: Current connection status
- `PING/PONG`: Keep-alive

---

### CF4: AI/ML Bot Deployment
**Description**: Train and deploy ML models for automated trading

**Acceptance Criteria**:
- User can create ML model configurations
- Model training can be initiated
- Trained models can generate predictions
- Models can be activated/deactivated for live trading
- Performance metrics are tracked

**API Endpoints**:
- `POST /api/v1/ml/models` - Create model
- `POST /api/v1/ml/models/{id}/train` - Train model
- `POST /api/v1/ml/models/{id}/predict` - Get prediction
- `POST /api/v1/ml/models/{id}/activate` - Activate for trading

**Expected Output**:
- Model performance metrics after training
- Predictions with direction and confidence
- Active model status

---

### CF5: AI LLM Trading Supervision
**Description**: AI supervisor monitors trading and provides analysis

**Acceptance Criteria**:
- User can chat with AI about trading
- AI provides daily market analysis
- AI can analyze specific symbols
- AI gives trading recommendations
- Conversation history is maintained

**API Endpoints**:
- `POST /api/v1/ai/chat` - Chat with AI
- `GET /api/v1/ai/analysis/daily` - Daily analysis
- `GET /api/v1/ai/analysis/{symbol}` - Symbol analysis
- `GET /api/v1/ai/recommendations` - Get recommendations

**Expected Output**:
- Chat responses with context
- Market analysis text
- Trading recommendations
- Conversation persistence
