"""equipment_models: add warranty_months_default column

Revision ID: 006
Revises: 005
Create Date: 2026-03-31
"""
from alembic import op
import sqlalchemy as sa

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'equipment_models',
        sa.Column('warranty_months_default', sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('equipment_models', 'warranty_months_default')
