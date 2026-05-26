"""make order_reviews.user_id nullable for account deletion anonymization

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-26
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("order_reviews", "user_id", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    op.execute("UPDATE order_reviews SET user_id = 'deleted' WHERE user_id IS NULL")
    op.alter_column("order_reviews", "user_id", existing_type=sa.String(), nullable=False)
