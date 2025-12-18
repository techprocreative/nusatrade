# Quick Fix: Run Migration on Render

## Langkah 1: Buka Render Dashboard

1. Login ke https://dashboard.render.com
2. Pilih service backend (nusatrade)

## Langkah 2: Buka Shell

1. Klik tab **"Shell"** di menu atas
2. Tunggu shell terminal terbuka

## Langkah 3: Pull Latest Code

```bash
git pull origin main
```

## Langkah 4: Run Migration

```bash
python run_migrations.py
```

**Output yang diharapkan:**
```
============================================================
Running database migrations...
============================================================
Database: [your-render-db-url]

Checking current database version...
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
Current revision(s) for postgresql://...: 0011_add_default_ml_models

Upgrading to latest version...
INFO  [alembic.runtime.migration] Running upgrade 0011 -> 0012, add pretrained fields to ml_models

============================================================
✅ Migrations completed successfully!
============================================================

Current database version:
0012_add_pretrained_fields (head)
```

## Langkah 5: Restart Service (Optional)

Jika perlu, restart service:
1. Klik tab **"Manual Deploy"**
2. Klik **"Deploy latest commit"**

Atau biarkan auto-deploy jalan karena sudah ada commit baru.

## Langkah 6: Test

Test endpoint import default model:

```bash
curl -X POST https://nusatrade.onrender.com/api/v1/ml/models/import-default/XAUUSD \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

Seharusnya return 200 OK (bukan 500 lagi).

---

## Troubleshooting

### Jika migration script error:

**Run SQL manual:**

1. Di Render Dashboard, buka **PostgreSQL database**
2. Klik **"Query"** atau **"Connect"**
3. Copy SQL dari `backend/migrations/versions/0012_manual_apply.sql`
4. Paste dan execute

### Jika git pull error:

```bash
# Stash any local changes first
git stash
git pull origin main
```

### Verify migration berhasil:

```bash
# Connect to PostgreSQL and run:
SELECT column_name FROM information_schema.columns
WHERE table_name = 'ml_models' AND column_name = 'is_pretrained';
```

Expected: menampilkan row `is_pretrained`

---

**Total waktu:** ~2 menit
**Downtime:** 0 (zero downtime, migration saat traffic)
