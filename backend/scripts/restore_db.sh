#!/usr/bin/env bash
# Восстановление Postgres LawDocs из дампа backup_db.sh (custom format).
#
# ⚠️ ДЕСТРУКТИВНО: --clean удаляет существующие объекты перед восстановлением.
# Запускать осознанно, в окне обслуживания, проверив целевой DATABASE_URL.
#
# Использование:
#   DATABASE_URL=postgresql://user:pass@host:5432/lawdocs ./scripts/restore_db.sh <dump-file>
set -euo pipefail

: "${DATABASE_URL:?DATABASE_URL не задан}"
DUMP="${1:?Укажите файл дампа: ./scripts/restore_db.sh <dump-file>}"
[ -f "$DUMP" ] || { echo "Файл не найден: $DUMP" >&2; exit 1; }

PG_URL="${DATABASE_URL/+asyncpg/}"

echo "ВНИМАНИЕ: восстановление в $PG_URL из $DUMP (существующие данные будут перезаписаны)."
read -r -p "Продолжить? введите 'yes': " ans
[ "$ans" = "yes" ] || { echo "Отменено"; exit 1; }

pg_restore --clean --if-exists --no-owner --no-privileges --dbname="$PG_URL" "$DUMP"
echo "Restore complete. Проверьте: alembic current (схема должна совпасть с head)."
