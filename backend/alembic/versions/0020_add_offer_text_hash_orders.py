"""add offer_text_hash to orders

Хэш канонического текста принятой редакции оферты (SHA-256, hex = 64 символа).
Версия (offer_version) — это метка редакции; хэш фиксирует, КАКОЙ именно текст
видел Заказчик в момент акцепта (доказуемость согласия). Nullable — старые заказы
без хэша остаются валидными.

Revision ID: 0020
Revises: 0019
Create Date: 2026-06-08
"""

from alembic import op
import sqlalchemy as sa

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("offer_text_hash", sa.String(length=64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orders", "offer_text_hash")
