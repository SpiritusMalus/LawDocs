"""add document preview_keys (watermarked pre-pay preview pages)

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("preview_keys", sa.JSON(), nullable=False, server_default="[]"),
    )


def downgrade() -> None:
    op.drop_column("documents", "preview_keys")
