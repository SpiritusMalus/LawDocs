"""add order_reviews table and user name/completed_orders_count

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-19
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("name", sa.String(100), nullable=True))
    op.add_column("users", sa.Column("completed_orders_count", sa.Integer(), nullable=False, server_default="0"))

    op.create_table(
        "order_reviews",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("order_id", sa.String(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("user_id", sa.String(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("situation_id", sa.String(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("text", sa.String(1000), nullable=False),
        sa.Column("name", sa.String(100), nullable=True),
        sa.Column("city", sa.String(50), nullable=True),
        sa.Column("completed_orders_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id"),
    )
    op.create_index("ix_order_reviews_order_id", "order_reviews", ["order_id"])
    op.create_index("ix_order_reviews_user_id", "order_reviews", ["user_id"])
    op.create_index("ix_order_reviews_situation_id", "order_reviews", ["situation_id"])


def downgrade() -> None:
    op.drop_index("ix_order_reviews_situation_id", "order_reviews")
    op.drop_index("ix_order_reviews_user_id", "order_reviews")
    op.drop_index("ix_order_reviews_order_id", "order_reviews")
    op.drop_table("order_reviews")
    op.drop_column("users", "completed_orders_count")
    op.drop_column("users", "name")
