# ForexAI Windows Connector

Desktop application untuk menghubungkan MetaTrader 5 dengan backend ForexAI.

## Requirements

- Windows 10/11
- MetaTrader 5 terinstall
- Python 3.10+

## Installation

### From Source (Development)

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
cd src
python main.py
```

### Build Executable

```bash
# Build .exe file
python build.py

# Output: dist/ForexAI-Connector.exe
```

## Features

- **MT5 Connection**: Connect ke akun demo/live MT5
- **WebSocket**: Real-time connection ke backend server
- **Auto-reconnect**: Reconnect otomatis jika koneksi terputus
- **Trade Execution**: Eksekusi order dari backend
- **Position Sync**: Sinkronisasi posisi terbuka
- **Account Monitoring**: Monitoring balance, equity, margin

## Configuration

Konfigurasi tersimpan di:
- Windows: `%APPDATA%/ForexAIConnector/config.json`
- Linux: `~/.config/forexai-connector/config.json`

### MT5 Settings

| Setting | Description |
|---------|-------------|
| Login | Nomor akun MT5 |
| Password | Password investor/trading |
| Server | Nama server broker |

### Server Settings

| Setting | Description |
|---------|-------------|
| Host | Backend server hostname |
| Port | Backend server port |
| SSL | Gunakan HTTPS/WSS |
| Token | JWT token untuk auth |

## Architecture

```
connector/
├── src/
│   ├── main.py           # Entry point
│   ├── app.py            # Qt application
│   ├── core/
│   │   ├── mt5_service.py    # MT5 API wrapper
│   │   ├── ws_service.py     # WebSocket client
│   │   └── config.py         # Configuration
│   └── ui/
│       └── main_window.py    # GUI
├── requirements.txt
└── build.py              # PyInstaller script
```

## Message Protocol

### From Server to Connector

```json
{"type": "TRADE_OPEN", "symbol": "EURUSD", "order_type": "BUY", "lot_size": 0.1}
{"type": "TRADE_CLOSE", "ticket": 123456}
{"type": "SYNC_REQUEST"}
{"type": "GET_POSITIONS"}
{"type": "GET_ACCOUNT"}
```

### From Connector to Server

```json
{"type": "TRADE_RESULT", "success": true, "ticket": 123456}
{"type": "SYNC_RESPONSE", "positions": [...], "account": {...}}
{"type": "POSITIONS", "data": [...]}
{"type": "ACCOUNT_INFO", "balance": 10000, "equity": 10500}
```

## Troubleshooting

### MT5 Connection Failed
- Pastikan MT5 sudah terbuka dan login
- Cek login, password, dan server
- Pastikan MetaTrader5 library terinstall

### WebSocket Connection Failed
- Cek host dan port server
- Pastikan backend running
- Cek firewall settings

### Build Failed
- Install Visual C++ Build Tools (Windows)
- Pastikan PyInstaller terinstall
