# Database Migration Fix - is_pretrained Column Missing

## Problem
Backend error when importing default ML models:
```
(psycopg2.errors.UndefinedColumn) column ml_models.is_pretrained does not exist
```

**Root Cause:** Migration `0012_add_pretrained_fields` exists in code but hasn't been applied to production database on Render.

## Solution

### Option 1: Run Migration Script (Recommended)

Run the automated migration script on Render:

```bash
# SSH into Render backend service or run via Render shell
cd /path/to/backend
python run_migrations.py
```

**What it does:**
- Checks current database version
- Applies all pending migrations (including 0012_add_pretrained_fields)
- Verifies successful completion
- Shows final database version

### Option 2: Manual SQL (If needed)

If automatic migration fails, run SQL manually in Render PostgreSQL console:

```bash
# Connect to Render PostgreSQL
# Then run the SQL file:
\i migrations/versions/0012_manual_apply.sql
```

Or copy-paste from `backend/migrations/versions/0012_manual_apply.sql`

**What the SQL does:**
1. Adds `is_pretrained` column (BOOLEAN, default false)
2. Adds `default_model_id` column (UUID, nullable)
3. Adds foreign key constraint to `default_ml_models`
4. Records migration in `alembic_version` table
5. Verifies columns were added

### Option 3: Via Render Dashboard (Easiest)

1. Go to Render Dashboard → Your Backend Service
2. Click "Shell" tab
3. Run:
   ```bash
   python run_migrations.py
   ```

## Files Added

1. **`backend/run_migrations.py`**
   - Automated migration runner
   - Uses alembic to apply all pending migrations
   - Safe to run multiple times (idempotent)
   - Checks DATABASE_URL from environment

2. **`backend/migrations/versions/0012_manual_apply.sql`**
   - Manual SQL fallback
   - Applies same changes as Python migration
   - Includes verification queries
   - Records migration in alembic_version

## Verification

After running migration, verify it worked:

```bash
# Check column exists
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name = 'ml_models'
  AND column_name = 'is_pretrained';
```

Expected output:
```
 column_name   | data_type | column_default
---------------+-----------+----------------
 is_pretrained | boolean   | false
```

Then test the endpoint:
```bash
curl -X POST https://nusatrade.onrender.com/api/v1/ml/models/import-default/XAUUSD \
  -H "Authorization: Bearer YOUR_TOKEN"
```

Should return 200 OK instead of 500.

## Why This Happened

The migration file was created locally but never applied to production because:
- No automatic migration on deployment
- No startup hook to run migrations
- Manual deployment to Render without migration step

## Prevention

Add to deployment process:
1. Add migration step to Render startup command
2. Or add pre-deploy hook in render.yaml
3. Or include in Dockerfile CMD

Example startup command for Render:
```bash
python run_migrations.py && uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Rollback (if needed)

If migration causes issues:

```bash
# Via Python
alembic downgrade 0011_add_default_ml_models

# Or via SQL
ALTER TABLE ml_models DROP COLUMN IF EXISTS is_pretrained;
ALTER TABLE ml_models DROP COLUMN IF EXISTS default_model_id;
DELETE FROM alembic_version WHERE version_num = '0012_add_pretrained_fields';
```

---

**Status:** Ready to deploy
**Date:** 2025-12-15
**Migration:** 0012_add_pretrained_fields
