"""add offer/PDn acceptance fields to orders

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-03
"""

from alembic import op
import sqlalchemy as sa

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "orders",
        sa.Column("offer_accepted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("offer_accepted_ip", sa.String(45), nullable=True),
    )
    op.add_column(
        "orders",
        sa.Column("offer_version", sa.String(20), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("orders", "offer_version")
    op.drop_column("orders", "offer_accepted_ip")
    op.drop_column("orders", "offer_accepted_at")
