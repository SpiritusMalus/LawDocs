"""add auto_retry_count to orders

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-17
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("auto_retry_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("orders", "auto_retry_count")
