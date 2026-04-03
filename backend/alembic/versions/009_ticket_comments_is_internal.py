"""ticket_comments_is_internal

Revision ID: 009
Revises: 008
Create Date: 2026-04-02
"""
from alembic import op
import sqlalchemy as sa

revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ticket_comments",
        sa.Column("is_internal", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("ticket_comments", "is_internal")
