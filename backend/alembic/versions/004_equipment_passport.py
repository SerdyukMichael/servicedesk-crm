"""equipment: add passport fields (manufacture_date, sale_date, warranty_start,
firmware_version) and extend status enum with 'transferred'

Revision ID: 004
Revises: 003
Create Date: 2026-03-31
"""
from alembic import op
import sqlalchemy as sa

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new date / varchar fields to equipment table
    op.add_column('equipment', sa.Column('manufacture_date', sa.Date(), nullable=True))
    op.add_column('equipment', sa.Column('sale_date', sa.Date(), nullable=True))
    op.add_column('equipment', sa.Column('warranty_start', sa.Date(), nullable=True))
    op.add_column('equipment', sa.Column('firmware_version', sa.String(64), nullable=True))

    # Extend the status ENUM to include 'transferred'.
    # MySQL requires re-specifying the full ENUM list; SQLite ignores ALTER COLUMN type.
    bind = op.get_bind()
    if bind.dialect.name == 'mysql':
        op.execute(
            "ALTER TABLE equipment MODIFY COLUMN status "
            "ENUM('active','in_repair','decommissioned','written_off','transferred') "
            "NOT NULL DEFAULT 'active'"
        )


def downgrade() -> None:
    op.drop_column('equipment', 'firmware_version')
    op.drop_column('equipment', 'warranty_start')
    op.drop_column('equipment', 'sale_date')
    op.drop_column('equipment', 'manufacture_date')

    bind = op.get_bind()
    if bind.dialect.name == 'mysql':
        op.execute(
            "ALTER TABLE equipment MODIFY COLUMN status "
            "ENUM('active','in_repair','decommissioned','written_off') "
            "NOT NULL DEFAULT 'active'"
        )
