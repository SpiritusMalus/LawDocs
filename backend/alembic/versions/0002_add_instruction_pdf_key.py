"""add instruction_pdf_key to documents

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-07
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("documents", sa.Column("instruction_pdf_key", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("documents", "instruction_pdf_key")
