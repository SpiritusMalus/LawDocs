#!/usr/bin/env bash
# Бэкап Postgres LawDocs в сжатый дамп (custom format, pg_restore-совместим).
#
# Использование:
#   DATABASE_URL=postgresql://user:pass@host:5432/lawdocs ./scripts/backup_db.sh [dir]
#
# Дамп: <dir>/lawdocs-YYYYmmdd-HHMMSS.dump  (по умолчанию dir=./backups)
# Хранит последние BACKUP_KEEP дампов (по умолчанию 14), старые удаляет.
#
# Восстановление — см. restore_db.sh и docs/runbooks/disaster-recovery.md.
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL не задан}"
OUT_DIR="${1:-./backups}"
KEEP="${BACKUP_KEEP:-14}"

# pg_dump понимает postgresql:// , но не драйверный суффикс +asyncpg — срезаем.
PG_URL="${DATABASE_URL/+asyncpg/}"

mkdir -p "$OUT_DIR"
STAMP="$(date -u +%Y%m%d-%H%M%S)"
FILE="$OUT_DIR/lawdocs-$STAMP.dump"

echo "Dumping to $FILE ..."
pg_dump --format=custom --no-owner --no-privileges --dbname="$PG_URL" --file="$FILE"
echo "OK: $(du -h "$FILE" | cut -f1)"

# Ротация: оставить KEEP последних.
ls -1t "$OUT_DIR"/lawdocs-*.dump 2>/dev/null | tail -n +"$((KEEP + 1))" | xargs -r rm -f
echo "Retained last $KEEP dumps in $OUT_DIR"
