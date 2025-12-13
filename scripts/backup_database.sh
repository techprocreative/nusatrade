#!/usr/bin/env bash
#
# Automated Database Backup Script for Forex AI Platform
# CRITICAL: For real money trading, reliable backups are MANDATORY
#
# Features:
# - Full PostgreSQL dumps with compression
# - Retention policy (keeps last N backups)
# - Backup verification
# - Upload to cloud storage (S3-compatible)
# - Automatic cleanup of old backups
# - Error notifications
#
# Usage:
#   ./backup_database.sh [--verify] [--upload]
#
# Cron schedule (recommended):
#   0 */6 * * * /path/to/backup_database.sh --upload >> /var/log/forex-ai-backup.log 2>&1
#

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# ==============================================================================
# Configuration
# ==============================================================================

# Database connection (read from environment or .env file)
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-forexai}"
DB_USER="${DB_USER:-forexai}"
DB_PASSWORD="${DB_PASSWORD:-}"

# Backup configuration
BACKUP_DIR="${BACKUP_DIR:-/var/backups/forexai}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"  # Keep backups for 30 days
MAX_BACKUPS="${MAX_BACKUPS:-60}"  # Maximum number of backups to keep

# Cloud storage (S3-compatible: AWS S3, Cloudflare R2, MinIO, etc.)
S3_BUCKET="${S3_BUCKET:-}"
S3_ENDPOINT="${S3_ENDPOINT:-}"  # Optional: for S3-compatible services
S3_REGION="${S3_REGION:-us-east-1}"

# Notification endpoints
WEBHOOK_URL="${BACKUP_WEBHOOK_URL:-}"  # Slack/Discord webhook for notifications
SENTRY_DSN="${SENTRY_DSN:-}"  # Sentry for error tracking

# ==============================================================================
# Functions
# ==============================================================================

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $*"
}

log_error() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $*" >&2
}

send_notification() {
    local message="$1"
    local level="${2:-info}"  # info, warning, error

    if [[ -n "$WEBHOOK_URL" ]]; then
        curl -X POST "$WEBHOOK_URL" \
            -H "Content-Type: application/json" \
            -d "{\"text\": \"🔴 Forex AI Backup $level: $message\"}" \
            --silent --show-error || true
    fi
}

check_dependencies() {
    local missing_deps=()

    command -v pg_dump >/dev/null 2>&1 || missing_deps+=("pg_dump")
    command -v gzip >/dev/null 2>&1 || missing_deps+=("gzip")

    if [[ "${1:-}" == "--upload" ]] && ! command -v aws >/dev/null 2>&1; then
        missing_deps+=("aws-cli")
    fi

    if [[ ${#missing_deps[@]} -gt 0 ]]; then
        log_error "Missing dependencies: ${missing_deps[*]}"
        exit 1
    fi
}

create_backup() {
    local backup_file="$1"

    log "Creating backup: $backup_file"

    # Use pg_dump with custom format (compressed, allows selective restore)
    PGPASSWORD="$DB_PASSWORD" pg_dump \
        --host="$DB_HOST" \
        --port="$DB_PORT" \
        --username="$DB_USER" \
        --dbname="$DB_NAME" \
        --format=custom \
        --compress=9 \
        --file="$backup_file" \
        --verbose

    local size=$(du -h "$backup_file" | cut -f1)
    log "Backup created successfully (size: $size)"
}

verify_backup() {
    local backup_file="$1"

    log "Verifying backup integrity..."

    # List backup contents without restoring
    PGPASSWORD="$DB_PASSWORD" pg_restore \
        --list "$backup_file" \
        >/dev/null 2>&1

    if [[ $? -eq 0 ]]; then
        log "✓ Backup verification PASSED"
        return 0
    else
        log_error "✗ Backup verification FAILED"
        return 1
    fi
}

upload_to_cloud() {
    local backup_file="$1"
    local backup_name=$(basename "$backup_file")

    if [[ -z "$S3_BUCKET" ]]; then
        log "S3_BUCKET not configured, skipping cloud upload"
        return 0
    fi

    log "Uploading backup to S3: s3://$S3_BUCKET/backups/$backup_name"

    local aws_args=(
        s3 cp "$backup_file" "s3://$S3_BUCKET/backups/$backup_name"
        --region "$S3_REGION"
    )

    if [[ -n "$S3_ENDPOINT" ]]; then
        aws_args+=(--endpoint-url "$S3_ENDPOINT")
    fi

    if aws "${aws_args[@]}"; then
        log "✓ Upload to S3 successful"
    else
        log_error "✗ Upload to S3 failed"
        return 1
    fi
}

cleanup_old_backups() {
    log "Cleaning up old backups (retention: $RETENTION_DAYS days, max: $MAX_BACKUPS files)"

    # Delete backups older than retention period
    find "$BACKUP_DIR" -name "forexai_backup_*.dump" -type f -mtime +"$RETENTION_DAYS" -delete

    # If still over max count, delete oldest
    local backup_count=$(find "$BACKUP_DIR" -name "forexai_backup_*.dump" -type f | wc -l)

    if [[ $backup_count -gt $MAX_BACKUPS ]]; then
        find "$BACKUP_DIR" -name "forexai_backup_*.dump" -type f -printf '%T+ %p\n' \
            | sort \
            | head -n $((backup_count - MAX_BACKUPS)) \
            | cut -d' ' -f2- \
            | xargs rm -f
    fi

    log "Cleanup complete"
}

# ==============================================================================
# Main Script
# ==============================================================================

main() {
    local verify_flag=false
    local upload_flag=false

    # Parse arguments
    for arg in "$@"; do
        case $arg in
            --verify) verify_flag=true ;;
            --upload) upload_flag=true ;;
            *)
                echo "Usage: $0 [--verify] [--upload]"
                exit 1
                ;;
        esac
    done

    log "========================================="
    log "Forex AI Database Backup Started"
    log "========================================="

    # Check dependencies
    check_dependencies "$@"

    # Create backup directory if it doesn't exist
    mkdir -p "$BACKUP_DIR"

    # Generate backup filename with timestamp
    local timestamp=$(date +'%Y%m%d_%H%M%S')
    local backup_file="$BACKUP_DIR/forexai_backup_${timestamp}.dump"

    # Create backup
    if ! create_backup "$backup_file"; then
        log_error "Backup creation failed"
        send_notification "Database backup FAILED" "error"
        exit 1
    fi

    # Verify backup if requested
    if [[ "$verify_flag" == true ]]; then
        if ! verify_backup "$backup_file"; then
            log_error "Backup verification failed"
            send_notification "Backup verification FAILED" "error"
            exit 1
        fi
    fi

    # Upload to cloud if requested
    if [[ "$upload_flag" == true ]]; then
        if ! upload_to_cloud "$backup_file"; then
            log_error "Cloud upload failed"
            send_notification "Backup upload to S3 FAILED" "warning"
            # Don't exit - local backup still exists
        fi
    fi

    # Cleanup old backups
    cleanup_old_backups

    log "========================================="
    log "Backup completed successfully"
    log "Backup file: $backup_file"
    log "========================================="

    send_notification "Database backup completed: $(basename $backup_file)" "info"
}

# Run main function
main "$@"
