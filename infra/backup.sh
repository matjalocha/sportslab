#!/bin/bash
# Daily Postgres backup to Backblaze B2.
# Requires: b2 CLI tool, POSTGRES_PASSWORD, B2_KEY_ID, B2_APPLICATION_KEY, B2_BUCKET env vars.

set -euo pipefail

DATE=$(date +%Y-%m-%d)
BACKUP_DIR="/tmp/sportslab-backups"
BACKUP_FILE="${BACKUP_DIR}/sportslab_${DATE}.sql.gz"

mkdir -p "$BACKUP_DIR"

PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump -h localhost -U sportslab sportslab | gzip > "$BACKUP_FILE"

b2 upload-file "${B2_BUCKET}" "$BACKUP_FILE" "backups/daily/sportslab_${DATE}.sql.gz"

rm -f "$BACKUP_FILE"

# Retention policy is managed in B2 lifecycle rules:
# keep 7 daily backups and 4 weekly Sunday backups.
echo "Backup complete: sportslab_${DATE}.sql.gz"
