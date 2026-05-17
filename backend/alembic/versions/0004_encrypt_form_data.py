"""encrypt form_data with Fernet (152-ФЗ)

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-17

Требования перед запуском:
  1. Сгенерируйте ключ: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  2. Добавьте FERNET_KEY=<ключ> в /opt/lawdocs/.env
  3. Запустите миграцию: alembic upgrade head
"""

import json
import os

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    fernet_key = os.environ.get("FERNET_KEY", "").strip()
    if not fernet_key:
        raise SystemExit(
            "\n\nFERNET_KEY не задан в окружении.\n"
            "Сгенерируйте ключ и добавьте в .env:\n"
            "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
        )

    from cryptography.fernet import Fernet
    f = Fernet(fernet_key.encode())

    # Добавляем TEXT-колонку рядом с JSON
    op.add_column("orders", sa.Column("form_data_enc", sa.Text(), nullable=True))

    conn = op.get_bind()

    # Читаем и шифруем все строки
    rows = conn.execute(sa.text("SELECT id, form_data FROM orders"))
    for row in rows.mappings():
        data = row["form_data"] or {}
        encrypted = f.encrypt(json.dumps(data, ensure_ascii=False).encode()).decode()
        conn.execute(
            sa.text("UPDATE orders SET form_data_enc = :enc WHERE id = :id"),
            {"enc": encrypted, "id": row["id"]},
        )

    # Убираем старую JSON-колонку, переименовываем новую
    op.drop_column("orders", "form_data")
    op.execute("ALTER TABLE orders RENAME COLUMN form_data_enc TO form_data")
    op.alter_column("orders", "form_data", nullable=False)


def downgrade() -> None:
    fernet_key = os.environ.get("FERNET_KEY", "").strip()
    if not fernet_key:
        raise SystemExit("FERNET_KEY не задан — невозможно расшифровать данные для downgrade")

    from cryptography.fernet import Fernet
    f = Fernet(fernet_key.encode())

    op.add_column("orders", sa.Column("form_data_plain", sa.JSON(), nullable=True))

    conn = op.get_bind()
    rows = conn.execute(sa.text("SELECT id, form_data FROM orders"))
    for row in rows.mappings():
        try:
            data = json.loads(f.decrypt(row["form_data"].encode()).decode())
        except Exception:
            data = {}
        conn.execute(
            sa.text("UPDATE orders SET form_data_plain = :data::jsonb WHERE id = :id"),
            {"data": json.dumps(data, ensure_ascii=False), "id": row["id"]},
        )

    op.drop_column("orders", "form_data")
    op.execute("ALTER TABLE orders RENAME COLUMN form_data_plain TO form_data")
    op.alter_column("orders", "form_data", nullable=False)
