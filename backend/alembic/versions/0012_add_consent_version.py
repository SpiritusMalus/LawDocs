"""add consent_version to users

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-26
"""

from alembic import op
import sqlalchemy as sa

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("consent_version", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "consent_version")
