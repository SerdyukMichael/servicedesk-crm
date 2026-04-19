"""012_system_settings

Revision ID: 012_system_settings
Revises: 6cd8b51a3e8b
Create Date: 2026-04-19

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime

revision = '012_system_settings'
down_revision = '89b7f086cd94'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'system_settings',
        sa.Column('key', sa.String(64), primary_key=True),
        sa.Column('value', sa.String(255), nullable=False),
        sa.Column('updated_at', sa.DateTime, nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('updated_by', sa.Integer, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
    )
    op.execute(
        "INSERT INTO system_settings (`key`, value) VALUES "
        "('currency_code', 'RUB'), "
        "('currency_name', 'Российский рубль')"
    )


def downgrade():
    op.drop_table('system_settings')
