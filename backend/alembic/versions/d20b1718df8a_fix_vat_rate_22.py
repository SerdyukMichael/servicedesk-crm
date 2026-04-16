"""fix_vat_rate_22

Revision ID: d20b1718df8a
Revises: b31f1f38108d
Create Date: 2026-04-16 20:51:38.546326

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd20b1718df8a'
down_revision: Union[str, None] = 'b31f1f38108d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Обновить ставку НДС на 22% и пересчитать суммы от invoice_items.
    op.execute("""
        UPDATE invoices i
        JOIN (
            SELECT invoice_id, SUM(total) AS items_total
            FROM invoice_items
            GROUP BY invoice_id
        ) ii ON i.id = ii.invoice_id
        SET
            i.vat_rate     = 22.00,
            i.total_amount = ii.items_total,
            i.vat_amount   = ROUND(ii.items_total * 22 / 122, 2),
            i.subtotal     = ROUND(ii.items_total - ROUND(ii.items_total * 22 / 122, 2), 2)
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE invoices i
        JOIN (
            SELECT invoice_id, SUM(total) AS items_total
            FROM invoice_items
            GROUP BY invoice_id
        ) ii ON i.id = ii.invoice_id
        SET
            i.vat_rate     = 20.00,
            i.total_amount = ii.items_total,
            i.vat_amount   = ROUND(ii.items_total * 20 / 120, 2),
            i.subtotal     = ROUND(ii.items_total - ROUND(ii.items_total * 20 / 120, 2), 2)
    """)
