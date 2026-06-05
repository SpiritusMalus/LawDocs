"""add per-order guest access token hash

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("guest_token_hash", sa.String(64), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orders", "guest_token_hash")
