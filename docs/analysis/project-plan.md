# Forex AI Trading Platform
## Complete Project Plan

---

## 1. Executive Summary

Platform web trading forex multi-user dengan:
- **Windows Connector App** untuk koneksi ke MT5 (Exness, XM, FBS, dll)
- **AI LLM Supervisor** untuk analisis dan rekomendasi
- **ML Trading Bot** untuk automated trading
- **Comprehensive Backtesting** untuk validasi strategi
- **Multi-user SaaS** yang bisa dijual ke trader

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           FOREX AI PLATFORM ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   CLOUD INFRASTRUCTURE                         USER'S MACHINE                  │
│   ════════════════════                         ══════════════                  │
│                                                                                 │
│   ┌─────────────────┐                         ┌────────────────────────────┐  │
│   │    FRONTEND     │                         │   WINDOWS CONNECTOR APP    │  │
│   │    (Vercel)     │                         │                            │  │
│   │   ┌─────────┐   │                         │  ┌──────────────────────┐  │  │
│   │   │ Next.js │   │                         │  │    PyQt6 GUI         │  │  │
│   │   │ React   │   │                         │  │  • Connection Status │  │  │
│   │   │ Charts  │   │                         │  │  • Account Info      │  │  │
│   │   └─────────┘   │                         │  │  • Trade Log         │  │  │
│   └────────┬────────┘                         │  └──────────┬───────────┘  │  │
│            │                                  │             │              │  │
│            │ HTTPS                            │    MT5 Python Library      │  │
│            ▼                                  │             │              │  │
│   ┌─────────────────┐         WebSocket       │             ▼              │  │
│   │    BACKEND      │◄═══════════════════════►│  ┌──────────────────────┐  │  │
│   │   (Railway)     │          WSS            │  │    MT5 Terminal      │  │  │
│   │                 │                         │  │  (Exness/XM/FBS)     │  │  │
│   │  ┌───────────┐  │                         │  └──────────────────────┘  │  │
│   │  │  FastAPI  │  │                         └────────────────────────────┘  │
│   │  ├───────────┤  │                                                         │
│   │  │ Services: │  │                                                         │
│   │  │ • Auth    │  │         ┌─────────────────────────────────────────┐    │
│   │  │ • Trading │  │         │              DATABASES                   │    │
│   │  │ • ML Bot  │  │         │                                         │    │
│   │  │ • Backtest│  │◄───────►│  PostgreSQL (Supabase) │ Redis (Upstash)│    │
│   │  │ • LLM     │  │         │                                         │    │
│   │  └───────────┘  │         └─────────────────────────────────────────┘    │
│   │                 │                                                         │
│   │  ┌───────────┐  │         ┌─────────────────────────────────────────┐    │
│   │  │  Celery   │  │         │           EXTERNAL SERVICES              │    │
│   │  │  Workers  │  │◄───────►│                                         │    │
│   │  │ (Railway) │  │         │  OpenAI API │ Claude API │ News APIs    │    │
│   │  └───────────┘  │         │                                         │    │
│   └─────────────────┘         └─────────────────────────────────────────┘    │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Tech Stack

### 3.1 Frontend (Web Platform)
| Technology | Purpose |
|------------|---------|
| Next.js 14 | React framework dengan App Router |
| TailwindCSS | Styling |
| shadcn/ui | UI components |
| TradingView Lightweight Charts | Trading charts |
| Socket.io-client | Real-time updates |
| Zustand | State management |
| React Query | Data fetching |

### 3.2 Backend (API Server)
| Technology | Purpose |
|------------|---------|
| Python 3.11+ | Runtime |
| FastAPI | Web framework |
| SQLAlchemy | ORM |
| Alembic | Database migrations |
| Celery | Background tasks |
| Socket.io | WebSocket server |
| Pydantic | Data validation |

### 3.3 Windows Connector App
| Technology | Purpose |
|------------|---------|
| Python 3.11+ | Runtime |
| PyQt6 | Desktop GUI |
| MetaTrader5 | Official MT5 library |
| websockets | Platform connection |
| PyInstaller | Build to .exe |

### 3.4 AI/ML Stack
| Technology | Purpose |
|------------|---------|
| OpenAI API / Claude API | LLM Supervisor |
| TensorFlow / PyTorch | ML models |
| scikit-learn | Classical ML |
| pandas / numpy | Data processing |
| ta-lib | Technical indicators |

### 3.5 Infrastructure
| Service | Purpose | Cost |
|---------|---------|------|
| Vercel | Frontend hosting | Free |
| Railway | Backend + Workers | $5/mo credit |
| Supabase | PostgreSQL + Auth | Free tier |
| Upstash | Redis | Free tier |
| Cloudflare R2 | File storage | Free 10GB |

---

## 4. Windows Connector App (Detail)

### 4.1 Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                    CONNECTOR APP ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                     PyQt6 GUI Layer                      │   │
│  │  • Main Window      • Settings Dialog    • System Tray  │   │
│  └─────────────────────────────┬───────────────────────────┘   │
│                                │                               │
│  ┌─────────────────────────────┴───────────────────────────┐   │
│  │                    Core Services                         │   │
│  │                                                          │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │   │
│  │  │ MT5 Service  │  │  WS Service  │  │Trade Executor│  │   │
│  │  │              │  │              │  │              │  │   │
│  │  │ • Connect    │  │ • Connect    │  │ • Buy/Sell   │  │   │
│  │  │ • Get Data   │  │ • Send/Recv  │  │ • Modify     │  │   │
│  │  │ • Execute    │  │ • Heartbeat  │  │ • Close      │  │   │
│  │  └──────┬───────┘  └──────┬───────┘  └──────────────┘  │   │
│  │         │                 │                             │   │
│  └─────────┼─────────────────┼─────────────────────────────┘   │
│            │                 │                                 │
│            ▼                 ▼                                 │
│     ┌────────────┐    ┌────────────────┐                      │
│     │ MT5        │    │ Cloud Platform │                      │
│     │ Terminal   │    │ (WebSocket)    │                      │
│     └────────────┘    └────────────────┘                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 GUI Design
```
┌─────────────────────────────────────────────────────────────────┐
│  ForexAI Connector                               [—] [□] [×]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  CONNECTION STATUS                                         │ │
│  │  ┌─────────────────────┐    ┌─────────────────────┐       │ │
│  │  │  Platform           │    │  MT5 Terminal        │       │ │
│  │  │  ● Connected        │    │  ● Connected        │       │ │
│  │  │  Ping: 45ms         │    │  Exness-MT5         │       │ │
│  │  └─────────────────────┘    └─────────────────────┘       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  ACCOUNT INFORMATION                                       │ │
│  │  ┌─────────────┬─────────────┬─────────────┬────────────┐ │ │
│  │  │ Balance     │ Equity      │ Margin      │ Free Margin│ │ │
│  │  │ $10,000.00  │ $10,250.00  │ $500.00     │ $9,750.00  │ │ │
│  │  └─────────────┴─────────────┴─────────────┴────────────┘ │ │
│  │  Broker: Exness │ Account: 12345678 │ Server: Real       │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  OPEN POSITIONS                                            │ │
│  │  ┌────────┬────────┬────────┬──────────┬─────────────────┐│ │
│  │  │ Symbol │ Type   │ Lots   │ Profit   │ Open Price      ││ │
│  │  ├────────┼────────┼────────┼──────────┼─────────────────┤│ │
│  │  │ EURUSD │ BUY    │ 0.10   │ +$25.00  │ 1.0890          ││ │
│  │  │ GBPUSD │ SELL   │ 0.05   │ -$12.50  │ 1.2650          ││ │
│  │  └────────┴────────┴────────┴──────────┴─────────────────┘│ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  ACTIVITY LOG                                     [Clear] │ │
│  │  ─────────────────────────────────────────────────────────│ │
│  │  10:30:15  ✓ Trade executed: BUY EURUSD 0.1 @ 1.0890     │ │
│  │  10:30:14  ← Signal received: BUY EURUSD                  │ │
│  │  10:28:03  ✓ Platform connected                           │ │
│  │  10:28:01  ✓ MT5 initialized successfully                 │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │  ▶ START     │  │  ⏹ STOP      │  │  SETTINGS            │ │
│  └──────────────┘  └──────────────┘  └──────────────────────┘ │
│                                                                 │
│  ──────────────────────────────────────────────────────────── │
│  v1.0.0 │ Uptime: 2h 15m │ Trades today: 5 │ Auto-start: ON   │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Communication Protocol
```json
// Platform → Connector (Trade Command)
{
  "type": "TRADE_COMMAND",
  "id": "cmd_123456",
  "action": "OPEN",
  "symbol": "EURUSD",
  "order_type": "BUY",
  "lot_size": 0.1,
  "stop_loss": 1.0850,
  "take_profit": 1.0950,
  "magic_number": 123456,
  "comment": "ForexAI Bot"
}

// Connector → Platform (Trade Result)
{
  "type": "TRADE_RESULT",
  "command_id": "cmd_123456",
  "success": true,
  "ticket": 12345678,
  "open_price": 1.0890,
  "timestamp": "2024-01-15T10:30:15Z"
}

// Connector → Platform (Account Update)
{
  "type": "ACCOUNT_UPDATE",
  "balance": 10000.00,
  "equity": 10250.00,
  "margin": 500.00,
  "free_margin": 9750.00,
  "profit": 250.00,
  "positions": [
    {
      "ticket": 12345678,
      "symbol": "EURUSD",
      "type": "BUY",
      "lots": 0.1,
      "open_price": 1.0890,
      "profit": 25.00
    }
  ]
}

// Heartbeat (both directions)
{
  "type": "HEARTBEAT",
  "timestamp": "2024-01-15T10:30:20Z"
}
```

### 4.4 Connector Directory Structure
```
connector-app/
├── src/
│   ├── main.py                 # Entry point
│   ├── app.py                  # Application class
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py      # Main window
│   │   ├── settings_dialog.py  # Settings
│   │   ├── system_tray.py      # Tray icon
│   │   ├── widgets/
│   │   │   ├── status_card.py
│   │   │   ├── account_info.py
│   │   │   ├── positions_table.py
│   │   │   └── activity_log.py
│   │   └── styles/
│   │       └── dark_theme.qss
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── mt5_service.py      # MT5 connection
│   │   ├── ws_service.py       # WebSocket client
│   │   ├── trade_executor.py   # Trade execution
│   │   └── sync_manager.py     # Data sync
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── account.py
│   │   ├── position.py
│   │   └── trade.py
│   │
│   └── utils/
│       ├── __init__.py
│       ├── config.py           # Configuration
│       ├── logger.py           # Logging
│       ├── crypto.py           # Encryption
│       └── updater.py          # Auto-update
│
├── resources/
│   ├── icon.ico
│   ├── icon.png
│   └── logo.png
│
├── tests/
│   ├── test_mt5_service.py
│   └── test_trade_executor.py
│
├── requirements.txt
├── build.spec                  # PyInstaller spec
├── build.py                    # Build script
└── README.md
```

---

## 5. Broker Integration

### 5.1 Supported Brokers (Indonesia)
| Broker | Platform | Status |
|--------|----------|--------|
| Exness | MT5 | Primary Support |
| XM | MT5 | Primary Support |
| FBS | MT5 | Primary Support |
| OctaFX | MT5 | Primary Support |
| ICMarkets | MT5 | Primary Support |
| HFM | MT5 | Secondary |
| Tickmill | MT5 | Secondary |
| FXTM | MT5 | Secondary |

### 5.2 Connection Flow
```
1. User Setup:
   ├── Download Connector App dari web platform
   ├── Install dan jalankan
   ├── Login dengan akun ForexAI
   ├── Pilih MT5 terminal (auto-detect)
   └── Connector ready

2. Connection:
   ├── Connector connect ke MT5 via Python lib
   ├── Connector connect ke Platform via WebSocket
   ├── Handshake & authentication
   └── Start data sync

3. Trading:
   ├── Platform kirim signal
   ├── Connector validasi
   ├── Execute di MT5
   ├── Return result
   └── Sync positions
```

---

## 6. Backtesting System

### 6.1 Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                      BACKTESTING ENGINE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐                    │
│  │  Data Manager   │    │  Strategy       │                    │
│  │                 │───▶│  Engine         │                    │
│  │  • OHLCV data   │    │                 │                    │
│  │  • Multi-TF     │    │  • Entry rules  │                    │
│  │  • Indicators   │    │  • Exit rules   │                    │
│  └─────────────────┘    │  • Position mgmt│                    │
│                         └────────┬────────┘                    │
│                                  │                              │
│  ┌─────────────────┐            │            ┌─────────────────┐│
│  │  Performance    │◀───────────┴───────────▶│  Trade          ││
│  │  Analyzer       │                         │  Simulator      ││
│  │                 │                         │                 ││
│  │  • Metrics      │                         │  • Slippage     ││
│  │  • Reports      │                         │  • Spread       ││
│  │  • Charts       │                         │  • Commission   ││
│  └─────────────────┘                         └─────────────────┘│
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 Data Sources
```python
data_sources = {
    "free": [
        "Dukascopy (Tick data)",
        "HistData.com (OHLC)",
        "Yahoo Finance",
        "User's MT5 history"
    ],
    "paid": [
        "Polygon.io",
        "Alpha Vantage"
    ]
}
```

### 6.3 Performance Metrics
| Metric | Description |
|--------|-------------|
| Net Profit | Total P/L |
| Win Rate | % winning trades |
| Profit Factor | Gross profit / Gross loss |
| Max Drawdown | Largest peak-to-trough |
| Sharpe Ratio | Risk-adjusted return |
| Sortino Ratio | Downside risk-adjusted |
| Calmar Ratio | CAGR / Max Drawdown |
| Expectancy | Expected profit per trade |
| Avg Win/Loss | Average win vs loss |
| Recovery Factor | Net profit / Max DD |

### 6.4 Backtest Features
```
├── Data Management
│   ├── Multi-timeframe (M1 - Monthly)
│   ├── Tick data support
│   ├── Gap handling
│   └── Timezone management
│
├── Simulation
│   ├── Realistic slippage
│   ├── Variable spread
│   ├── Commission
│   └── Swap calculation
│
├── Optimization
│   ├── Grid search
│   ├── Genetic algorithm
│   ├── Walk-forward analysis
│   └── Monte Carlo
│
└── Reporting
    ├── Equity curve
    ├── Drawdown chart
    ├── Trade distribution
    └── Export PDF/Excel
```

### 6.5 Backtest UI
```
┌─────────────────────────────────────────────────────────────────┐
│  Backtest Results: MA Crossover Strategy                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                     EQUITY CURVE                          │ │
│  │        ╱╲     ╱╲                                          │ │
│  │      ╱╱  ╲  ╱╱  ╲╱╲      ╱╲                              │ │
│  │    ╱╱     ╲╱        ╲──╱╱  ╲────────────                 │ │
│  │  ╱╱                                                       │ │
│  │ $10k                                              $12.5k  │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ │
│  │Net Profit│ │Win Rate │ │Profit F │ │Max DD   │ │Sharpe   │ │
│  │ +$2,450  │ │ 58.3%   │ │  1.85   │ │ -12.5%  │ │  1.42   │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ │
│                                                                 │
│  [Full Report] [Optimize] [Deploy Live]                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## 7. ML Trading Bot

### 7.1 Model Types
```
├── Price Prediction
│   ├── LSTM Network
│   ├── Transformer
│   └── XGBoost Ensemble
│
├── Signal Classification
│   ├── Random Forest
│   ├── Gradient Boosting
│   └── Neural Network
│
├── Risk Assessment
│   ├── Volatility prediction
│   └── Regime detection
│
└── Sentiment Analysis
    ├── News sentiment
    └── Social media
```

### 7.2 Features
```python
features = {
    "technical": [
        "RSI", "MACD", "Bollinger Bands",
        "ATR", "ADX", "Stochastic",
        "Moving Averages (SMA, EMA)",
        "Support/Resistance levels"
    ],
    "price_action": [
        "Candlestick patterns",
        "Price momentum",
        "Volatility measures"
    ],
    "time": [
        "Hour of day",
        "Day of week",
        "Session (Asian/London/NY)"
    ]
}
```

### 7.3 Bot Flow
```
┌─────────────────────────────────────────────────────────────────┐
│                        ML BOT FLOW                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│  │  Market  │───▶│ Feature  │───▶│   ML     │───▶│  Signal  │ │
│  │   Data   │    │Engineering│    │  Model   │    │ Generator│ │
│  └──────────┘    └──────────┘    └──────────┘    └────┬─────┘ │
│                                                        │       │
│                                                        ▼       │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐ │
│  │  Trade   │◀───│  Order   │◀───│  Risk    │◀───│ Position │ │
│  │ Executor │    │  Builder │    │  Filter  │    │  Sizer   │ │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 8. LLM Supervisor

### 8.1 Capabilities
```
├── Trade Analysis
│   ├── Explain why trade was taken
│   ├── Analyze win/loss reasons
│   └── Suggest improvements
│
├── Market Analysis
│   ├── Daily market summary
│   ├── Key levels identification
│   └── News impact assessment
│
├── Risk Assessment
│   ├── Portfolio risk analysis
│   ├── Correlation warnings
│   └── Drawdown alerts
│
├── Strategy Coach
│   ├── Answer trading questions
│   ├── Explain indicators
│   └── Education content
│
└── Anomaly Detection
    ├── Unusual market conditions
    ├── Strategy performance issues
    └── Risk threshold breaches
```

### 8.2 LLM Integration
```python
llm_config = {
    "primary": "gpt-4-turbo",      # Best quality
    "fallback": "claude-3-sonnet", # Alternative
    "local": "ollama/llama3",      # Cost-free option
}

# Context includes:
context = {
    "account_state": {...},
    "open_positions": [...],
    "recent_trades": [...],
    "market_data": {...},
    "strategy_config": {...}
}
```

### 8.3 Supervisor UI
```
┌─────────────────────────────────────────────────────────────────┐
│  AI Supervisor                                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ AI: Based on your recent trades, I noticed:               │ │
│  │                                                            │ │
│  │ 1. Win rate dropped from 65% to 52% this week             │ │
│  │ 2. Most losses occurred during Asian session              │ │
│  │ 3. GBPUSD trades have -$120 total while EURUSD is +$340  │ │
│  │                                                            │ │
│  │ Recommendation: Consider avoiding GBPUSD during Asian     │ │
│  │ hours and focus on EURUSD during London session.          │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Type your question...                              [Send] │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Quick Actions:                                                 │
│  [Analyze Today] [Market Summary] [Risk Check]                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 9. Database Schema

```sql
-- =====================
-- USERS & AUTH
-- =====================
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    full_name VARCHAR(255),
    role VARCHAR(50) DEFAULT 'trader',
    subscription_tier VARCHAR(50) DEFAULT 'free',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    plan VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'active',
    stripe_subscription_id VARCHAR(255),
    current_period_start TIMESTAMP,
    current_period_end TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================
-- BROKER CONNECTIONS
-- =====================
CREATE TABLE broker_connections (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    broker_name VARCHAR(100) NOT NULL,
    account_number VARCHAR(50),
    server VARCHAR(100),
    is_active BOOLEAN DEFAULT true,
    last_connected_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE connector_sessions (
    id UUID PRIMARY KEY,
    connection_id UUID REFERENCES broker_connections(id),
    session_token VARCHAR(255) UNIQUE,
    status VARCHAR(50) DEFAULT 'online',
    last_heartbeat TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================
-- TRADING
-- =====================
CREATE TABLE trades (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    connection_id UUID REFERENCES broker_connections(id),
    ticket BIGINT,
    symbol VARCHAR(20) NOT NULL,
    trade_type VARCHAR(10) NOT NULL,
    lot_size DECIMAL(10, 2),
    open_price DECIMAL(20, 5),
    close_price DECIMAL(20, 5),
    stop_loss DECIMAL(20, 5),
    take_profit DECIMAL(20, 5),
    profit DECIMAL(20, 2),
    commission DECIMAL(20, 2),
    swap DECIMAL(20, 2),
    open_time TIMESTAMP,
    close_time TIMESTAMP,
    magic_number INTEGER,
    comment TEXT,
    source VARCHAR(50),
    ml_model_id UUID,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE positions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    connection_id UUID REFERENCES broker_connections(id),
    ticket BIGINT,
    symbol VARCHAR(20),
    trade_type VARCHAR(10),
    lot_size DECIMAL(10, 2),
    open_price DECIMAL(20, 5),
    current_price DECIMAL(20, 5),
    stop_loss DECIMAL(20, 5),
    take_profit DECIMAL(20, 5),
    profit DECIMAL(20, 2),
    open_time TIMESTAMP,
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE signals (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    ml_model_id UUID,
    symbol VARCHAR(20),
    direction VARCHAR(10),
    confidence DECIMAL(5, 2),
    entry_price DECIMAL(20, 5),
    stop_loss DECIMAL(20, 5),
    take_profit DECIMAL(20, 5),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================
-- BACKTESTING
-- =====================
CREATE TABLE strategies (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    strategy_type VARCHAR(50),
    config JSONB,
    is_public BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE backtest_sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    strategy_id UUID REFERENCES strategies(id),
    symbol VARCHAR(20),
    timeframe VARCHAR(10),
    start_date DATE,
    end_date DATE,
    initial_balance DECIMAL(20, 2),
    config JSONB,
    status VARCHAR(50) DEFAULT 'running',
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE backtest_results (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES backtest_sessions(id),
    net_profit DECIMAL(20, 2),
    total_trades INTEGER,
    winning_trades INTEGER,
    losing_trades INTEGER,
    win_rate DECIMAL(5, 2),
    profit_factor DECIMAL(10, 2),
    max_drawdown DECIMAL(10, 2),
    max_drawdown_pct DECIMAL(5, 2),
    sharpe_ratio DECIMAL(10, 2),
    sortino_ratio DECIMAL(10, 2),
    calmar_ratio DECIMAL(10, 2),
    expectancy DECIMAL(20, 2),
    avg_win DECIMAL(20, 2),
    avg_loss DECIMAL(20, 2),
    equity_curve JSONB,
    trades JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE historical_data (
    id BIGSERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    open DECIMAL(20, 5),
    high DECIMAL(20, 5),
    low DECIMAL(20, 5),
    close DECIMAL(20, 5),
    volume DECIMAL(20, 2),
    UNIQUE(symbol, timeframe, timestamp)
);

-- =====================
-- ML MODELS
-- =====================
CREATE TABLE ml_models (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    name VARCHAR(255),
    model_type VARCHAR(50),
    config JSONB,
    performance_metrics JSONB,
    file_path VARCHAR(500),
    is_active BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE ml_predictions (
    id UUID PRIMARY KEY,
    model_id UUID REFERENCES ml_models(id),
    symbol VARCHAR(20),
    prediction JSONB,
    actual_outcome JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================
-- LLM / AI
-- =====================
CREATE TABLE llm_conversations (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    context JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE llm_messages (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES llm_conversations(id),
    role VARCHAR(20),
    content TEXT,
    tokens_used INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE market_analysis (
    id UUID PRIMARY KEY,
    symbol VARCHAR(20),
    timeframe VARCHAR(10),
    analysis_type VARCHAR(50),
    content TEXT,
    sentiment_score DECIMAL(3, 2),
    created_at TIMESTAMP DEFAULT NOW()
);

-- =====================
-- INDEXES
-- =====================
CREATE INDEX idx_trades_user_id ON trades(user_id);
CREATE INDEX idx_trades_symbol ON trades(symbol);
CREATE INDEX idx_trades_open_time ON trades(open_time);
CREATE INDEX idx_positions_user_id ON positions(user_id);
CREATE INDEX idx_historical_data_lookup ON historical_data(symbol, timeframe, timestamp);
CREATE INDEX idx_signals_user_id ON signals(user_id);
CREATE INDEX idx_backtest_sessions_user_id ON backtest_sessions(user_id);
```

---

## 10. API Structure

```
/api/v1/
│
├── /auth
│   ├── POST   /register
│   ├── POST   /login
│   ├── POST   /logout
│   ├── POST   /refresh
│   ├── POST   /forgot-password
│   └── POST   /reset-password
│
├── /users
│   ├── GET    /me
│   ├── PATCH  /me
│   └── GET    /me/stats
│
├── /brokers
│   ├── GET    /connections
│   ├── POST   /connections
│   ├── GET    /connections/:id
│   ├── DELETE /connections/:id
│   ├── GET    /connections/:id/status
│   └── POST   /connections/:id/sync
│
├── /connector
│   ├── WS     /ws
│   ├── POST   /auth
│   └── POST   /heartbeat
│
├── /trading
│   ├── GET    /positions
│   ├── POST   /orders
│   ├── PUT    /orders/:id
│   ├── DELETE /orders/:id
│   ├── GET    /history
│   └── GET    /signals
│
├── /backtest
│   ├── GET    /strategies
│   ├── POST   /strategies
│   ├── GET    /strategies/:id
│   ├── PUT    /strategies/:id
│   ├── DELETE /strategies/:id
│   ├── POST   /run
│   ├── GET    /sessions
│   ├── GET    /sessions/:id
│   └── POST   /optimize
│
├── /ml
│   ├── GET    /models
│   ├── POST   /models
│   ├── GET    /models/:id
│   ├── PUT    /models/:id
│   ├── DELETE /models/:id
│   ├── POST   /models/:id/train
│   ├── GET    /models/:id/predictions
│   └── POST   /models/:id/activate
│
├── /ai
│   ├── POST   /chat
│   ├── GET    /conversations
│   ├── GET    /conversations/:id
│   ├── GET    /analysis/daily
│   ├── GET    /analysis/:symbol
│   └── GET    /recommendations
│
├── /data
│   ├── GET    /symbols
│   ├── GET    /candles
│   └── WS     /prices
│
└── /admin
    ├── GET    /users
    ├── GET    /stats
    └── GET    /revenue
```

---

## 11. Directory Structure

```
forex-ai/
├── frontend/                          # Next.js Web App
│   ├── app/
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   ├── register/
│   │   │   └── forgot-password/
│   │   ├── (dashboard)/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── trading/
│   │   │   ├── backtest/
│   │   │   ├── bots/
│   │   │   ├── ai-supervisor/
│   │   │   ├── connections/
│   │   │   └── settings/
│   │   └── api/
│   ├── components/
│   │   ├── ui/
│   │   ├── charts/
│   │   ├── trading/
│   │   ├── backtest/
│   │   └── layout/
│   ├── lib/
│   ├── hooks/
│   ├── stores/
│   ├── types/
│   ├── public/
│   ├── package.json
│   └── next.config.js
│
├── backend/                          # FastAPI Backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py
│   │   │   ├── v1/
│   │   │   │   ├── router.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── users.py
│   │   │   │   ├── brokers.py
│   │   │   │   ├── trading.py
│   │   │   │   ├── backtest.py
│   │   │   │   ├── ml.py
│   │   │   │   └── ai.py
│   │   │   └── websocket/
│   │   │       └── connector.py
│   │   ├── core/
│   │   │   ├── security.py
│   │   │   ├── database.py
│   │   │   └── redis.py
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── backtesting/
│   │   │   ├── engine.py
│   │   │   ├── data_manager.py
│   │   │   ├── simulator.py
│   │   │   ├── metrics.py
│   │   │   ├── optimizer.py
│   │   │   └── strategies/
│   │   └── ml/
│   │       ├── features.py
│   │       ├── models/
│   │       └── training.py
│   ├── workers/
│   │   ├── celery_app.py
│   │   ├── backtest_worker.py
│   │   └── ml_worker.py
│   ├── migrations/
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── alembic.ini
│
├── connector/                        # Windows Connector App
│   ├── src/
│   │   ├── main.py
│   │   ├── app.py
│   │   ├── ui/
│   │   ├── core/
│   │   ├── models/
│   │   └── utils/
│   ├── resources/
│   ├── tests/
│   ├── requirements.txt
│   ├── build.spec
│   └── build.py
│
├── ml/                               # ML Training
│   ├── notebooks/
│   ├── data/
│   ├── models/
│   └── scripts/
│
├── docker/
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   ├── Dockerfile.backend
│   └── Dockerfile.frontend
│
├── docs/
│   ├── api.md
│   ├── connector-setup.md
│   └── deployment.md
│
├── .github/
│   └── workflows/
│       ├── backend.yml
│       ├── frontend.yml
│       └── connector.yml
│
├── .gitignore
├── README.md
└── project-plan.md
```

---

## 12. Development Phases & Timeline

### Phase 1: Foundation (4-5 minggu)
```
Week 1-2:
├── Project setup (repos, CI/CD)
├── Database schema & migrations
├── Auth system (Supabase Auth)
└── Basic API structure

Week 3-4:
├── User management
├── Frontend skeleton
└── Basic dashboard UI

Week 5:
├── Testing & bug fixes
└── Deploy to staging
```

### Phase 2: Windows Connector (3-4 minggu)
```
Week 6-7:
├── MT5 Python integration
├── WebSocket communication
└── Basic GUI

Week 8-9:
├── Trade execution
├── Account sync
├── Auto-update system
└── Build & distribute .exe
```

### Phase 3: Backtesting (3-4 minggu)
```
Week 10-11:
├── Historical data management
├── Backtest engine core
└── Strategy framework

Week 12-13:
├── Performance metrics
├── Optimization
├── Backtest UI
└── Report generation
```

### Phase 4: ML Trading Bot (4-5 minggu)
```
Week 14-15:
├── Feature engineering
├── Model development
└── Training pipeline

Week 16-18:
├── Signal generation
├── Bot execution engine
├── Performance tracking
└── Bot management UI
```

### Phase 5: LLM Supervisor (3-4 minggu)
```
Week 19-20:
├── LLM integration
├── Context building
└── Chat interface

Week 21-22:
├── Analysis features
├── Recommendations
└── Alerts system
```

### Phase 6: Monetization & Polish (2-3 minggu)
```
Week 23-25:
├── Stripe/Midtrans integration
├── Subscription management
├── Admin dashboard
├── Documentation
└── Production deployment
```

**Total: 19-25 minggu (5-6 bulan)**

---

## 13. Cost Estimation

### Development Phase (Monthly)
| Item | Cost |
|------|------|
| Railway (Backend) | $5 (free credit) |
| Vercel (Frontend) | Free |
| Supabase (Database) | Free |
| Upstash (Redis) | Free |
| Domain | ~$12/year |
| **Total** | **~$5/month** |

### Production Phase (Monthly)
| Item | Free | Scale |
|------|------|-------|
| Railway | $5 | $20-50 |
| Vercel | Free | $20 |
| Supabase | Free | $25 |
| Upstash | Free | $10 |
| OpenAI API | - | $20-100 |
| Cloudflare R2 | Free | $5 |
| **Total** | **~$5** | **~$100-210** |

### Payment Gateway (Per Transaction)
| Gateway | Fee |
|---------|-----|
| Stripe | 2.9% + $0.30 |
| Midtrans (IDR) | 2.9% + Rp2,000 |

---

## 14. Pricing Model (Suggestion)

| Tier | Price | Features |
|------|-------|----------|
| **Free** | $0 | 1 broker, basic backtest, limited AI |
| **Pro** | $29/mo | 3 brokers, full backtest, ML bot (1), full AI |
| **Enterprise** | $99/mo | Unlimited brokers, all features, priority support |

---

## 15. Security Checklist

- [ ] HTTPS everywhere
- [ ] JWT with short expiry + refresh tokens
- [ ] Password hashing (bcrypt)
- [ ] Rate limiting
- [ ] Input validation (Pydantic)
- [ ] SQL injection prevention (ORM)
- [ ] XSS protection
- [ ] CORS configuration
- [ ] Secrets in environment variables
- [ ] Connector token encryption
- [ ] Audit logging for trades
- [ ] 2FA support

---

## 16. Next Steps

1. Setup project structure
2. Initialize Git repository
3. Setup CI/CD pipelines
4. Create database schema
5. Start Phase 1: Foundation
