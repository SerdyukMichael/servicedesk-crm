"""fix_vat_inclusive_recalculate

Revision ID: b31f1f38108d
Revises: 011
Create Date: 2026-04-16 20:35:56.751401

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b31f1f38108d'
down_revision: Union[str, None] = '011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Пересчёт НДС "в т.ч." для всех существующих счетов.
    # Источник истины — сумма позиций (invoice_items.total).
    # Ставка меняется на 22%. total_amount = сумма позиций (не растёт).
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
    # Откат: вернуть старую формулу (НДС сверху).
    # total_amount было = subtotal_old + vat_old = subtotal_new + vat_new + vat_new
    # Проще: total_old = subtotal_new + vat_new (= текущий total_amount) — уже правильно для downgrade
    op.execute("""
        UPDATE invoices
        SET
            vat_amount   = ROUND(total_amount * vat_rate / 100, 2),
            subtotal     = total_amount,
            total_amount = ROUND(total_amount * (1 + vat_rate / 100), 2)
    """)
