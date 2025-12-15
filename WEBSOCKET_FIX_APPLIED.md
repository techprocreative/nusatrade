# WebSocket Connection Fix - Applied

## Problem Summary
**Error:** `WebSocket connection rejected (403 Forbidden)`

**Root Cause:**
1. Token expired causing `GET /api/v1/brokers/connections` to return 401
2. `connection_id` not retrieved from backend
3. WebSocket connection attempted without required `connection_id` parameter
4. Backend rejected connection (requires both `token` AND `connection_id`)

## Fixes Applied

### Fix 1: Enhanced Error Handling in Registration
**File:** `connector/src/ui/main_window.py`
**Method:** `_register_broker_connection()`

**Changes:**
- Added return type `-> bool`
- Check for 401 (expired token) and show clear error
- Check for other HTTP errors
- Return `True` on success, `False` on failure
- Better logging with connection ID

### Fix 2: Validation Before WebSocket Connect
**File:** `connector/src/ui/main_window.py`
**Method:** `_connect()` around line 383

**Changes:**
- Check if `_register_broker_connection()` succeeded
- If failed, show error and abort connection
- Display connection ID on success
- Prevent WebSocket connect without valid connection_id

### Fix 3: Fixed URL Building (No Duplicate Token)
**File:** `connector/src/ui/main_window.py`
**Method:** `_connect()` around line 418

**Changes:**
- Build complete URL with both `connection_id` and `token`
- Pass `token=None` to WebSocketService (already in URL)
- Order: `?connection_id=X&token=Y` (consistent)

### Fix 4: Smart Token Handling in WebSocketService
**File:** `connector/src/core/ws_service.py`
**Method:** `_connect()`

**Changes:**
- Check if `token=` already in URL before adding
- Only add token if not already present
- Added debug logging for connection URL

## How to Deploy

### Step 1: Rebuild Connector (Windows VPS)

```bash
# On Windows VPS, open PowerShell/CMD
cd C:\path\to\nusatrade\connector

# Install/update dependencies (if needed)
pip install -r requirements.txt

# Build executable
python build.py

# Result will be in: dist/NusaTradeConnector.exe
```

### Step 2: Test the Fix

1. **Close old connector** if running
2. **Run new connector:** `dist/NusaTradeConnector.exe`
3. **Login** with credentials
4. **Connect to MT5** with your broker credentials

**Expected Behavior:**
```
✅ MT5 connected successfully
✅ Detected: [Broker Name] - [Account Number]
✅ Using existing connection: [UUID] OR
✅ Registered new connection: [UUID]
✅ Connection ID: [UUID]
✅ Connecting to server...
✅ Connected
```

**If Token Expired:**
```
❌ Token expired - please re-login
❌ Failed to register broker connection
❌ Please re-login and try again
MT5: 🔴 Registration Failed
```

**Action:** Close connector, re-login, try again

### Step 3: Verify WebSocket Connection

**Check Render logs:**
```
INFO: ('IP', 0) - "WebSocket /connector/ws?connection_id=UUID&token=..."
INFO: connection accepted
```

**Should NOT see:**
```
INFO: connection rejected (403 Forbidden)  ← Fixed!
```

## Error Messages Explained

| Error Message | Cause | Solution |
|--------------|-------|----------|
| `Token expired - please re-login` | JWT token expired | Re-login to connector |
| `Failed to fetch connections: 401` | Authentication failed | Re-login to connector |
| `Failed to register connection: XXX` | Backend API error | Check backend logs |
| `Not authenticated - cannot register connection` | Not logged in | Login first |
| `❌ Failed to register broker connection` | Registration failed | Check error above, re-login |

## Testing Checklist

- [ ] Connector builds successfully
- [ ] Login works
- [ ] MT5 connection works
- [ ] Broker connection registered (see UUID in logs)
- [ ] WebSocket connects successfully
- [ ] No 403 errors in backend logs
- [ ] Can send/receive commands
- [ ] Auto-trading can execute trades

## Rollback Plan

If issues occur, use old connector version. No backend changes were made, so backend is compatible with both old and new connector versions.

## Next Steps

Once WebSocket is connected:
1. Test manual trade execution
2. Enable ML bot
3. Monitor auto-trading cycle
4. Check trade execution in MT5

## Technical Details

**WebSocket URL Format (Fixed):**
```
wss://nusatrade.onrender.com/connector/ws?connection_id=<UUID>&token=<JWT>
```

**Backend expects:**
- `connection_id` (required) - UUID from broker connections table
- `token` (required) - Valid JWT from login

**Connector flow (Fixed):**
1. Login → Get JWT token
2. Connect MT5 → Get account info
3. Register connection → Get connection_id (with validation!)
4. Build WebSocket URL → Both params included
5. Connect WebSocket → Backend accepts

## Files Changed

1. `connector/src/ui/main_window.py` - 3 fixes
2. `connector/src/core/ws_service.py` - 1 fix

Total: 4 fixes, 2 files

---

**Status:** ✅ Ready for Deployment
**Date:** 2025-12-15
**Version:** Post-fix v1.0.1
