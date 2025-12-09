# 🚀 ForexAI Platform - Render.com Deployment Guide

Complete step-by-step guide for deploying ForexAI Platform to Render.com.

## 📋 Table of Contents

1. [Why Render?](#why-render)
2. [Prerequisites](#prerequisites)
3. [Database Setup](#database-setup)
4. [Backend Deployment](#backend-deployment)
5. [Frontend Deployment](#frontend-deployment)
6. [Redis Setup](#redis-setup)
7. [Environment Variables](#environment-variables)
8. [Custom Domain](#custom-domain)
9. [Monitoring](#monitoring)
10. [Troubleshooting](#troubleshooting)

---

## Why Render?

### ✅ Advantages

- **Free Tier**: 750 hours/month free for web services
- **Free PostgreSQL**: 90 days free, then $7/month
- **Auto-deploy**: GitHub integration with automatic deployments
- **Zero Config**: Detects Python/Node.js automatically
- **Fast Builds**: Faster than most competitors
- **Great DX**: Modern, intuitive dashboard
- **Free SSL**: Automatic HTTPS for custom domains
- **Better Pricing**: More affordable than Railway/Heroku

### 💰 Pricing Estimate

| Service | Plan | Cost |
|---------|------|------|
| Backend (Render) | Starter | $7/month |
| Database (Supabase) | Free | **$0** 🎉 |
| Frontend (Vercel) | Free | $0 |
| Redis (Upstash) | Free | $0 |
| **Total** | | **$7/month** |

Compare to Railway: ~$25-30/month for same setup.

**💡 Even better: Supabase free tier is permanent (500 MB), not just 90 days!**

---

## Prerequisites

### Required Accounts

1. **Render.com** - [Sign up](https://render.com) - For backend hosting
2. **Supabase** - [Sign up](https://supabase.com) - For database ⭐ **RECOMMENDED**
3. **GitHub** - Your code repository
4. **Upstash** - [Sign up](https://upstash.com) - For Redis (free tier)
5. **OpenAI** - API key for AI features

### Required Tools

```bash
# On your local machine
git --version
python --version  # 3.12+
node --version    # 20+
```

---

## Database Setup

### Option A: Supabase (⭐ RECOMMENDED)

**Why Supabase?**
- ✅ **Free forever** (500 MB, not just 90 days)
- ✅ **Auto backups** (Point-in-time recovery)
- ✅ **Better tooling** (SQL Editor, Table Editor)
- ✅ **Auth included** (if you need it later)
- ✅ **Realtime** (WebSocket support built-in)
- ✅ **Storage** (File uploads if needed)

#### Step 1: Create Supabase Project

1. Go to [Supabase Dashboard](https://supabase.com/dashboard)
2. Click **New Project**
3. Configure:
   - **Name**: `forexai`
   - **Database Password**: Generate strong password (save it!)
   - **Region**: Choose closest to your Render region
   - **Plan**: Free (500 MB, permanent)
4. Click **Create new project**
5. Wait ~2 minutes for provisioning

#### Step 2: Get Connection String

1. Go to **Project Settings** → **Database**
2. Scroll to **Connection string** → **URI**
3. Copy the connection string:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:5432/postgres
   ```
4. Replace `[YOUR-PASSWORD]` with your actual password
5. **Important**: Change `postgres` to `postgres.pooler` for connection pooling:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:6543/postgres
   ```
   (Note: port changed from 5432 to 6543 for pooler)

#### Step 3: Enable Connection Pooling (Recommended)

1. In Supabase Dashboard → **Database** → **Connection Pooling**
2. Enable **Transaction Mode** (best for FastAPI)
3. Use the pooler connection string (port 6543)

### Option B: Render PostgreSQL (Alternative)

Only use this if you specifically need Render-hosted database.

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **New** → **PostgreSQL**
3. Configure:
   - **Name**: `forexai-db`
   - **Database**: `forexai`
   - **Region**: Same as backend
   - **Plan**: Free (90 days) or Starter ($7/month)
4. Copy connection string

**Note**: Render free tier only lasts 90 days, then $7/month.

---

## Backend Deployment

### Step 1: Prepare Repository

Ensure your `backend` folder has:

```
backend/
├── app/
├── requirements.txt
├── alembic.ini
├── migrations/
└── .env.example
```

### Step 2: Create Web Service

1. In Render Dashboard, click **New** → **Web Service**
2. Connect your GitHub repository
3. Configure:
   - **Name**: `forexai-backend`
   - **Region**: Same as database
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**:
     ```bash
     pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT
     ```
   - **Plan**: Free (750 hrs/month) or Starter ($7/month)

### Step 3: Add Environment Variables

Click **Environment** tab and add:

```bash
# Application
ENVIRONMENT=production
LOG_LEVEL=INFO

# Database (Supabase - from Database Setup section)
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:6543/postgres

# Security - GENERATE NEW SECRETS!
JWT_SECRET=<generate-with-command-below>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS - Update with your frontend URL
BACKEND_CORS_ORIGINS=https://forexai.onrender.com,https://yourdomain.com

# AI Provider

**Generate JWT Secret:**
```bash
openssl rand -hex 32
```

# AI/LLM Provider (OpenAI-Compatible)
LLM_API_KEY=your-api-key-here
LLM_MODEL=gpt-4-turbo-preview

# Optional: Custom base URL for alternative providers
# Leave empty to use OpenAI (default)
# LLM_BASE_URL=

# Examples for different providers:
# OpenRouter: LLM_BASE_URL=https://openrouter.ai/api/v1
# Together AI: LLM_BASE_URL=https://api.together.xyz/v1
# Groq: LLM_BASE_URL=https://api.groq.com/openai/v1
# Local: LLM_BASE_URL=http://localhost:11434/v1

# Legacy (still supported)
# OPENAI_API_KEY=sk-your-key
# OPENAI_MODEL=gpt-4-turbo-preview

# Anthropic (fallback only)
ANTHROPIC_API_KEY=sk-ant-your-key
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# Redis (we'll add this later)
REDIS_URL=redis://default:***@***.upstash.io:6379

# Optional: Celery
CELERY_BROKER_URL=redis://default:***@***.upstash.io:6379/1
CELERY_RESULT_BACKEND=redis://default:***@***.upstash.io:6379/2
```

**Generate JWT Secret:**
```bash
openssl rand -hex 32
```

### Step 4: Deploy

1. Click **Create Web Service**
2. Wait for build to complete (~3-5 minutes)
3. Your backend will be available at: `https://forexai-backend.onrender.com`

### Step 5: Run Database Migrations

After first deployment:

1. Go to **Shell** tab in Render dashboard
2. Run:
   ```bash
   alembic upgrade head
   ```

Or use Render's one-off jobs:
```bash
# In Render dashboard: Shell
python -m alembic upgrade head
```

### Step 6: Test Backend

Visit: `https://forexai-backend.onrender.com/api/v1/health`

Should return:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

---

## Frontend Deployment

### Option A: Vercel (Recommended for Next.js)

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
cd frontend
vercel --prod
```

Set environment variables in Vercel:
```bash
NEXT_PUBLIC_API_URL=https://forexai-backend.onrender.com
NEXT_PUBLIC_WS_URL=wss://forexai-backend.onrender.com
```

### Option B: Render Static Site

1. In Render Dashboard, click **New** → **Static Site**
2. Connect GitHub repository
3. Configure:
   - **Name**: `forexai-frontend`
   - **Root Directory**: `frontend`
   - **Build Command**:
     ```bash
     npm install && npm run build
     ```
   - **Publish Directory**: `.next`
   - **Plan**: Free

4. Add environment variables:
   ```bash
   NEXT_PUBLIC_API_URL=https://forexai-backend.onrender.com
   NEXT_PUBLIC_WS_URL=wss://forexai-backend.onrender.com
   ```

5. Deploy!

**Note**: For Next.js with SSR, use Vercel instead. Render Static Sites are for static exports only.

---

## Redis Setup

### Using Upstash (Free Tier)

1. Go to [Upstash Console](https://console.upstash.com)
2. Create new Redis database:
   - **Name**: `forexai-redis`
   - **Region**: Same as Render services
   - **Type**: Regional (free)
3. Copy connection string:
   ```
   redis://default:***@***.upstash.io:6379
   ```
4. Add to Render environment variables:
   - `REDIS_URL`
   - `CELERY_BROKER_URL` (append `/1`)
   - `CELERY_RESULT_BACKEND` (append `/2`)

---

## Environment Variables

### Backend (.env)

Complete list of environment variables for Render:

```bash
# ============================================
# APPLICATION
# ============================================
APP_NAME=Forex AI Backend
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# ============================================
# DATABASE (Supabase)
# ============================================
# Use Supabase pooler connection string (port 6543)
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.xxx.supabase.co:6543/postgres
REDIS_URL=redis://default:***@***.upstash.io:6379

# ============================================
# SECURITY
# ============================================
JWT_SECRET=<your-generated-secret-32-chars>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# ============================================
# CORS
# ============================================
BACKEND_CORS_ORIGINS=https://forexai.vercel.app,https://yourdomain.com

# ============================================
# CELERY
# ============================================
CELERY_BROKER_URL=redis://default:***@***.upstash.io:6379/1
CELERY_RESULT_BACKEND=redis://default:***@***.upstash.io:6379/2

# ============================================
# AI/LLM (OpenAI-Compatible)
# ============================================
# Unified configuration (recommended)
LLM_API_KEY=your-api-key
LLM_MODEL=gpt-4-turbo-preview
# LLM_BASE_URL=  # Optional: for alternative providers

# Examples:
# OpenRouter: LLM_BASE_URL=https://openrouter.ai/api/v1
# Together AI: LLM_BASE_URL=https://api.together.xyz/v1
# Groq: LLM_BASE_URL=https://api.groq.com/openai/v1

# Legacy (still supported)
# OPENAI_API_KEY=sk-***
# OPENAI_MODEL=gpt-4-turbo-preview

# Anthropic (fallback only)
ANTHROPIC_API_KEY=sk-ant-***
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# ============================================
# STORAGE (Optional)
# ============================================
R2_ACCOUNT_ID=your-cloudflare-account-id
R2_ACCESS_KEY_ID=***
R2_SECRET_ACCESS_KEY=***
R2_BUCKET_NAME=forex-ai-storage

# ============================================
# RATE LIMITING
# ============================================
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60

# ============================================
# TRADING
# ============================================
MAX_LOT_SIZE=10.0
MAX_POSITIONS_PER_USER=20
DEFAULT_SLIPPAGE_PIPS=2.0

# ============================================
# WEBSOCKET
# ============================================
WS_HEARTBEAT_INTERVAL=30
WS_CONNECTION_TIMEOUT=60
```

### Frontend (.env.production)

```bash
NEXT_PUBLIC_API_URL=https://forexai-backend.onrender.com
NEXT_PUBLIC_WS_URL=wss://forexai-backend.onrender.com
NEXT_PUBLIC_APP_NAME=ForexAI
NEXT_PUBLIC_APP_VERSION=1.0.0
NEXT_PUBLIC_ENABLE_AI_SUPERVISOR=true
NEXT_PUBLIC_ENABLE_BACKTESTING=true
NEXT_PUBLIC_ENABLE_LIVE_TRADING=true
```

---

## Custom Domain

### Backend Domain (api.yourdomain.com)

1. In Render Dashboard → Backend Service → Settings
2. Click **Add Custom Domain**
3. Enter: `api.yourdomain.com`
4. Add CNAME record in your DNS:
   ```
   CNAME api.yourdomain.com → forexai-backend.onrender.com
   ```
5. Wait for SSL certificate (automatic, ~5 minutes)

### Frontend Domain (app.yourdomain.com)

If using Vercel:
1. Vercel Dashboard → Settings → Domains
2. Add `app.yourdomain.com`
3. Follow Vercel's DNS instructions

If using Render Static Site:
1. Same process as backend
2. Add CNAME for your domain

---

## Monitoring

### 1. Render Built-in Monitoring

- **Metrics**: CPU, Memory, Request rate
- **Logs**: Real-time logs in dashboard
- **Alerts**: Email notifications for crashes

### 2. Health Checks

Render automatically monitors:
```
https://forexai-backend.onrender.com/api/v1/health
```

Configure in Render:
- **Health Check Path**: `/api/v1/health`
- **Health Check Interval**: 30 seconds

### 3. External Monitoring

**UptimeRobot** (Free):
1. Add monitor: `https://api.yourdomain.com/api/v1/health`
2. Interval: 5 minutes
3. Alert: Email on downtime

### 4. Error Tracking

**Sentry** (Free tier):
1. Create project at [sentry.io](https://sentry.io)
2. Add to environment variables:
   ```bash
   SENTRY_DSN=https://***@***.ingest.sentry.io/***
   ```

---

## Backup Strategy

### Database Backups

**Automatic** (Render Starter plan):
- Daily backups
- 7-day retention
- One-click restore

**Manual Backup**:
```bash
# In Render Shell
pg_dump $DATABASE_URL > backup.sql

# Or download via Render dashboard
```

### Restore from Backup

```bash
# In Render Shell
psql $DATABASE_URL < backup.sql
```

---

## Scaling

### Free Tier Limitations

- **Web Service**: 750 hours/month (sleeps after 15 min inactivity)
- **Database**: 256 MB RAM, 1 GB storage
- **Build Time**: Slower builds

### Upgrade to Starter ($7/month)

Benefits:
- ✅ No sleep (always on)
- ✅ Faster builds
- ✅ More resources
- ✅ Daily backups
- ✅ Better support

### Horizontal Scaling

For high traffic:
1. Upgrade to **Pro plan** ($25/month)
2. Enable **Auto-scaling**
3. Add **Read replicas** for database
4. Use **CDN** for static assets

---

## Troubleshooting

### 1. Build Failed

**Check logs**:
1. Render Dashboard → Service → Logs
2. Look for Python/pip errors

**Common fixes**:
```bash
# Update requirements.txt
pip freeze > requirements.txt

# Specify Python version in render.yaml
python_version: "3.12"
```

### 2. Database Connection Error

**Check**:
- DATABASE_URL is correct
- Database is running (Render dashboard)
- Migrations ran successfully

**Fix**:
```bash
# In Render Shell
alembic upgrade head
```

### 3. Service Sleeping (Free Tier)

Free tier sleeps after 15 minutes of inactivity.

**Solutions**:
- Upgrade to Starter ($7/month)
- Use external ping service (UptimeRobot)
- Accept 30-second cold start

### 4. CORS Errors

**Check**:
```bash
# Environment variable must match exactly
BACKEND_CORS_ORIGINS=https://yourdomain.com
# No trailing slash!
```

### 5. WebSocket Not Working

**Ensure**:
- Using `wss://` (not `ws://`)
- CORS includes WebSocket origin
- Render plan supports WebSockets (Starter+)

---

## Cost Optimization

### Free Tier Setup ($0/month) 🎉

- Backend: Render Free tier (sleeps after 15 min)
- Database: **Supabase Free tier (500 MB, permanent)** ✅
- Frontend: Vercel free tier
- Redis: Upstash free tier

**Total**: **$0/month forever!** (with sleep on backend)

### Production Setup ($7/month) ⭐ RECOMMENDED

- Backend: Render Starter ($7/month) - Always on
- Database: **Supabase Free tier (500 MB, permanent)** ✅
- Frontend: Vercel free tier
- Redis: Upstash free tier

**Total**: **$7/month** (vs $25-30/month on Railway!)

### Growing Business ($32/month)

- Backend: Render Starter ($7/month)
- Database: **Supabase Pro ($25/month)** - 8 GB, better performance
- Frontend: Vercel free tier
- Redis: Upstash free tier

**Total**: $32/month

### High-Traffic Setup ($52/month)

- Backend: Render Pro ($25/month)
- Database: Supabase Pro ($25/month)
- Frontend: Vercel Pro ($20/month)
- Redis: Upstash paid ($5/month)

**Total**: $75/month

---

## Deployment Checklist

### Pre-Deployment

- [ ] Code pushed to GitHub
- [ ] Environment variables prepared
- [ ] Database migrations tested locally
- [ ] API endpoints tested
- [ ] Frontend builds successfully
- [ ] CORS configured correctly

### Deployment Steps

- [ ] Create PostgreSQL database on Render
- [ ] Deploy backend web service
- [ ] Add environment variables
- [ ] Run database migrations
- [ ] Test backend health endpoint
- [ ] Setup Redis on Upstash
- [ ] Deploy frontend to Vercel
- [ ] Test full application flow
- [ ] Configure custom domains
- [ ] Setup monitoring (UptimeRobot, Sentry)
- [ ] Configure backups
- [ ] Test WebSocket connections
- [ ] Load testing
- [ ] Security audit

### Post-Deployment

- [ ] Monitor logs for errors
- [ ] Check performance metrics
- [ ] Test all features in production
- [ ] Setup alerts
- [ ] Document any issues
- [ ] Train team on deployment process

---

## Render.yaml (Optional)

For infrastructure as code, create `render.yaml`:

```yaml
services:
  # Backend
  - type: web
    name: forexai-backend
    env: python
    region: oregon
    plan: starter
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /api/v1/health
    envVars:
      - key: ENVIRONMENT
        value: production
      - key: DATABASE_URL
        fromDatabase:
          name: forexai-db
          property: connectionString
      - key: JWT_SECRET
        generateValue: true
      - key: REDIS_URL
        sync: false

databases:
  - name: forexai-db
    databaseName: forexai
    user: forexai
    plan: starter
```

---

## Comparison: Render + Supabase vs Railway vs Heroku

| Feature | Render + Supabase | Railway | Heroku |
|---------|-------------------|---------|--------|
| Free Tier | 750 hrs/month + DB free forever | $5 credit | 550 hrs/month |
| Database Free | ✅ **500 MB permanent** | ❌ $5/month | ❌ $9/month |
| Starter Price | $7/month | ~$10/month | $7/month |
| Database Starter | **$0 (free tier)** | $5/month | $9/month |
| Build Speed | ⚡ Fast | Medium | Slow |
| DX | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Documentation | Excellent | Good | Excellent |
| Database Tooling | ⭐⭐⭐⭐⭐ (Supabase) | ⭐⭐⭐ | ⭐⭐ |
| **Total Cost** | **$7/month** | **$15/month** | **$16/month** |

**Winner: Render + Supabase** 🏆 (50%+ cheaper!)

---

## Next Steps

1. **Deploy to Render** using this guide
2. **Test thoroughly** in production
3. **Monitor performance** for first week
4. **Optimize** based on metrics
5. **Scale** as needed

---

## Support

- **Render Docs**: https://render.com/docs
- **Community**: https://community.render.com
- **Status**: https://status.render.com

---

**Happy Deploying!** 🚀

*Last Updated: December 2024*
*Version: 1.0.0*
