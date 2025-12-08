# 🚀 Forex AI Platform - Production Deployment Guide

Complete guide for deploying Forex AI Platform to production.

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Infrastructure Setup](#infrastructure-setup)
3. [Database Setup](#database-setup)
4. [Backend Deployment](#backend-deployment)
5. [Frontend Deployment](#frontend-deployment)
6. [Connector Distribution](#connector-distribution)
7. [Monitoring & Maintenance](#monitoring--maintenance)
8. [Security Checklist](#security-checklist)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Accounts & Services

1. **Cloud Platform** (choose one):
   - Railway.app (recommended for simplicity)
   - AWS/DigitalOcean/Heroku
   - Self-hosted VPS

2. **Database**:
   - PostgreSQL 14+ (Supabase, Railway, AWS RDS)

3. **Redis**:
   - Upstash Redis (recommended for serverless)
   - Redis Cloud
   - Self-hosted Redis

4. **Email Service** (choose one):
   - SendGrid (recommended)
   - AWS SES
   - Mailgun

5. **Monitoring**:
   - Sentry.io account

6. **Domain & DNS**:
   - Custom domain (e.g., forexai.com)
   - DNS provider (Cloudflare recommended)

### Required Tools

```bash
# On your local machine
- Git
- Python 3.12+
- Node.js 20+
- Docker (optional, for local testing)
```

---

## Infrastructure Setup

### 1. Database (PostgreSQL)

#### Option A: Supabase (Recommended)

1. Go to [supabase.com](https://supabase.com) and create project
2. Navigate to Project Settings → Database
3. Copy connection string:
   ```
   postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres
   ```
4. Save as `DATABASE_URL` environment variable

#### Option B: Railway

1. Create new PostgreSQL database in Railway
2. Copy `DATABASE_URL` from service variables

### 2. Redis

#### Using Upstash (Recommended)

1. Go to [upstash.com](https://upstash.com)
2. Create new Redis database
3. Copy connection string:
   ```
   redis://default:[PASSWORD]@[HOST].upstash.io:6379
   ```
4. Save as `REDIS_URL` environment variable

### 3. Email Service

#### Using SendGrid

1. Sign up at [sendgrid.com](https://sendgrid.com)
2. Create API key with "Mail Send" permissions
3. Verify sender email address
4. Save API key as `SENDGRID_API_KEY`
5. Set `EMAIL_PROVIDER=sendgrid`

### 4. Monitoring

#### Setup Sentry

1. Create account at [sentry.io](https://sentry.io)
2. Create new project (select FastAPI)
3. Copy DSN
4. Save as `SENTRY_DSN` environment variable

### 5. AI/LLM APIs

#### OpenAI

1. Get API key from [platform.openai.com](https://platform.openai.com)
2. Save as `OPENAI_API_KEY`

#### Anthropic (Optional)

1. Get API key from [console.anthropic.com](https://console.anthropic.com)
2. Save as `ANTHROPIC_API_KEY`

---

## Backend Deployment

### Step 1: Prepare Backend

```bash
cd backend

# Create production environment file
cp .env.production.example .env.production

# Edit with your actual credentials
nano .env.production
```

**Critical environment variables:**

```env
# Security
JWT_SECRET=<generate-with-openssl-rand-hex-32>
WS_AUTH_SECRET=<generate-strong-secret>

# Database
DATABASE_URL=postgresql://...

# Redis
REDIS_URL=redis://...

# Email
EMAIL_PROVIDER=sendgrid
SENDGRID_API_KEY=SG.xxx
EMAIL_FROM=noreply@yourdomain.com

# AI
OPENAI_API_KEY=sk-xxx

# Monitoring
SENTRY_DSN=https://xxx@sentry.io/xxx

# CORS
CORS_ORIGINS=https://app.yourdomain.com,https://yourdomain.com
FRONTEND_URL=https://app.yourdomain.com
```

### Step 2: Run Database Migrations

```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python -m alembic upgrade head
```

### Step 3: Deploy to Railway

#### Method A: Using Railway CLI

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Link project
railway link

# Deploy
railway up
```

#### Method B: GitHub Integration

1. Push code to GitHub
2. In Railway dashboard:
   - New → Deploy from GitHub repo
   - Select your repository
   - Select `backend` folder as root directory
3. Configure environment variables in Railway dashboard
4. Deploy automatically triggers

### Step 4: Configure Build Settings

In Railway, set:

**Build Command:**
```bash
pip install -r requirements.txt && alembic upgrade head
```

**Start Command:**
```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Health Check Path:**
```
/api/v1/health
```

### Step 5: Setup Custom Domain

1. In Railway → Settings → Domains
2. Add custom domain: `api.yourdomain.com`
3. Update DNS records (CNAME or A record)
4. Wait for SSL certificate provisioning (automatic)

---

## Frontend Deployment

### Step 1: Prepare Frontend

```bash
cd frontend

# Create production environment file
cp .env.local.example .env.production

# Edit with actual API URL
echo "NEXT_PUBLIC_API_URL=https://api.yourdomain.com" > .env.production
echo "NEXT_PUBLIC_WS_URL=wss://api.yourdomain.com" >> .env.production
```

### Step 2: Build & Deploy to Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy to production
vercel --prod
```

**Or via Vercel Dashboard:**

1. Import GitHub repository
2. Select `frontend` folder as root directory
3. Set environment variables:
   - `NEXT_PUBLIC_API_URL=https://api.yourdomain.com`
   - `NEXT_PUBLIC_WS_URL=wss://api.yourdomain.com`
4. Deploy

### Step 3: Configure Custom Domain

1. In Vercel → Settings → Domains
2. Add `app.yourdomain.com`
3. Update DNS (Vercel provides instructions)

---

## Connector Distribution

### Step 1: Build Windows Executable

```bash
cd connector

# Install dependencies
pip install -r requirements.txt

# Build executable
python build.py
```

This creates `dist/ForexAI-Connector.exe`

### Step 2: Test Executable

```bash
# Run executable
./dist/ForexAI-Connector.exe

# Test connection to production backend
```

### Step 3: Create Installer (Optional)

Use Inno Setup or NSIS to create installer:

```bash
# Install Inno Setup
# Create installer script

iscc connector-installer.iss
```

### Step 4: Distribute

**Option A: Direct Download**
- Host on your website
- Create download page with instructions

**Option B: GitHub Releases**
```bash
# Create release
gh release create v1.0.0 ./dist/ForexAI-Connector.exe
```

### Step 5: Auto-Update Setup (Optional)

Implement auto-update using:
- GitHub Releases API
- Check for updates on startup
- Download and install new version

---

## Monitoring & Maintenance

### 1. Setup Health Checks

**UptimeRobot / Pingdom:**
```
Monitor: https://api.yourdomain.com/api/v1/health
Interval: 5 minutes
Alert: Email/SMS on downtime
```

### 2. Setup Logging

**CloudWatch / Papertrail:**
- Configure log shipping from Railway
- Set up log retention (30-90 days)
- Create alerts for errors

### 3. Database Backups

**Automated Backups:**
```sql
-- Daily backups at 2 AM UTC
-- Retention: 30 days
-- Test restore monthly
```

For Supabase:
- Backups automatic on paid plans
- Manual backups via CLI

For Railway:
```bash
# Manual backup
railway run pg_dump -Fc > backup.dump

# Restore
railway run pg_restore -d $DATABASE_URL backup.dump
```

### 4. Performance Monitoring

**Sentry Performance:**
- Transaction tracking enabled
- Monitor slow endpoints (>1s)
- Database query optimization

**Railway Metrics:**
- CPU usage
- Memory usage
- Request rate
- Response times

### 5. Error Alerts

**Sentry Alerts:**
- Email on new errors
- Slack integration for critical issues
- Weekly digest of all errors

---

## Security Checklist

### Pre-Launch Security

- [ ] JWT secret is strong (32+ characters)
- [ ] All secrets are in environment variables (not code)
- [ ] CORS configured for production domains only
- [ ] Rate limiting enabled
- [ ] SQL injection prevention (using ORM)
- [ ] Input validation on all endpoints
- [ ] HTTPS enforced (no HTTP)
- [ ] Security headers configured
- [ ] Database backups enabled
- [ ] 2FA enabled for admin accounts
- [ ] Sentry error tracking active
- [ ] Password reset token expiration (1 hour)
- [ ] Session timeout configured
- [ ] API docs disabled in production
- [ ] Debug mode disabled

### Post-Launch Security

- [ ] Regular dependency updates
- [ ] Security audit quarterly
- [ ] Penetration testing
- [ ] Monitor error logs daily
- [ ] Review access logs weekly
- [ ] Rotate secrets every 90 days
- [ ] Database query optimization
- [ ] Load testing completed
- [ ] Incident response plan documented
- [ ] GDPR compliance (if EU users)

---

## Database Migrations

### Running Migrations in Production

```bash
# Check current version
railway run alembic current

# Run migrations
railway run alembic upgrade head

# Rollback (if needed)
railway run alembic downgrade -1
```

### Creating New Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Review migration file
# Edit if needed

# Test locally first
alembic upgrade head

# Deploy to production
git push
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

```bash
# Check database URL
echo $DATABASE_URL

# Test connection
psql $DATABASE_URL

# Check firewall rules
# Ensure Railway service can access database
```

#### 2. Redis Connection Failed

```bash
# Test Redis connection
redis-cli -u $REDIS_URL ping

# Check Upstash dashboard for connection limits
```

#### 3. Email Not Sending

```bash
# Check SendGrid API key
# Verify sender email is verified
# Check SendGrid activity logs
# Review Sentry for email errors
```

#### 4. CORS Errors

```bash
# Verify CORS_ORIGINS environment variable
# Must match frontend domain exactly
# Include protocol (https://)
# No trailing slash
```

#### 5. WebSocket Connection Failed

```bash
# Check WS_AUTH_SECRET matches connector
# Verify WSS protocol (not WS)
# Check firewall allows WebSocket
```

#### 6. High Memory Usage

```bash
# Check database connection pool size
# Review Sentry for memory leaks
# Scale up Railway service
```

### Getting Help

- **Documentation**: https://docs.forexai.com
- **Discord**: https://discord.gg/forexai
- **Email**: support@forexai.com
- **GitHub Issues**: https://github.com/yourusername/forex-ai/issues

---

## Performance Optimization

### Backend

```python
# Enable database query caching
# Use Redis for session storage
# Optimize database indexes
# Enable Gzip compression
# CDN for static assets
```

### Frontend

```typescript
# Enable Next.js caching
# Optimize images
# Code splitting
# Lazy loading
# Service worker for offline
```

### Database

```sql
-- Add indexes on frequently queried columns
CREATE INDEX idx_trades_user_symbol ON trades(user_id, symbol);
CREATE INDEX idx_trades_open_time ON trades(open_time);

-- Vacuum and analyze
VACUUM ANALYZE;
```

---

## Scaling Strategy

### Vertical Scaling (First Step)

- Upgrade Railway plan (more CPU/RAM)
- Increase database size
- Upgrade Redis plan

### Horizontal Scaling (Growth)

- Multiple backend instances (load balancer)
- Read replicas for database
- Redis cluster
- CDN for static assets
- Separate ML workers (Celery)

---

## Compliance & Legal

### Required Documents

1. **Terms of Service**: Define user responsibilities
2. **Privacy Policy**: GDPR/CCPA compliance
3. **Risk Disclosure**: Trading risks
4. **Cookie Policy**: If using cookies
5. **Data Processing Agreement**: For EU users

### Regulatory Considerations

- **Not Financial Advice**: Add disclaimers
- **Trading Risks**: Clear warnings
- **Data Protection**: Encrypt sensitive data
- **User Consent**: For email/notifications
- **Age Verification**: 18+ only

---

## Success Metrics

### Track These KPIs

- User registrations
- Active users (DAU/MAU)
- Trades executed
- API response times
- Error rate
- Uptime percentage
- Revenue (if applicable)

### Monitoring Dashboard

Create dashboard with:
- Real-time active users
- API health status
- Database performance
- Error rate trends
- Revenue metrics

---

## Post-Deployment Checklist

- [ ] All services running
- [ ] Health checks passing
- [ ] Backups configured
- [ ] Monitoring active
- [ ] Alerts configured
- [ ] SSL certificates valid
- [ ] DNS propagated
- [ ] Email sending works
- [ ] WebSocket connections working
- [ ] 2FA tested
- [ ] Password reset tested
- [ ] Trading flow tested
- [ ] ML bot tested
- [ ] Backtesting tested
- [ ] Documentation updated
- [ ] Team trained
- [ ] Support ready
- [ ] Marketing materials ready
- [ ] Soft launch to beta users
- [ ] Collect feedback
- [ ] Fix issues
- [ ] Public launch 🚀

---

**Congratulations on deploying Forex AI Platform!** 🎉

For questions or support, reach out to the team.

---

*Last Updated: December 2025*
*Version: 1.0.0*
