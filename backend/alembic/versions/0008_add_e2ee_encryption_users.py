"""add e2ee encryption fields to users

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-22
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавить поля для E2EE
    op.add_column(
        "users",
        sa.Column("email_hash", sa.String(64), nullable=True, unique=True, index=True),
    )
    op.add_column(
        "users",
        sa.Column("email_encrypted", sa.String(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("name_encrypted", sa.String(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("public_key", sa.String(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("private_key_backup_encrypted", sa.String(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("consent_timestamp", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("consent_ip", sa.String(45), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "consent_ip")
    op.drop_column("users", "consent_timestamp")
    op.drop_column("users", "private_key_backup_encrypted")
    op.drop_column("users", "public_key")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "name_encrypted")
    op.drop_column("users", "email_encrypted")
    op.drop_index("ix_users_email_hash", table_name="users")
    op.drop_column("users", "email_hash")
