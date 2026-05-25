"""add user_encrypted to documents

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-24
"""

import sqlalchemy as sa
from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "documents",
        sa.Column("user_encrypted", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("documents", "user_encrypted")
