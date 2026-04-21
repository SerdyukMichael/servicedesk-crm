"""create_exchange_rates

Revision ID: 630140d83c77
Revises: 403d0220d2a5
Create Date: 2026-04-21 09:47:26.602624

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '630140d83c77'
down_revision: Union[str, None] = '403d0220d2a5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'exchange_rates',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('rate', sa.DECIMAL(precision=15, scale=4), nullable=False),
        sa.Column('set_by', sa.Integer(), nullable=False),
        sa.Column('set_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['set_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_exchange_rates_currency'), 'exchange_rates', ['currency'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_exchange_rates_currency'), table_name='exchange_rates')
    op.drop_table('exchange_rates')
