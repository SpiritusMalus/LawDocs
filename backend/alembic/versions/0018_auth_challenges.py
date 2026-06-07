"""add auth_challenges table + index on users.public_key

Revision ID: 0018
Revises: 0017
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_challenges",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("public_key", sa.String(), nullable=False),
        sa.Column("nonce_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    # Логин по ключу ищет юзера по публичному ключу — без индекса это full scan.
    op.create_index("ix_users_public_key", "users", ["public_key"])


def downgrade() -> None:
    op.drop_index("ix_users_public_key", table_name="users")
    op.drop_table("auth_challenges")
