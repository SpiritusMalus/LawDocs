"""add user_keys keyring table

Revision ID: 0019
Revises: 0018
Create Date: 2026-06-07
"""

from alembic import op
import sqlalchemy as sa

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_keys",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("public_key", sa.String(), nullable=False),
        sa.Column("wrapped_private_key", sa.Text(), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "public_key", name="uq_user_keys_user_pubkey"),
    )
    op.create_index("ix_user_keys_user_id", "user_keys", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_keys_user_id", table_name="user_keys")
    op.drop_table("user_keys")
