# 🚀 Production Deployment Guide

## Pre-Deployment Checklist

### 1. Security Configuration ✅

- [ ] **Rotate Database Credentials**
  ```bash
  # Go to Supabase/Railway dashboard and generate new credentials
  # Update .env with new DATABASE_URL
  ```

- [ ] **Generate Production Secrets**
  ```bash
  # Generate JWT secret
  openssl rand -hex 32

  # Generate encryption key
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

- [ ] **Remove .env from Git History** (if committed)
  ```bash
  # WARNING: Coordinate with team before running!
  git filter-branch --force --index-filter \
    "git rm --cached --ignore-unmatch backend/.env" \
    --prune-empty --tag-name-filter cat -- --all

  git push --force --all
  ```

- [ ] **Configure Environment Variables**
  ```bash
  cd backend
  cp .env.production.template .env
  # Edit .env with production values
  nano .env
  ```

### 2. Infrastructure Setup ✅

- [ ] **Provision Managed Services**
  - PostgreSQL database (Supabase/Railway/AWS RDS)
  - Redis instance (Upstash/Redis Labs)
  - Email service (SendGrid/AWS SES)
  - Error tracking (Sentry.io)

- [ ] **Configure DNS**
  - Set up A/CNAME records
  - Configure SSL/TLS certificates
  - Set up CDN (optional: Cloudflare)

- [ ] **Set up Monitoring**
  - Sentry error tracking
  - Uptime monitoring (UptimeRobot/Pingdom)
  - Log aggregation (if using cloud platform)

### 3. Application Validation ✅

- [ ] **Run Production Validation Script**
  ```bash
  cd backend
  python scripts/validate_production.py
  ```

- [ ] **Run Database Migrations**
  ```bash
  cd backend
  alembic upgrade head
  ```

- [ ] **Test All Endpoints**
  ```bash
  # Manual testing or use automated tests
  pytest tests/test_integration.py -v
  ```

### 4. Deployment Steps ✅

#### Option A: Docker Deployment

```bash
# 1. Build production images
cd docker
docker-compose -f docker-compose.prod.yml build

# 2. Start services
docker-compose -f docker-compose.prod.yml up -d

# 3. Check health
curl http://localhost:8000/api/v1/health
curl http://localhost:3000
```

#### Option B: Cloud Platform Deployment

**Railway:**
```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login
railway login

# 3. Create project
railway init

# 4. Add services
railway add # Select PostgreSQL
railway add # Select Redis

# 5. Set environment variables
railway variables set ENVIRONMENT=production
railway variables set JWT_SECRET=your-secret
# ... (set all required vars)

# 6. Deploy
railway up
```

**Vercel (Frontend):**
```bash
cd frontend
vercel --prod
```

### 5. Post-Deployment Validation ✅

- [ ] **Health Checks**
  ```bash
  curl https://api.yourdomain.com/api/v1/health
  ```

- [ ] **Test Critical Flows**
  - User registration
  - Login with 2FA
  - Trading operations
  - ML model predictions

- [ ] **Monitor Logs**
  ```bash
  # Docker logs
  docker-compose -f docker-compose.prod.yml logs -f

  # Check for errors
  docker-compose -f docker-compose.prod.yml logs | grep ERROR
  ```

- [ ] **Verify Monitoring**
  - Check Sentry dashboard
  - Verify metrics are being collected
  - Test error reporting

### 6. Rollback Plan ✅

- [ ] **Document Current Version**
  ```bash
  git tag v1.0.0-prod-$(date +%Y%m%d-%H%M%S)
  git push --tags
  ```

- [ ] **Prepare Rollback**
  ```bash
  # Keep previous image tags
  docker tag nusatrade-backend:latest nusatrade-backend:rollback
  docker tag nusatrade-frontend:latest nusatrade-frontend:rollback
  ```

- [ ] **Test Rollback Procedure**
  - Document steps to revert
  - Test database rollback (alembic downgrade)

---

## Environment Variables Checklist

### Critical (MUST SET)
- ✅ `ENVIRONMENT=production`
- ✅ `DATABASE_URL` (managed service, not localhost)
- ✅ `REDIS_URL` (managed service, not localhost)
- ✅ `JWT_SECRET` (min 32 characters)
- ✅ `SETTINGS_ENCRYPTION_KEY`
- ✅ `FRONTEND_URL` (https://, not localhost)
- ✅ `BACKEND_CORS_ORIGINS` (no localhost)

### Important (SHOULD SET)
- ⚠️ `LLM_API_KEY` (for AI features)
- ⚠️ `SENDGRID_API_KEY` (for emails)
- ⚠️ `SENTRY_DSN` (for error tracking)

### Optional
- 📝 `R2_ACCOUNT_ID` (cloud storage)
- 📝 `SENTRY_TRACES_SAMPLE_RATE=0.1`

---

## Deployment Platforms

### Recommended Stack

**Backend:**
- Railway (easy, auto-scaling)
- AWS ECS (advanced, full control)
- DigitalOcean App Platform (simple)

**Frontend:**
- Vercel (recommended for Next.js)
- Netlify (alternative)
- Cloudflare Pages

**Database:**
- Supabase (PostgreSQL + extras)
- Railway PostgreSQL
- AWS RDS

**Redis:**
- Upstash (serverless Redis)
- Redis Labs
- AWS ElastiCache

---

## Performance Optimization

### Database
```sql
-- Add indexes for frequently queried fields
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_trades_user_created ON trades(user_id, created_at DESC);
CREATE INDEX idx_ml_models_user ON ml_models(user_id);
```

### Caching Strategy
- Use Redis for session storage
- Cache ML model predictions (5 min TTL)
- Cache market data (1 min TTL)

### Connection Pooling
- Current config: 20 connections, 10 overflow
- Adjust based on load testing

---

## Monitoring & Alerts

### Set up Alerts for:
- Error rate > 5%
- Response time > 2s (p95)
- Database connection pool exhausted
- Redis connection failures
- Disk space < 20%
- Memory usage > 80%

### Metrics to Track:
- Request rate
- Error rate
- Response time (p50, p95, p99)
- Database query time
- Active WebSocket connections
- ML model prediction latency

---

## Security Hardening

### SSL/TLS
- Use Let's Encrypt or Cloudflare for SSL
- Enforce HTTPS redirects
- Enable HSTS headers

### Firewall Rules
- Allow only ports 80, 443 publicly
- Restrict database access to application servers only
- Use VPC/private networking where possible

### Regular Maintenance
- Rotate secrets every 90 days
- Update dependencies monthly
- Review and revoke old API keys
- Monitor for security advisories

---

## Troubleshooting

### Backend Won't Start
```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. Missing environment variables
python scripts/validate_production.py

# 2. Database connection
psql $DATABASE_URL -c "SELECT 1"

# 3. Redis connection
redis-cli -u $REDIS_URL ping
```

### High Memory Usage
```bash
# Check container stats
docker stats

# Reduce worker count
# In Dockerfile.backend.prod, change --workers 4 to --workers 2
```

### Database Migration Failed
```bash
# Check current version
alembic current

# Rollback one version
alembic downgrade -1

# Re-apply
alembic upgrade head
```

---

## Emergency Contacts

- **Technical Lead**: [Your Name] - [email/phone]
- **DevOps**: [Name] - [email/phone]
- **Database Admin**: [Name] - [email/phone]
- **On-Call**: [Rotation schedule]

---

## Next Steps After Deployment

1. ✅ Monitor for 24 hours
2. ✅ Set up automated backups
3. ✅ Configure auto-scaling rules
4. ✅ Run load tests
5. ✅ Document runbooks for common issues
6. ✅ Schedule security audit
7. ✅ Plan disaster recovery drills

---

**Last Updated**: December 2024
**Document Version**: 1.0.0
