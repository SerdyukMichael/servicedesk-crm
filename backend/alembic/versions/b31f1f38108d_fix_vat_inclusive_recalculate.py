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
    # Старая формула: total_amount = subtotal + vat (НДС сверху).
    # Новая формула:  total_amount = subtotal (сумма позиций, НДС внутри).
    # subtotal здесь — старое значение (= сумма позиций до ошибочного начисления).
    op.execute("""
        UPDATE invoices
        SET
            total_amount = subtotal,
            vat_amount   = ROUND(subtotal * vat_rate / (100 + vat_rate), 2),
            subtotal     = ROUND(subtotal - ROUND(subtotal * vat_rate / (100 + vat_rate), 2), 2)
        WHERE total_amount > subtotal
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
