# 📘 Forex AI Connector - User Manual

Complete guide for installing and using the Forex AI Windows Connector application.

## 📖 Table of Contents

1. [What is Forex AI Connector?](#what-is-forex-ai-connector)
2. [System Requirements](#system-requirements)
3. [Installation](#installation)
4. [Getting Started](#getting-started)
5. [Features](#features)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)
8. [Support](#support)

---

## What is Forex AI Connector?

The Forex AI Connector is a Windows desktop application that bridges your MetaTrader 5 (MT5) trading terminal with the Forex AI Platform. It allows:

- ✅ Real-time trade execution from web dashboard
- ✅ Live price streaming to platform
- ✅ Position monitoring
- ✅ Account synchronization
- ✅ Automated trading with ML bots

**Important**: The connector runs locally on your Windows PC where MT5 is installed.

---

## System Requirements

### Minimum Requirements

- **OS**: Windows 10 or later (64-bit)
- **RAM**: 4 GB
- **Disk Space**: 100 MB
- **Internet**: Stable broadband connection
- **MT5**: MetaTrader 5 installed and logged in

### Recommended

- **OS**: Windows 11 (64-bit)
- **RAM**: 8 GB or more
- **Internet**: Fiber/Cable with low latency
- **MT5**: Latest version

### Supported Brokers

The connector works with any MT5 broker, including:
- Exness
- XM
- FXTM
- IC Markets
- Pepperstone
- Admiral Markets
- FBS
- And more...

---

## Installation

### Step 1: Download Connector

1. Go to [https://app.forexai.com/download](https://app.forexai.com/download)
2. Click **Download Windows Connector**
3. Save `ForexAI-Connector-Setup.exe` to your Downloads folder

### Step 2: Install Application

1. Double-click `ForexAI-Connector-Setup.exe`
2. If Windows SmartScreen appears:
   - Click **More info**
   - Click **Run anyway**
3. Follow installation wizard:
   - Accept license agreement
   - Choose installation folder (default: `C:\Program Files\ForexAI\`)
   - Click **Install**
4. Click **Finish** when complete

### Step 3: Launch Connector

- Desktop shortcut created automatically
- Or find in Start Menu: **Forex AI Connector**

---

## Getting Started

### First Time Setup

#### 1. Login to Connector

When you first launch the connector:

1. **Enter Credentials**:
   - Email: Your Forex AI account email
   - Password: Your account password
   - Check "Remember me" (optional)

2. **Click Login**

#### 2. Connect MT5 Terminal

After login, the main window shows:

1. **MT5 Status**: Checking...
2. The connector automatically detects MT5

**If MT5 not detected**:
- Ensure MT5 is running
- Log into your trading account in MT5
- Click **Refresh** in connector

#### 3. Link Trading Account

Once MT5 is detected:

1. Connector shows your MT5 account number
2. Click **Link Account** button
3. Account will be linked to your Forex AI profile
4. Status changes to **Connected** ✅

**Success!** Your connector is now active.

---

## Features

### Main Window Overview

```
┌─────────────────────────────────────┐
│  Forex AI Connector          [_][□][X]│
├─────────────────────────────────────┤
│ Status: Connected ✅                │
│                                     │
│ Account: 12345678                   │
│ Balance: $10,000.00                 │
│ Equity:  $10,250.00                 │
│ Margin:  $500.00                    │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Open Positions (3)              │ │
│ │ EURUSD  BUY  0.1  +$25.00      │ │
│ │ GBPUSD  SELL 0.2  -$15.00      │ │
│ │ USDJPY  BUY  0.1  +$40.00      │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ Activity Log                    │ │
│ │ [12:30] Connected to server     │ │
│ │ [12:31] Position opened: EURUSD│ │
│ │ [12:32] Price update received  │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [ Settings ]  [ Help ]  [ Disconnect ]│
└─────────────────────────────────────┘
```

### System Tray

When minimized, connector runs in system tray:

- **Green icon**: Connected and active
- **Yellow icon**: Connecting...
- **Red icon**: Disconnected
- **Gray icon**: MT5 not detected

**Right-click tray icon** for quick actions:
- Show/Hide window
- Disconnect
- Exit

### Notifications

Desktop notifications for:
- ✅ Trade executed
- ✅ Position closed
- ⚠️ Connection lost
- ⚠️ Error occurred

---

## Using the Connector

### Trading from Web Dashboard

1. Go to [app.forexai.com/trading](https://app.forexai.com/trading)
2. Ensure connector shows **Connected**
3. Place trade on web dashboard
4. Connector executes immediately in MT5
5. See confirmation in connector activity log

### Real-Time Price Streaming

- Connector streams live prices to platform
- Updates every tick
- No manual refresh needed
- Low latency (<100ms typical)

### Position Monitoring

All open positions shown in:
- Connector main window
- Web dashboard
- Synced in real-time

### Account Information

Connector displays:
- Account number
- Balance
- Equity
- Free margin
- Leverage
- Server name

Updates every second.

---

## Settings

Click **Settings** button to configure:

### Connection Settings

- **Server URL**: Backend API URL (auto-configured)
- **WebSocket Port**: Default 8000
- **Reconnect**: Auto-reconnect on disconnect
- **Timeout**: Connection timeout (default 30s)

### MT5 Settings

- **Auto-detect**: Automatically find MT5
- **Manual Path**: Specify MT5 installation path
- **Polling Interval**: How often to check MT5 (default 1s)

### Notifications

- ☑️ Desktop notifications
- ☑️ Sound alerts
- ☑️ Trade confirmations
- ☑️ Error alerts

### Advanced

- **Logging Level**: Debug/Info/Warning/Error
- **Log File**: View logs for troubleshooting
- **Auto-start**: Start connector with Windows
- **Minimize to tray**: Hide to system tray on minimize

---

## Troubleshooting

### Common Issues

#### 1. "Cannot detect MT5"

**Possible causes**:
- MT5 not running
- Not logged into MT5 account
- MT5 installed in non-standard location

**Solutions**:
1. Launch MT5 and log into your account
2. Click **Refresh** in connector
3. If still not detected, go to Settings → MT5 Settings
4. Click **Browse** and locate `terminal64.exe`
   - Default: `C:\Program Files\MetaTrader 5\terminal64.exe`

#### 2. "Connection to server failed"

**Possible causes**:
- No internet connection
- Firewall blocking connector
- Server maintenance

**Solutions**:
1. Check your internet connection
2. Add connector to Windows Firewall exceptions
3. Check [status.forexai.com](https://status.forexai.com) for server status
4. Restart connector

#### 3. "Authentication failed"

**Solutions**:
1. Verify email and password are correct
2. Reset password at [app.forexai.com/reset-password](https://app.forexai.com/reset-password)
3. Check if 2FA is enabled (enter TOTP code)
4. Contact support if issue persists

#### 4. Trades not executing

**Check**:
- Connector shows **Connected** status
- MT5 is logged in and active
- Account has sufficient margin
- Symbol is available in MT5
- Market is open

**Debug**:
1. Check Activity Log for errors
2. Try manual trade in MT5 to verify account
3. Review Settings → Connection Settings
4. Restart connector

#### 5. High CPU/Memory usage

**Solutions**:
1. Close unnecessary programs
2. Reduce Polling Interval in Settings
3. Disable Debug logging
4. Update to latest connector version

#### 6. Connector crashes

**Steps**:
1. Check Windows Event Viewer for errors
2. Review log files in `%APPDATA%\ForexAI\logs\`
3. Reinstall connector
4. Contact support with log files

---

## FAQ

### Q: Do I need to keep connector running 24/7?

**A**: Yes, for automated trading and ML bots. For manual trading, only when placing trades.

### Q: Can I use multiple MT5 accounts?

**A**: Currently one MT5 account per connector instance. Run multiple connectors for multiple accounts.

### Q: What happens if my PC restarts?

**A**: Enable "Auto-start with Windows" in Settings. Connector will launch and reconnect automatically.

### Q: Is my data secure?

**A**: Yes. All communication is encrypted (SSL/TLS). Your MT5 password is never sent to our servers.

### Q: Can I use on Mac or Linux?

**A**: Not currently. Windows-only due to MT5 API. Web dashboard works on all platforms.

### Q: Does it work with MT4?

**A**: No, only MetaTrader 5 (MT5) is supported.

### Q: What's the latency?

**A**: Typical latency is 50-100ms for trade execution, depending on your internet connection.

### Q: Will it slow down my MT5?

**A**: No significant impact. Connector uses minimal resources.

### Q: Can I still trade manually in MT5?

**A**: Yes! Connector doesn't interfere with manual trading. All trades sync automatically.

### Q: What if I disconnect?

**A**: Existing positions remain open. Reconnect to resume monitoring and automated trading.

---

## Best Practices

### ✅ Do's

- ✅ Keep connector updated
- ✅ Enable auto-start if using bots
- ✅ Monitor Activity Log regularly
- ✅ Keep MT5 logged in
- ✅ Stable internet connection
- ✅ Allow through firewall
- ✅ Backup MT5 settings
- ✅ Test with demo account first

### ❌ Don'ts

- ❌ Don't run on public/shared computers
- ❌ Don't share account credentials
- ❌ Don't disable SSL verification
- ❌ Don't modify connector files
- ❌ Don't run without antivirus
- ❌ Don't trade on unstable internet

---

## Updating Connector

### Auto-Update (Recommended)

1. Connector checks for updates on startup
2. Notification appears when update available
3. Click **Update Now**
4. Connector downloads and installs automatically
5. Restart connector when prompted

### Manual Update

1. Download latest version from website
2. Run installer (overwrites old version)
3. No need to uninstall first
4. Settings and logs preserved

---

## Uninstalling

### Standard Uninstall

1. Close connector
2. Windows Settings → Apps
3. Find "Forex AI Connector"
4. Click **Uninstall**
5. Follow wizard

### Complete Removal

Also delete:
- `%APPDATA%\ForexAI\` (settings and logs)
- Desktop shortcut
- Start Menu shortcut

---

## Support

### Getting Help

1. **In-App Help**: Click **Help** button
2. **Documentation**: [docs.forexai.com/connector](https://docs.forexai.com/connector)
3. **Video Tutorials**: [youtube.com/@forexai](https://youtube.com/@forexai)
4. **Email Support**: support@forexai.com
5. **Discord Community**: [discord.gg/forexai](https://discord.gg/forexai)
6. **Live Chat**: Available on website

### Reporting Bugs

When reporting issues, include:

1. **Connector version** (Help → About)
2. **Windows version**
3. **MT5 version and broker**
4. **Error message** (screenshot)
5. **Activity log** (Help → View Logs)
6. **Steps to reproduce**

---

## Terms & Disclaimers

### Trading Risks

⚠️ **Warning**: Trading forex carries substantial risk of loss. Only trade with money you can afford to lose. Past performance is not indicative of future results.

### Connector Liability

- Connector provided "as-is"
- No guarantee of uptime or accuracy
- User responsible for verifying trades
- Always monitor your MT5 account
- Use stop-loss for risk management

### Data Privacy

- Your MT5 password stays on your PC
- Trade data encrypted in transit
- Read full [Privacy Policy](https://forexai.com/privacy)

---

## Keyboard Shortcuts

- `Ctrl + R`: Refresh MT5 connection
- `Ctrl + S`: Open Settings
- `Ctrl + L`: View Activity Log
- `Ctrl + D`: Disconnect
- `Ctrl + Q`: Quit (prompts confirmation)
- `F1`: Open Help
- `F11`: Toggle fullscreen

---

## Changelog

### Version 1.0.0 (Current)
- ✨ Initial release
- ✅ MT5 integration
- ✅ Real-time price streaming
- ✅ Trade execution
- ✅ Position monitoring
- ✅ System tray support

### Upcoming Features
- 🔜 Multi-account support
- 🔜 Trade journal integration
- 🔜 Custom alerts
- 🔜 Advanced charting
- 🔜 Strategy tester integration

---

**Thank you for using Forex AI Connector!** 🚀

Trade smart, trade automated.

---

*User Manual v1.0.0*  
*Last Updated: December 2025*  
*© 2025 Forex AI Platform. All rights reserved.*
