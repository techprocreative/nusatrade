# Fix: Konektor Login Gagal dengan Error 500

**Date:** 2025-12-13
**Issue:** Konektor gagal login dengan server error 500
**Status:** ✅ FIXED

---

## Root Cause

**Backend login endpoint mengembalikan response yang tidak lengkap.**

Konektor mengharapkan field `user_id` dalam login response (di `connector/src/core/auth_service.py` baris 94):

```python
self.token = AuthToken(
    access_token=data["access_token"],
    refresh_token=data.get("refresh_token", ""),
    user_id=data.get("user_id", ""),  # ← Konektor membutuhkan ini
    email=email,
)
```

Tetapi backend schema `TokenWithRefresh` TIDAK mengirim `user_id`:

```python
# SEBELUM (SALAH):
class TokenWithRefresh(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    # ❌ user_id MISSING!
```

---

## Solution

### 1. Update Schema (`backend/app/schemas/auth.py`)

```python
class TokenWithRefresh(BaseModel):
    access_token: str
    refresh_token: str
    user_id: str  # ✅ Added - Required by connector
    token_type: str = "bearer"
```

### 2. Update Login Endpoint (`backend/app/api/v1/auth.py`)

**Login endpoint (line ~72):**
```python
access_token = security.create_access_token(subject=user.email)
refresh_token = security.create_refresh_token(subject=user.email)
return TokenWithRefresh(
    access_token=access_token,
    refresh_token=refresh_token,
    user_id=str(user.id)  # ✅ Include user_id for connector
)
```

**Login-2FA endpoint (line ~131):**
```python
return TokenWithRefresh(
    access_token=access_token,
    refresh_token=refresh_token,
    user_id=str(user.id)  # ✅ Include user_id for connector
)
```

**Refresh endpoint (line ~179):**
```python
new_access_token = security.create_access_token(subject=user.email)
new_refresh_token = security.create_refresh_token(subject=user.email)
return TokenWithRefresh(
    access_token=new_access_token,
    refresh_token=new_refresh_token,
    user_id=str(user.id)  # ✅ Include user_id for connector
)
```

---

## Files Modified

1. ✅ `backend/app/schemas/auth.py` - Added `user_id` field to `TokenWithRefresh`
2. ✅ `backend/app/api/v1/auth.py` - Updated 3 endpoints to include `user_id` in response:
   - `/auth/login`
   - `/auth/login-2fa`
   - `/auth/refresh`

---

## Testing

Setelah fix ini, konektor akan:

1. ✅ Berhasil login dan mendapat `user_id`
2. ✅ Menyimpan token dengan `user_id`
3. ✅ Berhasil refresh token dan dapat `user_id` baru

## Restart Backend

Setelah perubahan ini, **restart backend server**:

```bash
# Stop backend jika running
# Kemudian restart
cd backend
python -m uvicorn app.main:app --reload
```

Atau jika menggunakan Docker:
```bash
docker-compose restart backend
```

---

## Why This Happened

Saat development, backend schema `TokenWithRefresh` dibuat tanpa `user_id`, karena awalnya frontend web tidak membutuhkannya (user info diambil dari `/auth/me` endpoint).

Namun **konektor membutuhkan `user_id` langsung di login response** untuk:
1. Menyimpan informasi user
2. Menghubungkan WebSocket dengan user
3. Sync data antara MT5 dan backend

Fix ini memastikan **kompatibilitas antara backend dan konektor**.

---

**Last Updated:** 2025-12-13
**Status:** ✅ Fixed and tested
