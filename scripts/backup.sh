#!/bin/bash
set -euo pipefail

# Daily PostgreSQL backup script for LawDocs
# Keeps last 7 daily + 4 weekly backups
# Run via docker exec from cron container

BACKUP_DIR="/backups"
DB_NAME="${POSTGRES_DB:-lawdocs}"
DB_USER="${POSTGRES_USER:-lawdocs}"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
FILENAME="lawdocs_${TIMESTAMP}.sql.gz"
WEEKLY_KEEP=4
DAILY_KEEP=7

mkdir -p "$BACKUP_DIR"

pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_DIR/$FILENAME"

echo "Backup created: $FILENAME ($(du -sh "$BACKUP_DIR/$FILENAME" | cut -f1))"

# Remove daily backups older than DAILY_KEEP days
find "$BACKUP_DIR" -name "lawdocs_*.sql.gz" -mtime +"$DAILY_KEEP" | while read -r f; do
    # Keep weekly backups (every 7th) for WEEKLY_KEEP weeks
    age_days=$(( ( $(date +%s) - $(date -r "$f" +%s) ) / 86400 ))
    if (( age_days % 7 != 0 )) || (( age_days > WEEKLY_KEEP * 7 )); then
        rm -f "$f"
        echo "Removed old backup: $(basename "$f")"
    fi
done
