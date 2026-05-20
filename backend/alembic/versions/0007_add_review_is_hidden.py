"""add is_hidden to order_reviews

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-20
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "order_reviews",
        sa.Column("is_hidden", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("order_reviews", "is_hidden")
