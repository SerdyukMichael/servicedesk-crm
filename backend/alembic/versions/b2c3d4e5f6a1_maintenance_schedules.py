"""maintenance_schedules

Revision ID: b2c3d4e5f6a1
Revises: a1b2c3d4e5f6
Create Date: 2026-04-24 10:02:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision: str = 'b2c3d4e5f6a1'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if 'maintenance_schedules' in inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        'maintenance_schedules',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('equipment_id', sa.Integer(), nullable=False),
        sa.Column('frequency', sa.Enum('monthly', 'quarterly', 'semiannual', 'annual',
                                       name='maintenance_frequency_enum'), nullable=False),
        sa.Column('first_date', sa.Date(), nullable=False),
        sa.Column('next_date', sa.Date(), nullable=False),
        sa.Column('last_ticket_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('NOW()'), nullable=False),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['last_ticket_id'], ['tickets.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_maintenance_schedules_equipment_id', 'maintenance_schedules', ['equipment_id'])
    op.create_index('ix_maintenance_schedules_next_date', 'maintenance_schedules', ['next_date'])
    op.create_index('ix_maint_active_next', 'maintenance_schedules', ['is_active', 'next_date'])


def downgrade() -> None:
    op.drop_index('ix_maint_active_next', table_name='maintenance_schedules')
    op.drop_index('ix_maintenance_schedules_next_date', table_name='maintenance_schedules')
    op.drop_index('ix_maintenance_schedules_equipment_id', table_name='maintenance_schedules')
    op.drop_table('maintenance_schedules')
    op.execute("DROP TYPE IF EXISTS maintenance_frequency_enum")
