"""tickets: add ticket_status_history table

Revision ID: 003
Revises: 002
Create Date: 2026-03-31
"""
from alembic import op
import sqlalchemy as sa

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ticket_status_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ticket_id', sa.Integer(), nullable=False),
        sa.Column('from_status', sa.String(32), nullable=True),
        sa.Column('to_status', sa.String(32), nullable=False),
        sa.Column('changed_by', sa.Integer(), nullable=True),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('changed_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['ticket_id'], ['tickets.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_tsh_ticket_id', 'ticket_id'),
    )


def downgrade() -> None:
    op.drop_table('ticket_status_history')
