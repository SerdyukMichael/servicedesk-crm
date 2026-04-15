"""remove_product_catalog

Revision ID: 011
Revises: 010
Create Date: 2026-04-14

Изменения:
  - Удалить FK и колонку product_id из work_act_items
  - Откатить enum work_act_item_type_enum: 'service/part/product' -> 'service/part'
  - Удалить FK и колонку product_id из invoice_items
  - Откатить enum invoice_item_type_enum: 'service/part/product/manual' -> 'service/part/manual'
  - Удалить таблицу product_catalog
  - Добавить audit-поля в spare_parts (created_by, created_at, updated_at)
  - Создать таблицу price_history
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '011'
down_revision: Union[str, None] = '010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Убрать product_id из work_act_items
    op.drop_constraint('fk_work_act_items_product_id', 'work_act_items', type_='foreignkey')
    op.drop_column('work_act_items', 'product_id')

    # 2. Откатить enum work_act_item_type_enum: убрать 'product'
    op.alter_column(
        'work_act_items', 'item_type',
        existing_type=sa.Enum('service', 'part', 'product', name='work_act_item_type_enum'),
        type_=sa.Enum('service', 'part', name='work_act_item_type_enum'),
        existing_nullable=False,
    )

    # 3. Убрать product_id из invoice_items
    op.drop_constraint('fk_invoice_items_product_id', 'invoice_items', type_='foreignkey')
    op.drop_column('invoice_items', 'product_id')

    # 4. Откатить enum invoice_item_type_enum: убрать 'product'
    op.alter_column(
        'invoice_items', 'item_type',
        existing_type=sa.Enum('service', 'part', 'product', 'manual', name='invoice_item_type_enum'),
        type_=sa.Enum('service', 'part', 'manual', name='invoice_item_type_enum'),
        existing_nullable=True,
    )

    # 5. Удалить таблицу product_catalog
    op.drop_index('ix_product_catalog_code', table_name='product_catalog')
    op.drop_table('product_catalog')

    # 6. Добавить audit-поля в spare_parts
    op.add_column('spare_parts',
        sa.Column('created_by', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_spare_parts_created_by', 'spare_parts',
        'users', ['created_by'], ['id'], ondelete='SET NULL',
    )
    op.add_column('spare_parts',
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')))
    op.add_column('spare_parts',
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')))

    # 7. Создать таблицу price_history
    op.create_table(
        'price_history',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('entity_type',
                  sa.Enum('service', 'spare_part', name='price_history_entity_type_enum'),
                  nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('old_price', sa.DECIMAL(12, 2), nullable=False),
        sa.Column('new_price', sa.DECIMAL(12, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, server_default='RUB'),
        sa.Column('reason', sa.String(512), nullable=False),
        sa.Column('changed_by', sa.Integer(), nullable=False),
        sa.Column('changed_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_price_history_entity', 'price_history',
                    ['entity_type', 'entity_id'])


def downgrade() -> None:
    op.drop_index('ix_price_history_entity', table_name='price_history')
    op.drop_table('price_history')

    op.drop_constraint('fk_spare_parts_created_by', 'spare_parts', type_='foreignkey')
    op.drop_column('spare_parts', 'updated_at')
    op.drop_column('spare_parts', 'created_at')
    op.drop_column('spare_parts', 'created_by')

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

    op.alter_column(
        'invoice_items', 'item_type',
        existing_type=sa.Enum('service', 'part', 'manual', name='invoice_item_type_enum'),
        type_=sa.Enum('service', 'part', 'product', 'manual', name='invoice_item_type_enum'),
        existing_nullable=True,
    )
    op.add_column('invoice_items',
        sa.Column('product_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_invoice_items_product_id', 'invoice_items',
        'product_catalog', ['product_id'], ['id'], ondelete='RESTRICT',
    )

    op.alter_column(
        'work_act_items', 'item_type',
        existing_type=sa.Enum('service', 'part', name='work_act_item_type_enum'),
        type_=sa.Enum('service', 'part', 'product', name='work_act_item_type_enum'),
        existing_nullable=False,
    )
    op.add_column('work_act_items',
        sa.Column('product_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_work_act_items_product_id', 'work_act_items',
        'product_catalog', ['product_id'], ['id'], ondelete='RESTRICT',
    )
