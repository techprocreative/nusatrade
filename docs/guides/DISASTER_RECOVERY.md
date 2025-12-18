# 🚨 Disaster Recovery Plan - Forex AI Platform

**CRITICAL**: For real money trading, this document is MANDATORY reading for all operators.

Last Updated: 2025-12-12
Version: 1.0

---

## 📋 Table of Contents

1. [Backup Strategy](#backup-strategy)
2. [Restore Procedures](#restore-procedures)
3. [Disaster Scenarios](#disaster-scenarios)
4. [Emergency Contacts](#emergency-contacts)
5. [Post-Recovery Checklist](#post-recovery-checklist)

---

## 🔐 Backup Strategy

### Automated Backups

**Schedule**: Every 6 hours (00:00, 06:00, 12:00, 18:00 UTC)

**Script**: `/scripts/backup_database.sh`

**Cron Configuration**:
```bash
# Add to crontab (crontab -e)
0 */6 * * * /path/to/forex-ai/scripts/backup_database.sh --verify --upload >> /var/log/forex-ai-backup.log 2>&1
```

**Retention Policy**:
- **Local backups**: 30 days
- **Cloud backups (S3)**: 90 days
- **Monthly snapshots**: 1 year

### What Gets Backed Up

1. **Database (PostgreSQL)**:
   - All user accounts
   - Trading history
   - Open positions
   - ML models
   - System settings

2. **File Storage** (if applicable):
   - User uploads
   - ML model files
   - Logs

3. **Configuration**:
   - Environment variables (encrypted)
   - Secrets (stored separately in vault)

### Backup Verification

**Weekly**: Automated verification (script includes `--verify` flag)

**Monthly**: Full restore test to staging environment

**Verification Steps**:
```bash
# List backup contents
pg_restore --list /path/to/backup.dump

# Test restore to temporary database
createdb test_restore
pg_restore --dbname=test_restore /path/to/backup.dump

# Verify data integrity
psql test_restore -c "SELECT COUNT(*) FROM trades;"
psql test_restore -c "SELECT COUNT(*) FROM users;"

# Cleanup
dropdb test_restore
```

---

## 🔄 Restore Procedures

### 1. Full Database Restore

**When**: Complete database loss or corruption

**Downtime**: 15-60 minutes (depends on database size)

**Procedure**:

```bash
# 1. STOP ALL SERVICES IMMEDIATELY
sudo systemctl stop forexai-backend
sudo systemctl stop forexai-frontend
sudo systemctl stop forexai-workers

# 2. CLOSE ALL MT5 CONNECTOR CONNECTIONS
# Contact all users to close connectors OR force disconnect

# 3. Download latest backup
aws s3 cp s3://$S3_BUCKET/backups/latest.dump /tmp/restore.dump

# 4. Drop existing database (DANGEROUS - ensure backup is good!)
dropdb $DB_NAME

# 5. Create fresh database
createdb $DB_NAME

# 6. Restore from backup
pg_restore --dbname=$DB_NAME \
           --verbose \
           --no-owner \
           --no-privileges \
           /tmp/restore.dump

# 7. Run migrations (if needed)
cd backend
alembic upgrade head

# 8. Verify data integrity
psql $DB_NAME -c "SELECT COUNT(*) FROM trades WHERE close_time IS NULL;"
psql $DB_NAME -c "SELECT COUNT(*) FROM users;"

# 9. Restart services
sudo systemctl start forexai-backend
sudo systemctl start forexai-frontend
sudo systemctl start forexai-workers

# 10. Health check
curl https://api.yourdomain.com/api/v1/health

# 11. Notify users
# Send email/notification about restoration complete
```

### 2. Partial Database Restore (Single Table)

**When**: Specific table corrupted but rest of DB is fine

**Procedure**:

```bash
# 1. Extract single table from backup
pg_restore --list backup.dump | grep "TABLE DATA.*trades"

# 2. Restore only that table
pg_restore --dbname=$DB_NAME \
           --table=trades \
           --data-only \
           --clean \
           backup.dump
```

### 3. Point-in-Time Recovery (PITR)

**Prerequisite**: PostgreSQL configured with WAL archiving

**When**: Need to restore to specific point in time (e.g., before data corruption)

**Procedure**:

```bash
# 1. Stop PostgreSQL
sudo systemctl stop postgresql

# 2. Restore base backup
tar -xzf base_backup.tar.gz -C /var/lib/postgresql/14/main

# 3. Create recovery.conf
cat > /var/lib/postgresql/14/main/recovery.conf <<EOF
restore_command = 'cp /var/lib/postgresql/wal_archive/%f %p'
recovery_target_time = '2025-12-12 14:30:00'
EOF

# 4. Start PostgreSQL (will replay WAL to target time)
sudo systemctl start postgresql

# 5. Verify recovery
psql -c "SELECT pg_last_wal_replay_lsn();"
```

---

## 🔥 Disaster Scenarios

### Scenario 1: Complete Server Failure

**Impact**: Total service outage

**Recovery Time Objective (RTO)**: 4 hours
**Recovery Point Objective (RPO)**: 6 hours (last backup)

**Steps**:

1. **Provision new server**:
   ```bash
   # Use infrastructure-as-code (Terraform/CloudFormation)
   terraform apply -var-file="production.tfvars"
   ```

2. **Restore database** (see Full Database Restore above)

3. **Deploy application**:
   ```bash
   git clone https://github.com/yourusername/forex-ai.git
   cd forex-ai
   git checkout production

   # Deploy using Docker Compose
   docker-compose -f docker-compose.prod.yml up -d
   ```

4. **Update DNS** (if IP changed)

5. **Verify all services**

6. **Notify users**

### Scenario 2: Database Corruption

**Impact**: Data inconsistency, potential data loss

**Steps**:

1. **Isolate the issue**:
   ```bash
   # Check database integrity
   vacuumdb --analyze-only --verbose $DB_NAME

   # Check for corruption
   psql $DB_NAME -c "SELECT * FROM pg_stat_database_conflicts;"
   ```

2. **If repairable**:
   ```bash
   # Attempt repair
   vacuumdb --full --verbose $DB_NAME
   reindexdb --all $DB_NAME
   ```

3. **If not repairable**: Full restore from backup

### Scenario 3: Data Breach / Compromise

**Impact**: Security incident, potential financial loss

**IMMEDIATE ACTIONS**:

1. **ISOLATE SYSTEM**:
   ```bash
   # Block all incoming traffic
   sudo ufw deny in

   # Stop all services
   sudo systemctl stop forexai-*
   ```

2. **REVOKE ALL CREDENTIALS**:
   - Change all passwords
   - Rotate JWT secrets
   - Revoke API keys
   - Reset database credentials

3. **NOTIFY**:
   - Users (via email, not through compromised system)
   - Regulatory authorities (if required)
   - Law enforcement (if needed)

4. **FORENSICS**:
   ```bash
   # Preserve logs
   tar -czf incident_logs_$(date +%Y%m%d).tar.gz \
       /var/log/forexai/ \
       /var/log/nginx/ \
       /var/log/postgresql/

   # Preserve database snapshot
   pg_dump --format=custom $DB_NAME > incident_db_$(date +%Y%m%d).dump
   ```

5. **REBUILD FROM KNOWN-GOOD STATE**

### Scenario 4: Accidental Data Deletion

**Impact**: User data loss, trading history loss

**Steps**:

1. **Identify deletion time**:
   ```bash
   # Check audit logs
   psql $DB_NAME -c "SELECT * FROM audit_log WHERE action='DELETE' AND entity_type='trade' ORDER BY timestamp DESC LIMIT 100;"
   ```

2. **Restore from backup BEFORE deletion**:
   - Use point-in-time recovery (PITR) if available
   - Or restore from backup taken before deletion

3. **Extract deleted records**:
   ```bash
   # From restored backup
   pg_dump --table=trades --data-only restored_db > deleted_trades.sql

   # Import to production
   psql $DB_NAME < deleted_trades.sql
   ```

### Scenario 5: MT5 Connector Sync Issues

**Impact**: Database shows different positions than MT5

**Steps**:

1. **STOP AUTO-TRADING IMMEDIATELY**:
   ```bash
   # Disable auto-trading in admin panel OR
   psql $DB_NAME -c "UPDATE users SET auto_trading_enabled = false;"
   ```

2. **Reconcile positions**:
   ```bash
   # Export MT5 positions (from connector)
   # Compare with database
   psql $DB_NAME -c "SELECT * FROM positions;"
   ```

3. **Identify discrepancies**:
   - Positions in DB but not MT5: Close in DB
   - Positions in MT5 but not DB: Add to DB or close in MT5

4. **Manual reconciliation**:
   ```sql
   -- Remove orphaned positions
   DELETE FROM positions WHERE id NOT IN (SELECT position_id FROM mt5_sync_log);
   ```

---

## 📞 Emergency Contacts

### Internal Team

| Role | Name | Phone | Email | Availability |
|------|------|-------|-------|--------------|
| Lead Developer | [Name] | +XX XXX XXX | dev@forexai.com | 24/7 |
| DevOps | [Name] | +XX XXX XXX | devops@forexai.com | 24/7 |
| Security | [Name] | +XX XXX XXX | security@forexai.com | 24/7 |

### External Services

| Service | Support | Priority |
|---------|---------|----------|
| Hosting (Railway/AWS) | support@railway.app | P1 |
| Database (Supabase) | support@supabase.com | P1 |
| Monitoring (Sentry) | support@sentry.io | P2 |

### Escalation Path

1. **L1**: On-call engineer (responds within 15 minutes)
2. **L2**: Senior engineer (responds within 1 hour)
3. **L3**: CTO/Lead architect (responds within 2 hours)

---

## ✅ Post-Recovery Checklist

After any disaster recovery, complete this checklist:

- [ ] **Data Integrity**:
  - [ ] User count matches expected
  - [ ] No orphaned trades
  - [ ] All open positions accounted for
  - [ ] P/L calculations correct

- [ ] **System Health**:
  - [ ] All services running
  - [ ] Health checks passing
  - [ ] Database performance normal
  - [ ] No error spikes in Sentry

- [ ] **Security**:
  - [ ] All secrets rotated (if breach)
  - [ ] Audit logs reviewed
  - [ ] Access logs reviewed
  - [ ] No suspicious activity

- [ ] **Communication**:
  - [ ] Users notified
  - [ ] Status page updated
  - [ ] Incident documented
  - [ ] Post-mortem scheduled

- [ ] **Verification**:
  - [ ] Test user login
  - [ ] Test trade execution
  - [ ] Test MT5 connector
  - [ ] Test price feeds
  - [ ] Test notifications

- [ ] **Monitoring**:
  - [ ] Alerts configured
  - [ ] Dashboards updated
  - [ ] On-call schedule confirmed

---

## 📝 Incident Log Template

Use this template to document all incidents:

```markdown
## Incident: [Title]

**Date**: YYYY-MM-DD
**Time**: HH:MM UTC
**Severity**: Critical / High / Medium / Low
**Impact**: [Users affected, services down, data loss, etc.]

### Timeline

- [Time]: Issue detected
- [Time]: Team notified
- [Time]: Investigation started
- [Time]: Root cause identified
- [Time]: Fix implemented
- [Time]: Services restored
- [Time]: Users notified

### Root Cause

[Detailed explanation]

### Resolution

[What was done to fix it]

### Preventive Measures

[What will be done to prevent recurrence]

### Financial Impact

[If applicable: trading losses, refunds, etc.]
```

---

## 🔄 Regular Drills

**Quarterly**: Conduct disaster recovery drill

**Procedure**:
1. Schedule maintenance window
2. Simulate disaster scenario
3. Execute recovery procedures
4. Time the recovery
5. Document lessons learned
6. Update this document

---

**REMEMBER**: In a real disaster:
1. Stay calm
2. Follow procedures
3. Document everything
4. Communicate clearly
5. Learn and improve

---

*This document is a living document and should be updated after every incident or drill.*
