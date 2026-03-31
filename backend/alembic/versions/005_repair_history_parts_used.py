"""repair_history: add parts_used JSON column

Revision ID: 005
Revises: 004
Create Date: 2026-03-31
"""
from alembic import op
import sqlalchemy as sa

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('repair_history', sa.Column('parts_used', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('repair_history', 'parts_used')
