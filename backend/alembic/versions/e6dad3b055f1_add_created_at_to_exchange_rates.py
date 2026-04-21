"""add_created_at_to_exchange_rates

Revision ID: e6dad3b055f1
Revises: 630140d83c77
Create Date: 2026-04-21 11:36:59.331222

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'e6dad3b055f1'
down_revision: Union[str, None] = '630140d83c77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'exchange_rates',
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
    )


def downgrade() -> None:
    op.drop_column('exchange_rates', 'created_at')
