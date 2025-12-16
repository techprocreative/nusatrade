# 🧪 Testing Guide: Strategy Templates Fix

**Date**: 2025-12-16
**Backend**: https://nusatrade.onrender.com
**Frontend**: https://nusatrade-beta.vercel.app

---

## ✅ Fixes Deployed

3 commits have been pushed to fix strategy templates:

1. **`c6bdee1`** - Backend filter: Include public preset strategies
2. **`61600f7`** - Pydantic validation: Transform data to match schema
3. **`cb67727`** - Strategy selector: Include public templates for ML models

---

## 🚀 Deployment Status

### Backend (Render)
- Repo: https://github.com/techprocreative/nusatrade
- Auto-deploy from: `main` branch
- Status: Check Render dashboard

### Frontend (Vercel)
- Repo: https://github.com/techprocreative/nusatrade
- Auto-deploy from: `main` branch (frontend folder)
- Status: Check Vercel dashboard

---

## 🧪 Manual Testing

### Test 1: Run Automated Test Script

```bash
cd /media/d88k/01D9C5CA3CB3C3E0/edo/nusatrade/backend
source venv/bin/activate
python scripts/test_endpoints.py
```

This will:
1. Ask for your auth token
2. Test 5 endpoints
3. Verify public templates are returned
4. Show detailed results

**Expected Output**:
```
✅ PASS | List All Strategies (4 preset templates)
✅ PASS | Strategies for XAUUSD (1 preset template)
✅ PASS | Strategies for EURUSD (1 preset template)
✅ PASS | Strategies for GBPUSD (1 preset template)
✅ PASS | Strategies for USDJPY (1 preset template)

🎉 ALL TESTS PASSED!
```

---

### Test 2: Frontend UI Testing

#### 2.1 Test `/strategies` Tab "Templates"
1. Open https://nusatrade-beta.vercel.app/strategies
2. Login if needed
3. Click tab "Templates"
4. **Expected**: 4 strategy cards displayed:
   - XAUUSD Profitable Strategy (H1)
   - EURUSD Profitable Strategy (H1)
   - GBPUSD Profitable Strategy (H1)
   - USDJPY Profitable Strategy (H1)

#### 2.2 Test "Import to My Bots" Modal
1. Open https://nusatrade-beta.vercel.app/bots
2. Scroll to "Profitable Pre-trained Models" section
3. Click "Import to My Bots" for XAUUSD
4. Wait for import to complete
5. Modal "Link Strategy to Model" should auto-open
6. **Expected**: Dropdown shows "XAUUSD Profitable Strategy (H1)"
7. Select the strategy and click "Link Strategy"

#### 2.3 Test "Create New Model" Modal
1. Open https://nusatrade-beta.vercel.app/bots
2. Click "+ Create Model"
3. Fill in:
   - Name: "Test Model"
   - Symbol: XAUUSD
4. Scroll to "Link to Strategy (Optional)"
5. Click the dropdown
6. **Expected**: Shows:
   - "No Strategy"
   - "XAUUSD Profitable Strategy (H1)" (if exists)
   - Any other user strategies

---

## 🔍 API Testing via Browser Console

If UI still shows empty, test API directly:

### 1. Get Your Token
```javascript
// Open browser console (F12) on frontend
const token = localStorage.getItem('token')
console.log('Token:', token)
```

### 2. Test Endpoint: List All Strategies
```javascript
fetch('https://nusatrade.onrender.com/api/v1/strategies', {
  headers: { 'Authorization': `Bearer ${token}` }
})
.then(r => r.json())
.then(data => {
  console.log('Total strategies:', data.length)
  const presets = data.filter(s => s.strategy_type === 'preset')
  console.log('Preset templates:', presets.length)
  console.log('Presets:', presets.map(s => `${s.symbol} - ${s.name}`))
})
```

**Expected Console Output**:
```
Total strategies: 4 (or more if user has own strategies)
Preset templates: 4
Presets: [
  "XAUUSD - XAUUSD Profitable Strategy (H1)",
  "EURUSD - EURUSD Profitable Strategy (H1)",
  "GBPUSD - GBPUSD Profitable Strategy (H1)",
  "USDJPY - USDJPY Profitable Strategy (H1)"
]
```

### 3. Test Endpoint: Strategies for XAUUSD
```javascript
fetch('https://nusatrade.onrender.com/api/v1/ml/strategies/for-model/XAUUSD', {
  headers: { 'Authorization': `Bearer ${token}` }
})
.then(r => r.json())
.then(data => {
  console.log('Response:', data)
  console.log('Strategies for XAUUSD:', data.strategies.length)
  console.log('Strategy names:', data.strategies.map(s => s.name))
})
```

**Expected Console Output**:
```
Strategies for XAUUSD: 1 (or more if user has XAUUSD strategies)
Strategy names: ["XAUUSD Profitable Strategy (H1)"]
```

---

## 🐛 Troubleshooting

### Problem: Still showing empty

#### Solution 1: Check Render Deployment
1. Go to Render dashboard
2. Find "nusatrade" service
3. Check "Events" tab
4. Verify latest deploy succeeded
5. Check deploy time - should be after 2025-12-16 09:40 UTC

#### Solution 2: Hard Refresh Browser
```
Windows/Linux: Ctrl + Shift + R
Mac: Cmd + Shift + R
```

#### Solution 3: Clear React Query Cache
```javascript
// In browser console
localStorage.clear()
sessionStorage.clear()
location.reload()
```

#### Solution 4: Check Network Tab
1. Open browser DevTools (F12)
2. Go to "Network" tab
3. Filter by "Fetch/XHR"
4. Refresh the page that should show strategies
5. Find request to `/api/v1/strategies` or `/api/v1/ml/strategies/for-model/...`
6. Click on request
7. Check "Response" tab
8. Should see array with preset strategies

---

## 📊 Database Verification

If API returns empty, verify database has the preset strategies:

```bash
cd /media/d88k/01D9C5CA3CB3C3E0/edo/nusatrade/backend
source venv/bin/activate
python scripts/verify_implementation.py
```

This will check:
1. Database has 4 default strategies
2. All are marked as `is_public=true`, `is_active=true`, `strategy_type='preset'`
3. All have `user_id IS NULL`

If strategies are missing, repopulate:
```bash
python scripts/populate_default_strategies.py
```

---

## 📞 Getting Help

If tests still fail after:
1. ✅ Render deployment succeeded
2. ✅ Hard refresh browser
3. ✅ Cleared cache
4. ✅ Database has 4 preset strategies

Then check:
- Backend logs on Render for errors
- Frontend console for errors
- Network tab for failed requests

Share the error logs for further debugging.

---

**Status**: Waiting for Render deployment to complete (~5-10 minutes)
