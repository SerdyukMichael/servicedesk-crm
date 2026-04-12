"""product_catalog

Revision ID: 010
Revises: 6cd8b51a3e8b
Create Date: 2026-04-12

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = '010'
down_revision: Union[str, None] = '6cd8b51a3e8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Новая таблица product_catalog
    op.create_table(
        'product_catalog',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('code', sa.String(32), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category',
                  sa.Enum('spare_part', 'other', name='product_category_enum'),
                  nullable=False, server_default='other'),
        sa.Column('unit',
                  sa.Enum('pcs', 'pack', 'kit', name='product_unit_enum'),
                  nullable=False, server_default='pcs'),
        sa.Column('unit_price', sa.DECIMAL(12, 2), nullable=False, server_default='0'),
        sa.Column('currency', sa.String(3), nullable=False, server_default='RUB'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_product_catalog_code', 'product_catalog', ['code'], unique=True)

    # 2. Добавить product_id в work_act_items
    op.add_column('work_act_items',
        sa.Column('product_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_work_act_items_product_id', 'work_act_items',
        'product_catalog', ['product_id'], ['id'], ondelete='RESTRICT'
    )
    # 3. Расширить enum work_act_item_type_enum: добавить 'product'
    op.alter_column('work_act_items', 'item_type',
        existing_type=sa.Enum('service', 'part', name='work_act_item_type_enum'),
        type_=sa.Enum('service', 'part', 'product', name='work_act_item_type_enum'),
        existing_nullable=False,
    )

    # 4. Добавить product_id в invoice_items
    op.add_column('invoice_items',
        sa.Column('product_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_invoice_items_product_id', 'invoice_items',
        'product_catalog', ['product_id'], ['id'], ondelete='RESTRICT'
    )
    # 5. Расширить enum invoice_item_type_enum: добавить 'product'
    op.alter_column('invoice_items', 'item_type',
        existing_type=sa.Enum('service', 'part', 'manual', name='invoice_item_type_enum'),
        type_=sa.Enum('service', 'part', 'product', 'manual', name='invoice_item_type_enum'),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column('invoice_items', 'item_type',
        existing_type=sa.Enum('service', 'part', 'product', 'manual', name='invoice_item_type_enum'),
        type_=sa.Enum('service', 'part', 'manual', name='invoice_item_type_enum'),
        existing_nullable=True,
    )
    op.drop_constraint('fk_invoice_items_product_id', 'invoice_items', type_='foreignkey')
    op.drop_column('invoice_items', 'product_id')

    op.alter_column('work_act_items', 'item_type',
        existing_type=sa.Enum('service', 'part', 'product', name='work_act_item_type_enum'),
        type_=sa.Enum('service', 'part', name='work_act_item_type_enum'),
        existing_nullable=False,
    )
    op.drop_constraint('fk_work_act_items_product_id', 'work_act_items', type_='foreignkey')
    op.drop_column('work_act_items', 'product_id')

    op.drop_index('ix_product_catalog_code', table_name='product_catalog')
    op.drop_table('product_catalog')
