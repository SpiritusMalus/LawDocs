"""add processing_restricted to users

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("processing_restricted", sa.Boolean(), nullable=False, server_default="false"),
    )
    op.add_column(
        "users",
        sa.Column("processing_restricted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "processing_restricted_at")
    op.drop_column("users", "processing_restricted")
