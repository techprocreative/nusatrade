# ⚠️ VERCEL ENVIRONMENT VARIABLE - NOT SET

**Issue**: Frontend calling wrong API URL
**Status**: NEEDS CONFIGURATION

---

## 🐛 PROBLEM

Browser console shows:
```
GET https://nusatrade-beta.vercel.app/api/v1/ml/auto-trading/status
[HTTP/2 404]
```

This is WRONG! Frontend should call:
```
GET https://nusatrade.onrender.com/api/v1/ml/auto-trading/status
```

---

## 🔍 ROOT CAUSE

**Vercel environment variable `NEXT_PUBLIC_API_URL` is NOT SET**

When `NEXT_PUBLIC_API_URL` is not set, code falls back to:
```javascript
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
```

In browser, `localhost:8000` doesn't work, so browser tries relative URL:
- Tries: `/api/v1/...`
- Becomes: `https://nusatrade-beta.vercel.app/api/v1/...`
- Result: **404 Not Found**

---

## ✅ SOLUTION

### Step 1: Set Vercel Environment Variable

1. Go to: https://vercel.com (login)
2. Select project: **nusatrade-beta** (or your project name)
3. Go to: **Settings** → **Environment Variables**
4. Click: **Add New**
5. Enter:
   - **Name**: `NEXT_PUBLIC_API_URL`
   - **Value**: `https://nusatrade.onrender.com`
   - **Environment**: Check all:
     - ☑️ Production
     - ☑️ Preview
     - ☑️ Development
6. Click: **Save**

### Step 2: Redeploy Frontend

Option A: Automatic
- Vercel will automatically redeploy after saving environment variable

Option B: Manual
- Go to: **Deployments** tab
- Click: **Redeploy** on latest deployment

---

## 🧪 VERIFICATION

### After Redeployment:

1. **Open browser**:
   - Go to: https://nusatrade-beta.vercel.app

2. **Open DevTools (F12)**:
   - Go to: **Console** tab
   - Clear console

3. **Navigate to /bots page**:
   - URL: https://nusatrade-beta.vercel.app/bots

4. **Check Network tab**:
   - You should see requests to: `https://nusatrade.onrender.com/api/v1/...`
   - NOT: `https://nusatrade-beta.vercel.app/api/v1/...`

5. **Check for errors**:
   - Should see: ✅ 200 OK responses
   - Not: ❌ 404 Not Found

---

## 📋 CHECKLIST

- [ ] Vercel environment variable `NEXT_PUBLIC_API_URL` set to `https://nusatrade.onrender.com`
- [ ] Variable applied to all environments (Production, Preview, Development)
- [ ] Frontend redeployed
- [ ] Browser console shows requests to `nusatrade.onrender.com` (not `nusatrade-beta.vercel.app`)
- [ ] API calls returning 200 (not 404)

---

## 🎯 EXPECTED RESULT

### Before Fix:
```
❌ GET https://nusatrade-beta.vercel.app/api/v1/ml/auto-trading/status
   → 404 Not Found
```

### After Fix:
```
✅ GET https://nusatrade.onrender.com/api/v1/ml/auto-trading/status
   → 200 OK
```

---

## 📝 ADDITIONAL INFO

### Files Using NEXT_PUBLIC_API_URL:

1. `lib/api-client.ts` - Axios client base URL
2. `lib/websocket.ts` - WebSocket connection
3. `lib/api/ml-models.ts` - ML models API calls
4. `hooks/api/useStrategies.ts` - Strategies hook
5. All API fetch calls throughout the app

### Why NEXT_PUBLIC_ prefix?

Next.js requires `NEXT_PUBLIC_` prefix for environment variables that are:
- Exposed to the browser
- Used in client-side code

Variables without this prefix are only available on the server side.

---

## 🚀 SUMMARY

**Problem**: Environment variable not set in Vercel
**Solution**: Add `NEXT_PUBLIC_API_URL=https://nusatrade.onrender.com` in Vercel settings
**Impact**: All API calls will now go to correct backend URL
**Time**: ~2-3 minutes to set + redeploy

After this fix:
- ✅ API calls will work
- ✅ Modal will fetch strategies
- ✅ Auto-trading status will load
- ✅ All features will function correctly
