"""force_vat_rate_22_all_invoices

Revision ID: 89b7f086cd94
Revises: d20b1718df8a
Create Date: 2026-04-17 13:47:44.934220

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '89b7f086cd94'
down_revision: Union[str, None] = 'd20b1718df8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Шаг 1: ставка 22% для всех счетов безусловно
    op.execute("UPDATE invoices SET vat_rate = 22.00")

    # Шаг 2: пересчёт для счетов с позициями (от суммы позиций)
    op.execute("""
        UPDATE invoices i
        JOIN (
            SELECT invoice_id, SUM(total) AS s
            FROM invoice_items
            GROUP BY invoice_id
        ) ii ON i.id = ii.invoice_id
        SET
            i.total_amount = ii.s,
            i.vat_amount   = ROUND(ii.s * 22 / 122, 2),
            i.subtotal     = ROUND(ii.s - ROUND(ii.s * 22 / 122, 2), 2)
    """)

    # Шаг 3: пересчёт для пустых счетов (нет позиций) — от total_amount
    op.execute("""
        UPDATE invoices i
        LEFT JOIN invoice_items ii ON ii.invoice_id = i.id
        SET
            i.vat_amount = ROUND(i.total_amount * 22 / 122, 2),
            i.subtotal   = ROUND(i.total_amount - ROUND(i.total_amount * 22 / 122, 2), 2)
        WHERE ii.invoice_id IS NULL
    """)


def downgrade() -> None:
    op.execute("UPDATE invoices SET vat_rate = 20.00")
    op.execute("""
        UPDATE invoices i
        JOIN (
            SELECT invoice_id, SUM(total) AS s
            FROM invoice_items
            GROUP BY invoice_id
        ) ii ON i.id = ii.invoice_id
        SET
            i.total_amount = ii.s,
            i.vat_amount   = ROUND(ii.s * 20 / 120, 2),
            i.subtotal     = ROUND(ii.s - ROUND(ii.s * 20 / 120, 2), 2)
    """)
