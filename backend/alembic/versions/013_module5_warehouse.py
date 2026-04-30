"""Module 5: warehouses, warehouse_stock, stock_receipts, parts_transfers, work_act_items.warehouse_id

Revision ID: 013_module5_warehouse
Revises: f1a2b3c4d5e6
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa

revision = "013_module5_warehouse"
down_revision = "b2c3d4e5f6a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # warehouses
    op.create_table(
        "warehouses",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.Enum("company", "bank", name="warehouse_type_enum"), nullable=False, server_default="company"),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
    )

    # warehouse_stock
    op.create_table(
        "warehouse_stock",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("part_id", sa.Integer(), sa.ForeignKey("spare_parts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("unit_price_snapshot", sa.DECIMAL(12, 2), nullable=True),
        sa.UniqueConstraint("warehouse_id", "part_id", name="uq_warehouse_part"),
    )

    # stock_receipts
    op.create_table(
        "stock_receipts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("receipt_number", sa.String(20), nullable=False, unique=True),
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("receipt_date", sa.Date(), nullable=False),
        sa.Column("vendor_id", sa.Integer(), sa.ForeignKey("vendors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("supplier_doc_number", sa.String(100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("draft", "posted", "cancelled", name="stock_receipt_status_enum"),
                  nullable=False, server_default="draft"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_stock_receipts_receipt_number", "stock_receipts", ["receipt_number"])

    # stock_receipt_items
    op.create_table(
        "stock_receipt_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("receipt_id", sa.Integer(), sa.ForeignKey("stock_receipts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("part_id", sa.Integer(), sa.ForeignKey("spare_parts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.DECIMAL(12, 2), nullable=False, server_default="0"),
    )

    # parts_transfers
    op.create_table(
        "parts_transfers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("transfer_number", sa.String(20), nullable=False, unique=True),
        sa.Column("from_warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("to_warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("transfer_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.Enum("draft", "posted", "cancelled", name="parts_transfer_status_enum"),
                  nullable=False, server_default="draft"),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("posted_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("posted_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_parts_transfers_transfer_number", "parts_transfers", ["transfer_number"])

    # parts_transfer_items
    op.create_table(
        "parts_transfer_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("transfer_id", sa.Integer(), sa.ForeignKey("parts_transfers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("part_id", sa.Integer(), sa.ForeignKey("spare_parts.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price_snapshot", sa.DECIMAL(12, 2), nullable=True),
    )

    # add warehouse_id to work_act_items
    op.add_column(
        "work_act_items",
        sa.Column("warehouse_id", sa.Integer(), sa.ForeignKey("warehouses.id", ondelete="SET NULL"), nullable=True),
    )

    # seed: create default company warehouse "Основной склад"
    op.execute(
        "INSERT INTO warehouses (name, type, client_id, is_active) VALUES ('Основной склад', 'company', NULL, 1)"
    )


def downgrade() -> None:
    op.drop_column("work_act_items", "warehouse_id")
    op.drop_table("parts_transfer_items")
    op.drop_index("ix_parts_transfers_transfer_number", "parts_transfers")
    op.drop_table("parts_transfers")
    op.drop_table("stock_receipt_items")
    op.drop_index("ix_stock_receipts_receipt_number", "stock_receipts")
    op.drop_table("stock_receipts")
    op.drop_table("warehouse_stock")
    op.drop_table("warehouses")
    op.execute("DROP TYPE IF EXISTS parts_transfer_status_enum")
    op.execute("DROP TYPE IF EXISTS stock_receipt_status_enum")
    op.execute("DROP TYPE IF EXISTS warehouse_type_enum")
