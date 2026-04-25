"""ticket_sla_fields

Revision ID: f1a2b3c4d5e6
Revises: e6dad3b055f1
Create Date: 2026-04-24 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'e6dad3b055f1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tickets', sa.Column('assigned_at', sa.DateTime(), nullable=True))
    op.add_column('tickets', sa.Column('sla_reaction_deadline', sa.DateTime(), nullable=True))
    op.add_column('tickets', sa.Column('sla_resolution_deadline', sa.DateTime(), nullable=True))
    op.add_column('tickets', sa.Column('sla_reaction_violated', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('tickets', sa.Column('sla_resolution_violated', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('tickets', sa.Column('sla_reaction_escalated_at', sa.DateTime(), nullable=True))
    op.add_column('tickets', sa.Column('sla_resolution_escalated_at', sa.DateTime(), nullable=True))
    op.create_index('ix_tickets_sla_reaction_deadline', 'tickets', ['sla_reaction_deadline'])
    op.create_index('ix_tickets_sla_resolution_deadline', 'tickets', ['sla_resolution_deadline'])


def downgrade() -> None:
    op.drop_index('ix_tickets_sla_resolution_deadline', table_name='tickets')
    op.drop_index('ix_tickets_sla_reaction_deadline', table_name='tickets')
    op.drop_column('tickets', 'sla_resolution_escalated_at')
    op.drop_column('tickets', 'sla_reaction_escalated_at')
    op.drop_column('tickets', 'sla_resolution_violated')
    op.drop_column('tickets', 'sla_reaction_violated')
    op.drop_column('tickets', 'sla_resolution_deadline')
    op.drop_column('tickets', 'sla_reaction_deadline')
    op.drop_column('tickets', 'assigned_at')
