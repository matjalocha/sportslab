#!/bin/bash
# Restore from B2 backup.
# Usage: ./restore.sh 2024-04-06

set -euo pipefail

DATE=${1:?Usage: ./restore.sh YYYY-MM-DD}

b2 download-file-by-name "${B2_BUCKET}" "backups/daily/sportslab_${DATE}.sql.gz" "/tmp/restore.sql.gz"
gunzip -c /tmp/restore.sql.gz | PGPASSWORD="${POSTGRES_PASSWORD}" psql -h localhost -U sportslab sportslab
