"""clients: contract_type VARCHAR, add city

Revision ID: 001
Revises:
Create Date: 2026-03-30
"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Change contract_type from ENUM to VARCHAR(64) — allows any string value
    op.alter_column(
        'clients', 'contract_type',
        existing_type=sa.Enum('none', 'standard', 'premium', name='contract_type_enum'),
        type_=sa.String(64),
        existing_nullable=False,
        server_default='none',
    )
    # Add city column
    op.add_column('clients', sa.Column('city', sa.String(128), nullable=True))


def downgrade() -> None:
    op.drop_column('clients', 'city')
    op.alter_column(
        'clients', 'contract_type',
        existing_type=sa.String(64),
        type_=sa.Enum('none', 'standard', 'premium', name='contract_type_enum'),
        existing_nullable=False,
        server_default='none',
    )
