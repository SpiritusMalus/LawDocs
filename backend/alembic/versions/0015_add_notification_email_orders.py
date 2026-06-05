"""add per-order notification_email

Revision ID: 0015
Revises: 0014
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("notification_email", sa.String(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orders", "notification_email")
