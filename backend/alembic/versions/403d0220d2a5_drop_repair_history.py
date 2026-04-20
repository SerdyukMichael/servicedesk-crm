"""drop_repair_history

Revision ID: 403d0220d2a5
Revises: 012_system_settings
Create Date: 2026-04-20 16:34:21.048137

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '403d0220d2a5'
down_revision: Union[str, None] = '012_system_settings'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table('repair_history')


def downgrade() -> None:
    op.create_table(
        'repair_history',
        sa.Column('id', sa.Integer, primary_key=True, autoincrement=True),
        sa.Column('equipment_id', sa.Integer, sa.ForeignKey('equipment.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('ticket_id', sa.Integer, sa.ForeignKey('tickets.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action_type', sa.String(64), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('performed_by', sa.Integer, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('performed_at', sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column('parts_used', sa.JSON, nullable=True),
    )
