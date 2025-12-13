# 🚀 Production Launch Checklist - Forex AI Platform

**CRITICAL**: This checklist MUST be completed 100% before launching with real money trading.

Last Updated: 2025-12-12
Version: 1.0

---

## ⚠️ PRE-LAUNCH WARNING

**Real money trading requires ZERO-ERROR tolerance**. Do not skip any items. If unsure about any item, STOP and get clarification.

---

## 📋 Checklist Overview

- [x] = IMPLEMENTED (by Claude Code)
- [ ] = NEEDS MANUAL VERIFICATION/COMPLETION

---

## 1️⃣ Security & Authentication (CRITICAL)

### Secrets & Credentials

- [x] JWT_SECRET is strong (32+ chars, high entropy)
- [x] JWT_SECRET validation prevents weak secrets
- [ ] JWT_SECRET is unique (not from documentation/examples)
- [x] SETTINGS_ENCRYPTION_KEY set (for encrypted settings)
- [ ] Database password is strong (16+ chars)
- [ ] Database password is NOT default (postgres/postgres)
- [ ] Redis password is set (if applicable)
- [ ] All API keys rotated from development keys

### Environment Configuration

- [x] ENVIRONMENT=production validated on startup
- [x] DEBUG=false enforced in production
- [x] API docs disabled in production (/docs, /redoc, /openapi.json)
- [ ] CORS origins restricted to production domains only
- [ ] No localhost/127.0.0.1 in CORS origins
- [ ] All environment variables documented in `.env.production.example`

### Authentication & Authorization

- [x] Rate limiting on auth endpoints (5 req/min, 50 req/hour)
- [x] Rate limiting on trading endpoints (30 req/min, 500 req/hour)
- [x] Rate limiting fail-closed in production (blocks on Redis failure)
- [ ] 2FA enabled for admin accounts
- [ ] Password strength requirements enforced
- [ ] Account lockout after failed login attempts
- [ ] Session timeout configured (60 minutes)
- [ ] Refresh tokens expire after 7 days

---

## 2️⃣ Data Integrity & Trading (CRITICAL)

### Database Transaction Safety

- [x] Test: MT5 success commits to database
- [x] Test: MT5 failure rolls back database
- [x] Test: MT5 connector offline prevents trades
- [x] Test: Network timeout triggers rollback
- [ ] Verify: No orphaned trades in database
- [ ] Verify: No orphaned positions in database
- [ ] Run data integrity audit script

### Money Calculations

- [x] Test: BUY profit calculation accuracy
- [x] Test: BUY loss calculation accuracy
- [x] Test: SELL profit calculation accuracy
- [x] Test: SELL loss calculation accuracy
- [x] Test: Fractional lot calculations (0.01, 0.1)
- [x] Test: Large lot calculations (no overflow)
- [x] Test: Zero profit scenario
- [ ] Verify: Profit calculations against known trades

### Input Validation

- [x] Negative lot sizes rejected
- [x] Zero lot sizes rejected
- [x] Excessive lot sizes rejected (> max_lot_size)
- [x] Invalid symbol formats rejected
- [x] Invalid prices rejected (negative, zero)
- [ ] SL/TP validation (must be logical based on entry)
- [ ] Position size limits enforced per user

### Race Conditions & Concurrency

- [x] Test: Concurrent trades respect position limit
- [x] Test: Double-close prevention
- [ ] Test: High-frequency trading stress test
- [ ] Test: Database connection pool under load

---

## 3️⃣ Infrastructure & Deployment

### Database

- [ ] PostgreSQL 14+ running
- [ ] Database connection pool configured (size: 20)
- [ ] Database indexes created on frequently queried columns
- [ ] Database vacuuming scheduled
- [ ] Database performance metrics monitored

### Redis

- [ ] Redis 7+ running
- [ ] Redis persistence enabled (AOF + RDB)
- [ ] Redis maxmemory policy set (allkeys-lru)
- [ ] Redis connection pool configured

### Backups

- [x] Automated backup script created (`scripts/backup_database.sh`)
- [ ] Backup script configured with correct credentials
- [ ] Backup cron job scheduled (every 6 hours)
- [ ] Backup verification enabled (`--verify` flag)
- [ ] Cloud upload configured (`--upload` to S3)
- [ ] Backup retention policy set (30 days local, 90 days cloud)
- [ ] Monthly backup restore test scheduled
- [ ] Disaster recovery plan documented

### Monitoring

- [ ] Sentry DSN configured
- [ ] Sentry error tracking active
- [ ] Sentry performance monitoring enabled
- [ ] Critical error alerts configured (email/Slack)
- [ ] Health check endpoint responding (`/api/v1/health`)
- [ ] Uptime monitoring configured (UptimeRobot/Pingdom)
- [ ] CPU/Memory alerts configured
- [ ] Database query performance monitored

### Deployment

- [ ] CI/CD pipeline running tests
- [ ] All tests passing (run: `pytest --cov=app tests/`)
- [ ] Docker images built for production
- [ ] Environment variables set in production
- [ ] Database migrations run (`alembic upgrade head`)
- [ ] SSL certificates valid and not expiring soon
- [ ] DNS records configured
- [ ] CDN configured (if applicable)

---

## 4️⃣ Testing & Quality Assurance

### Test Coverage

- [x] Data integrity tests (DB-MT5 sync)
- [x] Race condition tests
- [x] Money calculation tests
- [x] Error recovery tests
- [ ] Integration tests passing
- [ ] End-to-end tests passing
- [ ] Test coverage >80% on critical paths

### Manual Testing Checklist

- [ ] **User Registration**:
  - [ ] Register new user
  - [ ] Verify email sent (if applicable)
  - [ ] Verify password strength enforcement

- [ ] **Authentication**:
  - [ ] Login with correct credentials
  - [ ] Login with wrong password (should fail)
  - [ ] Login with non-existent user (should fail)
  - [ ] Rate limit triggered after 5 failed attempts
  - [ ] 2FA login (if enabled)

- [ ] **Trading Flow** (with DEMO account first!):
  - [ ] Connect MT5 connector
  - [ ] Open BUY position
  - [ ] Verify position appears in database
  - [ ] Verify position appears in MT5
  - [ ] Close position
  - [ ] Verify position closed in both DB and MT5
  - [ ] Verify profit calculation is correct
  - [ ] Test SL/TP execution

- [ ] **Error Scenarios**:
  - [ ] MT5 connector disconnect during trade
  - [ ] Network timeout during trade
  - [ ] Invalid lot size rejection
  - [ ] Position limit enforcement
  - [ ] Insufficient margin handling

---

## 5️⃣ Performance & Scalability

### Load Testing

- [ ] Auth endpoint load test (100 concurrent users)
- [ ] Trading endpoint load test (50 concurrent trades)
- [ ] Database query performance under load
- [ ] Redis performance under load
- [ ] WebSocket connections (MT5 connector)

### Performance Metrics

- [ ] API response time < 200ms (p95)
- [ ] Database query time < 100ms (p95)
- [ ] Trade execution time < 1s (p95)
- [ ] No memory leaks detected
- [ ] No database connection pool exhaustion

---

## 6️⃣ Legal & Compliance

### Documentation

- [x] Disaster recovery plan documented
- [ ] Terms of Service reviewed and updated
- [ ] Privacy Policy compliant (GDPR/CCPA if applicable)
- [ ] Risk disclosure prominent
- [ ] API documentation (internal use)
- [ ] User manual for MT5 connector

### Regulatory

- [ ] Trading risk warning displayed
- [ ] "Not financial advice" disclaimer
- [ ] Age verification (18+)
- [ ] User data encryption at rest and in transit
- [ ] Data retention policy documented
- [ ] GDPR data export capability (if EU users)

---

## 7️⃣ Operational Readiness

### Team Preparedness

- [ ] On-call schedule defined
- [ ] Escalation path documented
- [ ] Emergency contacts updated
- [ ] Disaster recovery drill completed
- [ ] Team trained on runbooks

### User Communication

- [ ] Status page set up
- [ ] Support email configured
- [ ] User notification system tested
- [ ] Incident communication template ready

---

## 8️⃣ Pre-Launch Verification (24 hours before)

Run these commands to verify production readiness:

```bash
# 1. Backend health check
curl https://api.yourdomain.com/api/v1/health
# Expected: {"status":"ok"}

# 2. Database connection
psql $DATABASE_URL -c "SELECT COUNT(*) FROM users;"
# Expected: Returns count

# 3. Redis connection
redis-cli -u $REDIS_URL ping
# Expected: PONG

# 4. Run full test suite
cd backend && pytest -v
# Expected: All tests pass

# 5. Check Sentry integration
# Trigger test error and verify it appears in Sentry

# 6. Verify backups
ls -lh /var/backups/forexai/
# Expected: Recent backup files exist

# 7. Check environment
env | grep -E "ENVIRONMENT|DEBUG|JWT_SECRET"
# Expected: ENVIRONMENT=production, DEBUG=false, JWT_SECRET=<strong-secret>

# 8. Verify API docs disabled
curl https://api.yourdomain.com/docs
# Expected: 404 Not Found

# 9. Test rate limiting
for i in {1..10}; do curl -X POST https://api.yourdomain.com/api/v1/auth/login; done
# Expected: 429 Too Many Requests after 5 attempts

# 10. Check SSL certificate
openssl s_client -connect api.yourdomain.com:443 -servername api.yourdomain.com < /dev/null 2>/dev/null | openssl x509 -noout -dates
# Expected: Valid dates, not expiring soon
```

---

## 9️⃣ Launch Day Checklist

### Morning (T-4 hours)

- [ ] Review all monitoring dashboards
- [ ] Verify backups from last night
- [ ] Check all services healthy
- [ ] Confirm on-call engineer available
- [ ] Prepare status page announcement

### Pre-Launch (T-1 hour)

- [ ] Final database backup
- [ ] Final code deployment
- [ ] Smoke test all critical paths
- [ ] Enable production traffic
- [ ] Monitor error rates

### Post-Launch (T+0 to T+4 hours)

- [ ] Monitor Sentry for errors
- [ ] Monitor API response times
- [ ] Monitor database performance
- [ ] Monitor user signups
- [ ] Monitor first trades
- [ ] Be ready to rollback if issues

### Post-Launch (T+24 hours)

- [ ] Review error logs
- [ ] Review support tickets
- [ ] Check backup completion
- [ ] Performance review
- [ ] User feedback collection

---

## 🔟 Rollback Plan

If critical issues occur:

1. **STOP TRADING IMMEDIATELY**:
   ```bash
   # Disable trading in admin panel OR
   psql $DB_NAME -c "UPDATE users SET auto_trading_enabled = false;"
   ```

2. **Notify users**:
   - Status page update
   - Email notification
   - In-app alert

3. **Revert code**:
   ```bash
   git revert HEAD
   # OR redeploy previous version
   ```

4. **Restore database (if data corruption)**:
   - See DISASTER_RECOVERY.md

5. **Investigate and fix**

6. **Deploy fix and re-launch**

---

## ✅ Final Sign-Off

Before launching to production, the following people MUST sign off:

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Lead Developer | _______ | _______ | ___/___/___ |
| DevOps Engineer | _______ | _______ | ___/___/___ |
| Security Lead | _______ | _______ | ___/___/___ |
| CTO/Technical Lead | _______ | _______ | ___/___/___ |

---

**REMEMBER**: Real money = real responsibility. When in doubt, delay launch and fix issues.

**Good luck! 🚀**
