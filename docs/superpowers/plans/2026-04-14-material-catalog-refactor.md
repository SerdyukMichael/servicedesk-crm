# Material Catalog Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Удалить `product_catalog` как отдельную сущность — единым каталогом матценностей становится `spare_parts`; добавить `price_history` для истории цен; обновить формы акта/счёта — выбор только из spare_parts с ценой (BR-F-122).

**Architecture:** Таблица `product_catalog` удаляется вместе с FK из `work_act_items` и `invoice_items`. Новая таблица `price_history` хранит историю цен для `service_catalog` (entity_type='service') и `spare_parts` (entity_type='spare_part'). Эндпоинт `/parts` расширяется фильтром `has_price` и операциями управления ценой. Фронтенд: удалить страницу товаров, добавить UI цены в страницу склада, фильтровать запчасти в форме акта.

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy 2.0 / Alembic / MySQL 8.0 / pytest+httpx / React+TypeScript / Docker Compose

---

## Карта файлов

| Действие | Файл |
|---|---|
| CREATE | `backend/alembic/versions/011_remove_product_catalog.py` |
| MODIFY | `backend/app/models/__init__.py` |
| MODIFY | `backend/app/schemas/__init__.py` |
| DELETE | `backend/app/api/endpoints/product_catalog.py` |
| MODIFY | `backend/app/api/router.py` |
| MODIFY | `backend/app/api/endpoints/parts.py` |
| DELETE | `backend/tests/test_product_catalog.py` |
| MODIFY | `backend/tests/conftest.py` |
| CREATE | `backend/tests/test_parts_price.py` |
| DELETE | `frontend/src/pages/ProductCatalogPage.tsx` |
| DELETE | `frontend/src/hooks/useProductCatalog.ts` |
| MODIFY | `frontend/src/App.tsx` |
| MODIFY | `frontend/src/components/Layout.tsx` |
| MODIFY | `frontend/src/api/types.ts` |
| MODIFY | `frontend/src/api/endpoints.ts` |
| MODIFY | `frontend/src/pages/PartsPage.tsx` |
| MODIFY | `frontend/src/pages/TicketDetailPage.tsx` |

---

## Task 1: Миграция БД (011)

**Files:**
- Create: `backend/alembic/versions/011_remove_product_catalog.py`

- [ ] **Step 1: Написать миграцию**

Создать файл `backend/alembic/versions/011_remove_product_catalog.py`:

```python
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
from datetime import datetime
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
                  server_default=sa.text('NOW()'),
                  comment='AUTO UPDATE via application'))

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
```

- [ ] **Step 2: Применить миграцию**

```bash
docker compose exec backend alembic upgrade head
```

Ожидаемый вывод: `Running upgrade 010 -> 011, remove_product_catalog`

---

## Task 2: Backend Models

**Files:**
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1: Удалить класс ProductCatalog и его связи**

Убрать весь блок `# ── Product Catalog ───` (строки ~329-351 с классом `ProductCatalog`).

Убрать из класса `WorkActItem`:
- поле `product_id` (строка с `ForeignKey("product_catalog.id", ...)`)
- relationship `product` (строка `product: Mapped[Optional["ProductCatalog"]] = ...`)

Убрать из класса `InvoiceItem`:
- поле `product_id` (строка с `ForeignKey("product_catalog.id", ...)`)

- [ ] **Step 2: Исправить enum WorkActItem**

```python
# ── Work Act Items ────────────────────────────────────────────────────────────
class WorkActItem(Base):
    __tablename__ = "work_act_items"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_act_id: Mapped[int]           = mapped_column(ForeignKey("work_acts.id", ondelete="CASCADE"), nullable=False)
    item_type:   Mapped[str]           = mapped_column(
        Enum("service", "part", name="work_act_item_type_enum"),
        nullable=False
    )
    service_id:  Mapped[Optional[int]] = mapped_column(ForeignKey("service_catalog.id", ondelete="RESTRICT"), nullable=True)
    part_id:     Mapped[Optional[int]] = mapped_column(ForeignKey("spare_parts.id", ondelete="RESTRICT"), nullable=True)
    name:        Mapped[str]           = mapped_column(String(255), nullable=False)
    quantity:    Mapped[Decimal]       = mapped_column(DECIMAL(10, 3), nullable=False, default=1)
    unit:        Mapped[str]           = mapped_column(String(16), nullable=False, default="шт")
    unit_price:  Mapped[Decimal]       = mapped_column(DECIMAL(12, 2), nullable=False, default=0)
    total:       Mapped[Decimal]       = mapped_column(DECIMAL(14, 2), nullable=False, default=0)
    sort_order:  Mapped[int]           = mapped_column(Integer, default=0, nullable=False)

    work_act: Mapped["WorkAct"]                  = relationship("WorkAct", back_populates="items")
    service:  Mapped[Optional["ServiceCatalog"]] = relationship("ServiceCatalog", back_populates="work_act_items")
    part:     Mapped[Optional["SparePart"]]      = relationship("SparePart")
```

- [ ] **Step 3: Исправить enum InvoiceItem**

```python
# ── Invoice Items ─────────────────────────────────────────────────────────────
class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id:  Mapped[int]           = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str]           = mapped_column(String(512), nullable=False)
    quantity:    Mapped[Decimal]       = mapped_column(DECIMAL(10, 3), default=1, nullable=False)
    unit:        Mapped[str]           = mapped_column(String(16), default="шт", nullable=False)
    unit_price:  Mapped[Decimal]       = mapped_column(DECIMAL(12, 2), nullable=False)
    total:       Mapped[Decimal]       = mapped_column(DECIMAL(14, 2), nullable=False)
    sort_order:  Mapped[int]           = mapped_column(Integer, default=0, nullable=False)
    item_type:   Mapped[Optional[str]] = mapped_column(
        Enum("service", "part", "manual", name="invoice_item_type_enum"),
        nullable=True
    )
    service_id:  Mapped[Optional[int]] = mapped_column(ForeignKey("service_catalog.id", ondelete="RESTRICT"), nullable=True)
    part_id:     Mapped[Optional[int]] = mapped_column(ForeignKey("spare_parts.id", ondelete="RESTRICT"), nullable=True)

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="items")
```

- [ ] **Step 4: Добавить audit-поля в SparePart**

```python
# ── Spare Parts ───────────────────────────────────────────────────────────────
class SparePart(Base):
    __tablename__ = "spare_parts"

    id:           Mapped[int]             = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku:          Mapped[str]             = mapped_column(String(64), unique=True, nullable=False, index=True)
    name:         Mapped[str]             = mapped_column(String(255), nullable=False)
    category:     Mapped[Optional[str]]   = mapped_column(String(64))
    unit:         Mapped[str]             = mapped_column(String(16), default="шт", nullable=False)
    quantity:     Mapped[int]             = mapped_column(Integer, default=0, nullable=False)
    min_quantity: Mapped[int]             = mapped_column(Integer, default=0, nullable=False)
    unit_price:   Mapped[Decimal]         = mapped_column(DECIMAL(12, 2), nullable=False, default=0)
    currency:     Mapped[str]             = mapped_column(String(3), default="RUB", nullable=False)
    vendor_id:    Mapped[Optional[int]]   = mapped_column(ForeignKey("vendors.id", ondelete="SET NULL"))
    description:  Mapped[Optional[str]]   = mapped_column(Text)
    is_active:    Mapped[bool]            = mapped_column(Boolean, default=True, nullable=False)
    created_by:   Mapped[Optional[int]]   = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at:   Mapped[datetime]        = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at:   Mapped[datetime]        = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor", back_populates="spare_parts")
```

- [ ] **Step 5: Добавить модель PriceHistory**

Добавить после класса `SparePart`:

```python
# ── Price History ─────────────────────────────────────────────────────────────
class PriceHistory(Base):
    __tablename__ = "price_history"

    id:          Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    entity_type: Mapped[str]      = mapped_column(
        Enum("service", "spare_part", name="price_history_entity_type_enum"),
        nullable=False
    )
    entity_id:   Mapped[int]      = mapped_column(Integer, nullable=False, index=True)
    old_price:   Mapped[Decimal]  = mapped_column(DECIMAL(12, 2), nullable=False)
    new_price:   Mapped[Decimal]  = mapped_column(DECIMAL(12, 2), nullable=False)
    currency:    Mapped[str]      = mapped_column(String(3), default="RUB", nullable=False)
    reason:      Mapped[str]      = mapped_column(String(512), nullable=False)
    changed_by:  Mapped[int]      = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    changed_at:  Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    changer: Mapped["User"] = relationship("User")
```

---

## Task 3: Backend Schemas

**Files:**
- Modify: `backend/app/schemas/__init__.py`

- [ ] **Step 1: Удалить ProductCatalog-схемы**

Найти и удалить весь блок `# ── Product Catalog ───` (~строки 819-860) с классами:
- `ProductCatalogCreate`
- `ProductCatalogUpdate`
- `ProductCatalogResponse`

- [ ] **Step 2: Обновить WorkActItemCreate и WorkActItemResponse — убрать product_id**

```python
class WorkActItemCreate(BaseModel):
    item_type: str  # "service" | "part"
    service_id: Optional[int] = None
    part_id: Optional[int] = None
    name: str
    quantity: Decimal = Decimal("1")
    unit: str = "шт"
    unit_price: Decimal = Decimal("0")
    sort_order: int = 0


class WorkActItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    work_act_id: int
    item_type: str
    service_id: Optional[int]
    part_id: Optional[int]
    name: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    total: Decimal
    sort_order: int
```

- [ ] **Step 3: Обновить InvoiceItemCreate и InvoiceItemResponse — убрать product_id**

```python
class InvoiceItemCreate(BaseModel):
    description: str
    quantity: Decimal = Decimal("1")
    unit: str = "шт"
    unit_price: Decimal
    sort_order: int = 0
    item_type: Optional[str] = None   # "service" | "part" | "manual"
    service_id: Optional[int] = None
    part_id: Optional[int] = None


class InvoiceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    description: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    total: Decimal
    sort_order: int
    item_type: Optional[str] = None
    service_id: Optional[int] = None
    part_id: Optional[int] = None
```

- [ ] **Step 4: Добавить SparePartPriceUpdate и PriceHistoryResponse**

Добавить в раздел `# ── Spare Parts ───` после `SparePartResponse`:

```python
class SparePartPriceUpdate(BaseModel):
    new_price: Decimal
    currency: str = "RUB"
    reason: str

    @field_validator("new_price")
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Цена не может быть отрицательной")
        return v

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if len(v.strip()) < 5:
            raise ValueError("Причина должна содержать минимум 5 символов")
        return v


class PriceHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    old_price: Decimal
    new_price: Decimal
    currency: str
    reason: str
    changed_by: int
    changed_at: datetime
```

---

## Task 4: Очистка старого backend-кода

**Files:**
- Delete: `backend/app/api/endpoints/product_catalog.py`
- Delete: `backend/tests/test_product_catalog.py`
- Modify: `backend/app/api/router.py`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Удалить файл product_catalog.py**

```bash
rm backend/app/api/endpoints/product_catalog.py
```

- [ ] **Step 2: Удалить файл test_product_catalog.py**

```bash
rm backend/tests/test_product_catalog.py
```

- [ ] **Step 3: Убрать product_catalog из router.py**

Найти строки в `backend/app/api/router.py`:
```python
from app.api.endpoints import product_catalog
...
api_router.include_router(product_catalog.router, prefix="/product-catalog", tags=["Каталог товаров"])
```

Удалить обе строки.

- [ ] **Step 4: Обновить conftest.py — убрать ProductCatalog**

В строке импорта в conftest.py заменить:
```python
from app.models import User, Client, Equipment, EquipmentModel, Ticket, SparePart, Vendor, WorkTemplate, WorkTemplateStep, NotificationSetting, ServiceCatalog  # noqa: E402
```

Оставить как есть — `ProductCatalog` там не импортирован явно (используется только в `make_product_catalog_item` через локальный `from app.models import ProductCatalog`).

Удалить функцию `make_product_catalog_item` (~строки 206-224).

- [ ] **Step 5: Проверить что существующие тесты проходят**

```bash
docker compose exec backend pytest tests/ -v
```

Ожидаемый вывод: все тесты PASSED (test_product_catalog.py удалён, остальные зелёные).

- [ ] **Step 6: Коммит**

```bash
git add backend/
git commit -m "refactor: remove product_catalog, add price_history model+migration"
```

---

## Task 5: Тесты для управления ценами (TDD — сначала failing)

**Files:**
- Create: `backend/tests/test_parts_price.py`

- [ ] **Step 1: Написать тесты**

Создать файл `backend/tests/test_parts_price.py`:

```python
"""
Тесты для управления ценами матценностей (UC-102, BR-F-121, BR-F-122).
"""
import pytest
from decimal import Decimal

from tests.conftest import (
    make_admin, make_svc_mgr, make_engineer, make_spare_part,
    auth_headers, make_user,
)


class TestHasPriceFilter:
    """GET /api/v1/parts?has_price=true — возвращать только позиции с unit_price > 0."""

    def test_has_price_false_by_default(self, client, db):
        admin = make_admin(db)
        make_spare_part(db, sku="P-001", quantity=5)   # price=100 (из фабрики)
        p0 = make_spare_part(db, sku="P-002", quantity=3)  # цена = 0 подставим вручную
        p0.unit_price = Decimal("0")
        db.commit()

        resp = client.get("/api/v1/parts", headers=auth_headers(admin.id, admin.roles))
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        # оба должны быть в списке по умолчанию
        assert p0.id in ids

    def test_has_price_true_excludes_zero_price(self, client, db):
        admin = make_admin(db)
        priced = make_spare_part(db, sku="P-003", quantity=5)  # price=100 из фабрики
        no_price = make_spare_part(db, sku="P-004", quantity=3)
        no_price.unit_price = Decimal("0")
        db.commit()

        resp = client.get(
            "/api/v1/parts",
            params={"has_price": True},
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert priced.id in ids
        assert no_price.id not in ids

    def test_has_price_true_includes_nonzero(self, client, db):
        admin = make_admin(db)
        p = make_spare_part(db, sku="P-005", quantity=1)  # unit_price=100 из фабрики
        assert p.unit_price == Decimal("100.00")

        resp = client.get(
            "/api/v1/parts",
            params={"has_price": True},
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200
        ids = [i["id"] for i in resp.json()["items"]]
        assert p.id in ids


class TestSetPartPrice:
    """PATCH /api/v1/parts/{id}/price — установить/изменить цену матценности."""

    def test_admin_can_set_price(self, client, db):
        admin = make_admin(db)
        part = make_spare_part(db, sku="X-001", quantity=5)
        # установим нулевую цену через ORM
        part.unit_price = Decimal("0")
        db.commit()

        resp = client.patch(
            f"/api/v1/parts/{part.id}/price",
            json={"new_price": "1500.00", "currency": "RUB", "reason": "Первичная установка цены"},
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert Decimal(data["unit_price"]) == Decimal("1500.00")
        assert data["currency"] == "RUB"

    def test_svc_mgr_can_set_price(self, client, db):
        mgr = make_svc_mgr(db)
        part = make_spare_part(db, sku="X-002", quantity=5)
        part.unit_price = Decimal("0")
        db.commit()

        resp = client.patch(
            f"/api/v1/parts/{part.id}/price",
            json={"new_price": "900.00", "currency": "RUB", "reason": "Плановое обновление цены"},
            headers=auth_headers(mgr.id, mgr.roles),
        )
        assert resp.status_code == 200

    def test_engineer_cannot_set_price(self, client, db):
        eng = make_engineer(db)
        part = make_spare_part(db, sku="X-003", quantity=5)

        resp = client.patch(
            f"/api/v1/parts/{part.id}/price",
            json={"new_price": "500.00", "currency": "RUB", "reason": "Попытка без прав"},
            headers=auth_headers(eng.id, eng.roles),
        )
        assert resp.status_code == 403

    def test_negative_price_rejected(self, client, db):
        admin = make_admin(db)
        part = make_spare_part(db, sku="X-004", quantity=5)

        resp = client.patch(
            f"/api/v1/parts/{part.id}/price",
            json={"new_price": "-10.00", "currency": "RUB", "reason": "Ошибочная цена"},
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 422

    def test_short_reason_rejected(self, client, db):
        admin = make_admin(db)
        part = make_spare_part(db, sku="X-005", quantity=5)

        resp = client.patch(
            f"/api/v1/parts/{part.id}/price",
            json={"new_price": "100.00", "currency": "RUB", "reason": "ab"},
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 422

    def test_set_price_creates_history_record(self, client, db):
        admin = make_admin(db)
        part = make_spare_part(db, sku="X-006", quantity=5)
        old_price = part.unit_price  # 100.00 из фабрики

        resp = client.patch(
            f"/api/v1/parts/{part.id}/price",
            json={"new_price": "2000.00", "currency": "RUB", "reason": "Обновление прайса поставщика"},
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200

        # Проверяем историю
        hist_resp = client.get(
            f"/api/v1/parts/{part.id}/price-history",
            headers=auth_headers(admin.id, admin.roles),
        )
        assert hist_resp.status_code == 200
        history = hist_resp.json()
        assert len(history) == 1
        assert Decimal(history[0]["old_price"]) == old_price
        assert Decimal(history[0]["new_price"]) == Decimal("2000.00")
        assert history[0]["reason"] == "Обновление прайса поставщика"
        assert history[0]["changed_by"] == admin.id

    def test_part_not_found_returns_404(self, client, db):
        admin = make_admin(db)
        resp = client.patch(
            "/api/v1/parts/99999/price",
            json={"new_price": "100.00", "currency": "RUB", "reason": "Тест не найдено"},
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 404


class TestPriceHistory:
    """GET /api/v1/parts/{id}/price-history — получить историю цен."""

    def test_empty_history(self, client, db):
        admin = make_admin(db)
        part = make_spare_part(db, sku="H-001", quantity=5)

        resp = client.get(
            f"/api/v1/parts/{part.id}/price-history",
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200
        assert resp.json() == []

    def test_history_sorted_newest_first(self, client, db):
        admin = make_admin(db)
        part = make_spare_part(db, sku="H-002", quantity=5)
        part.unit_price = Decimal("0")
        db.commit()

        # Первая установка
        client.patch(
            f"/api/v1/parts/{part.id}/price",
            json={"new_price": "100.00", "currency": "RUB", "reason": "Первая установка цены"},
            headers=auth_headers(admin.id, admin.roles),
        )
        # Вторая установка
        client.patch(
            f"/api/v1/parts/{part.id}/price",
            json={"new_price": "200.00", "currency": "RUB", "reason": "Повторная установка цены"},
            headers=auth_headers(admin.id, admin.roles),
        )

        resp = client.get(
            f"/api/v1/parts/{part.id}/price-history",
            headers=auth_headers(admin.id, admin.roles),
        )
        assert resp.status_code == 200
        history = resp.json()
        assert len(history) == 2
        # Новейшая запись первая
        assert Decimal(history[0]["new_price"]) == Decimal("200.00")
        assert Decimal(history[1]["new_price"]) == Decimal("100.00")

    def test_engineer_can_view_history(self, client, db):
        eng = make_engineer(db)
        part = make_spare_part(db, sku="H-003", quantity=5)

        resp = client.get(
            f"/api/v1/parts/{part.id}/price-history",
            headers=auth_headers(eng.id, eng.roles),
        )
        assert resp.status_code == 200

    def test_client_user_cannot_view_history(self, client, db):
        cu = make_user(db, email="cu@test.com", roles=["client_user"])
        part = make_spare_part(db, sku="H-004", quantity=5)

        resp = client.get(
            f"/api/v1/parts/{part.id}/price-history",
            headers=auth_headers(cu.id, cu.roles),
        )
        assert resp.status_code == 403
```

- [ ] **Step 2: Запустить тесты — убедиться что они FAIL**

```bash
docker compose exec backend pytest tests/test_parts_price.py -v
```

Ожидаемый вывод: `FAILED` (404 на PATCH /price и GET /price-history — эндпоинты не реализованы).

---

## Task 6: Реализовать эндпоинты управления ценами

**Files:**
- Modify: `backend/app/api/endpoints/parts.py`

- [ ] **Step 1: Обновить импорты в parts.py**

```python
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import SparePart, PriceHistory, User
from app.api.deps import get_current_user, require_roles, get_client_scope
from app.schemas import (
    SparePartCreate, SparePartUpdate, SparePartResponse,
    SparePartPriceUpdate, PriceHistoryResponse,
    StockAdjust, PaginatedResponse,
)

router = APIRouter()

_PRICE_ROLES = ("admin", "svc_mgr")
_WRITE_ROLES = ("admin", "warehouse")
_ADMIN = ("admin",)
```

- [ ] **Step 2: Добавить has_price в list_parts**

Найти в `list_parts` строку:
```python
def list_parts(
    category: Optional[str] = Query(None),
    low_stock: bool = Query(False),
```

Заменить сигнатуру и добавить фильтрацию:

```python
@router.get("", response_model=PaginatedResponse[SparePartResponse])
def list_parts(
    category: Optional[str] = Query(None),
    low_stock: bool = Query(False),
    has_price: bool = Query(False),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    if client_scope is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Нет доступа к складу запчастей"},
        )
    q = db.query(SparePart).filter(SparePart.is_active.is_(True))
    if category:
        q = q.filter(SparePart.category == category)
    if low_stock:
        q = q.filter(SparePart.quantity <= SparePart.min_quantity)
    if has_price:
        q = q.filter(SparePart.unit_price > 0)
    total = q.count()
    skip = (page - 1) * size
    items = q.order_by(SparePart.name).offset(skip).limit(size).all()
    pages = max(1, (total + size - 1) // size)
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)
```

- [ ] **Step 3: Добавить PATCH /{part_id}/price**

Добавить после `adjust_stock`:

```python
@router.patch("/{part_id}/price", response_model=SparePartResponse)
def set_part_price(
    part_id: int,
    data: SparePartPriceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_PRICE_ROLES)),
):
    """Установить / изменить цену матценности. Создаёт запись в price_history."""
    part = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Запчасть не найдена"},
        )
    history = PriceHistory(
        entity_type="spare_part",
        entity_id=part_id,
        old_price=part.unit_price,
        new_price=data.new_price,
        currency=data.currency,
        reason=data.reason,
        changed_by=current_user.id,
    )
    db.add(history)
    part.unit_price = data.new_price
    part.currency = data.currency
    db.commit()
    db.refresh(part)
    return part


@router.get("/{part_id}/price-history", response_model=List[PriceHistoryResponse])
def get_part_price_history(
    part_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    """Получить историю изменений цены матценности."""
    if client_scope is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Нет доступа"},
        )
    part = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Запчасть не найдена"},
        )
    history = (
        db.query(PriceHistory)
        .filter(
            PriceHistory.entity_type == "spare_part",
            PriceHistory.entity_id == part_id,
        )
        .order_by(PriceHistory.changed_at.desc())
        .all()
    )
    return history
```

- [ ] **Step 4: Запустить новые тесты — убедиться что они PASS**

```bash
docker compose exec backend pytest tests/test_parts_price.py -v
```

Ожидаемый вывод: все тесты `PASSED`.

- [ ] **Step 5: Запустить полный test suite**

```bash
docker compose exec backend pytest tests/ -v
```

Ожидаемый вывод: все тесты `PASSED`, нет `FAILED`.

- [ ] **Step 6: Коммит**

```bash
git add backend/
git commit -m "feat: add price management for spare_parts (PATCH price, GET price-history, has_price filter)"
```

---

## Task 7: Frontend — удаление ProductCatalog

**Files:**
- Delete: `frontend/src/pages/ProductCatalogPage.tsx`
- Delete: `frontend/src/hooks/useProductCatalog.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Step 1: Удалить ProductCatalogPage.tsx**

```bash
rm frontend/src/pages/ProductCatalogPage.tsx
```

- [ ] **Step 2: Удалить useProductCatalog.ts**

```bash
# Проверить существование
ls frontend/src/hooks/useProductCatalog.ts 2>/dev/null && rm frontend/src/hooks/useProductCatalog.ts || echo "not found"
```

- [ ] **Step 3: Обновить App.tsx — убрать ProductCatalogPage**

Убрать из `frontend/src/App.tsx`:
```tsx
import ProductCatalogPage from './pages/ProductCatalogPage'
```

Убрать маршрут:
```tsx
{/* Product Catalog */}
<Route path="product-catalog" element={<ProductCatalogPage />} />
```

- [ ] **Step 4: Обновить Layout.tsx — убрать «Товары»**

В массиве `NAV_ITEMS` убрать строку:
```tsx
{ to: '/product-catalog', icon: '📦', label: 'Товары' },
```

---

## Task 8: Frontend — типы и API

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/endpoints.ts`

- [ ] **Step 1: Обновить types.ts**

Удалить типы:
- `ProductCategory`
- `ProductUnit`
- `ProductCatalogItem`
- `ProductCatalogCreate`
- `ProductCatalogUpdate`
- поле `product_id?: number` из `WorkActItem` и `WorkActItemCreate`

Добавить:
```typescript
// ===== Price History =====
export interface PriceHistoryEntry {
  id: number
  entity_type: 'service' | 'spare_part'
  entity_id: number
  old_price: string
  new_price: string
  currency: string
  reason: string
  changed_by: number
  changed_at: string
}

export interface SparePartPriceUpdate {
  new_price: string
  currency: string
  reason: string
}
```

Обновить `WorkActItemCreate` — убрать `product_id`:
```typescript
export interface WorkActItemCreate {
  item_type: WorkActItemType
  service_id?: number
  part_id?: number
  name: string
  quantity: string | number
  unit: string
  unit_price: string | number
  sort_order?: number
}
```

Обновить `InvoiceItem` / inline invoice item — убрать `product_id`.

- [ ] **Step 2: Обновить endpoints.ts**

Удалить импорты ProductCatalog:
```typescript
// Удалить:
ProductCatalogItem,
ProductCatalogCreate,
ProductCatalogUpdate,
```

Удалить `productCatalogApi` (весь блок ~строки 320-336).

Добавить в `partsApi` методы цены:
```typescript
export const partsApi = {
  list: (params?: { category?: string; low_stock?: boolean; has_price?: boolean; page?: number; size?: number }) =>
    api.get<PaginatedResponse<SparePart>>('/parts', { params }),

  get: (id: number) =>
    api.get<SparePart>(`/parts/${id}`),

  create: (data: Partial<SparePart>) =>
    api.post<SparePart>('/parts', data),

  update: (id: number, data: Partial<SparePart>) =>
    api.put<SparePart>(`/parts/${id}`, data),

  adjustStock: (id: number, delta: number, reason?: string) =>
    api.post<SparePart>(`/parts/${id}/adjust`, { delta, reason }),

  setPrice: (id: number, data: SparePartPriceUpdate) =>
    api.patch<SparePart>(`/parts/${id}/price`, data),

  getPriceHistory: (id: number) =>
    api.get<PriceHistoryEntry[]>(`/parts/${id}/price-history`),
}
```

(импортировать `SparePartPriceUpdate` и `PriceHistoryEntry` из types.ts)

---

## Task 9: Frontend — PartsPage с управлением ценами

**Files:**
- Modify: `frontend/src/pages/PartsPage.tsx`

- [ ] **Step 1: Написать обновлённый PartsPage.tsx**

Полный код страницы с новой колонкой «Цена» + кнопка «Установить цену» / «Изменить цену» + модальное окно + модальное окно истории:

```tsx
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParts, useAdjustQuantity } from '../hooks/useParts'
import Pagination from '../components/Pagination'
import { partsApi } from '../api/endpoints'
import type { SparePart, SparePartPriceUpdate, PriceHistoryEntry } from '../api/types'
import { useAuth } from '../context/AuthContext'

export default function PartsPage() {
  const { hasRole } = useAuth()
  const canManagePrice = hasRole('admin', 'svc_mgr')

  const [page, setPage] = useState(1)
  const [category, setCategory] = useState('')
  const [lowStock, setLowStock] = useState(false)
  const [adjustPartId, setAdjustPartId] = useState<number | null>(null)
  const [adjustDelta, setAdjustDelta] = useState('')
  const [adjustReason, setAdjustReason] = useState('')
  const [pricePart, setPricePart] = useState<SparePart | null>(null)
  const [priceValue, setPriceValue] = useState('')
  const [priceCurrency, setPriceCurrency] = useState('RUB')
  const [priceReason, setPriceReason] = useState('')
  const [priceError, setPriceError] = useState<string | null>(null)
  const [historyPartId, setHistoryPartId] = useState<number | null>(null)

  const qc = useQueryClient()
  const params: Record<string, unknown> = { page, size: 20 }
  if (category) params.category = category
  if (lowStock) params.low_stock = true

  const { data, isLoading, isError } = useParts(params)
  const adjustQty = useAdjustQuantity()

  const setPrice = useMutation({
    mutationFn: ({ id, payload }: { id: number; payload: SparePartPriceUpdate }) =>
      partsApi.setPrice(id, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['parts'] })
      setPricePart(null)
      setPriceValue('')
      setPriceReason('')
      setPriceError(null)
    },
    onError: (e: { response?: { data?: { detail?: unknown } } }) => {
      const detail = e?.response?.data?.detail
      if (Array.isArray(detail)) {
        setPriceError(detail.map((d: { msg: string }) => d.msg).join(', '))
      } else if (typeof detail === 'string') {
        setPriceError(detail)
      } else {
        setPriceError('Ошибка при сохранении цены')
      }
    },
  })

  const { data: priceHistory } = useQuery({
    queryKey: ['price-history', historyPartId],
    queryFn: () => partsApi.getPriceHistory(historyPartId!).then(r => r.data),
    enabled: historyPartId !== null,
  })

  const handleAdjust = () => {
    if (!adjustPartId || !adjustDelta) return
    adjustQty.mutate(
      { id: adjustPartId, delta: parseInt(adjustDelta, 10), reason: adjustReason },
      {
        onSuccess: () => {
          setAdjustPartId(null)
          setAdjustDelta('')
          setAdjustReason('')
        },
      }
    )
  }

  const handleSetPrice = () => {
    if (!pricePart || !priceValue) return
    setPriceError(null)
    setPrice.mutate({
      id: pricePart.id,
      payload: { new_price: priceValue, currency: priceCurrency, reason: priceReason },
    })
  }

  const openPriceModal = (part: SparePart) => {
    setPricePart(part)
    setPriceValue(parseFloat(String(part.unit_price ?? part.price ?? 0)).toFixed(2))
    setPriceCurrency(part.currency ?? 'RUB')
    setPriceReason('')
    setPriceError(null)
  }

  const categories = data
    ? [...new Set(data.items.map(p => p.category).filter(Boolean))]
    : []

  const adjustPart = data?.items.find(p => p.id === adjustPartId)

  return (
    <>
      <div className="page-header">
        <h1>Склад запчастей</h1>
      </div>

      <div className="filters-bar">
        <select
          className="form-select"
          value={category}
          onChange={e => { setCategory(e.target.value); setPage(1) }}
        >
          <option value="">Все категории</option>
          {categories.map(c => (
            <option key={c} value={c!}>{c}</option>
          ))}
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer', color: 'var(--text)' }}>
          <input
            type="checkbox"
            checked={lowStock}
            onChange={e => { setLowStock(e.target.checked); setPage(1) }}
          />
          Только заканчивающиеся
        </label>
      </div>

      {isLoading && <div className="loading-center"><span className="spinner spinner-lg" /></div>}
      {isError && <div className="alert alert-error">Ошибка загрузки склада</div>}

      {data && (
        <>
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Название</th>
                  <th>Категория</th>
                  <th>Кол-во</th>
                  <th>Мин.</th>
                  <th>Цена</th>
                  <th>Статус</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {data.items.length === 0 && (
                  <tr>
                    <td colSpan={8} style={{ textAlign: 'center', padding: '40px', color: 'var(--text-muted)' }}>
                      Запчасти не найдены
                    </td>
                  </tr>
                )}
                {data.items.map(part => {
                  const price = parseFloat(String(part.unit_price ?? part.price ?? 0))
                  const isLow = part.quantity < part.min_quantity
                  const hasPriceSet = price > 0
                  return (
                    <tr key={part.id} className={isLow ? 'part-row-low' : ''}>
                      <td><span style={{ fontFamily: 'monospace', fontSize: 12 }}>{part.sku}</span></td>
                      <td style={{ fontWeight: 500 }}>{part.name}</td>
                      <td>{part.category ?? '—'}</td>
                      <td>
                        <span className={isLow ? 'qty-low' : 'qty-ok'}>{part.quantity}</span>
                      </td>
                      <td style={{ color: 'var(--text-muted)' }}>{part.min_quantity}</td>
                      <td>
                        <span style={{ fontWeight: hasPriceSet ? 600 : 400, color: hasPriceSet ? 'inherit' : 'var(--text-muted)' }}>
                          {hasPriceSet ? `${price.toFixed(2)} ${part.currency ?? '₽'}` : '—'}
                        </span>
                        {hasPriceSet && (
                          <button
                            className="btn-link"
                            style={{ marginLeft: 6, fontSize: 11 }}
                            onClick={() => setHistoryPartId(part.id)}
                          >
                            история
                          </button>
                        )}
                      </td>
                      <td>
                        {isLow
                          ? <span className="badge priority-high">Мало</span>
                          : <span className="badge badge-completed">В наличии</span>
                        }
                      </td>
                      <td style={{ display: 'flex', gap: 4 }}>
                        <button className="btn btn-secondary btn-sm" onClick={() => setAdjustPartId(part.id)}>
                          Кол-во
                        </button>
                        {canManagePrice && (
                          <button className="btn btn-primary btn-sm" onClick={() => openPriceModal(part)}>
                            {hasPriceSet ? 'Изм. цену' : 'Уст. цену'}
                          </button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          <Pagination page={data.page} pages={data.pages} total={data.total} size={data.size} onPageChange={setPage} />
        </>
      )}

      {/* Adjust quantity modal */}
      {adjustPartId && adjustPart && (
        <div className="modal-overlay" onClick={() => setAdjustPartId(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Изменить количество</h3>
              <button className="modal-close" onClick={() => setAdjustPartId(null)}>×</button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: 13, marginBottom: 16 }}>
                <strong>{adjustPart.name}</strong> — текущий остаток: <strong>{adjustPart.quantity}</strong>
              </p>
              <div className="form-group">
                <label className="form-label">Изменение (+ добавить / − списать)</label>
                <input type="number" className="form-input" placeholder="Например: 10 или -5"
                  value={adjustDelta} onChange={e => setAdjustDelta(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Причина</label>
                <input type="text" className="form-input" placeholder="Например: поступление, списание..."
                  value={adjustReason} onChange={e => setAdjustReason(e.target.value)} />
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={() => setAdjustPartId(null)}>Отмена</button>
              <button type="button" className="btn btn-primary" onClick={handleAdjust}
                disabled={!adjustDelta || adjustQty.isPending}>
                {adjustQty.isPending ? 'Сохранение...' : 'Применить'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Set price modal */}
      {pricePart && (
        <div className="modal-overlay" onClick={() => setPricePart(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{parseFloat(String(pricePart.unit_price ?? pricePart.price ?? 0)) > 0 ? 'Изменить цену' : 'Установить цену'}</h3>
              <button className="modal-close" onClick={() => setPricePart(null)}>×</button>
            </div>
            <div className="modal-body">
              <p style={{ fontSize: 13, marginBottom: 16 }}>
                <strong>{pricePart.name}</strong> (SKU: {pricePart.sku})
              </p>
              {priceError && <div className="alert alert-error" style={{ marginBottom: 12 }}>{priceError}</div>}
              <div className="form-group">
                <label className="form-label">Новая цена *</label>
                <input type="number" min="0" step="0.01" className="form-input"
                  placeholder="0.00" value={priceValue} onChange={e => setPriceValue(e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Валюта</label>
                <select className="form-select" value={priceCurrency} onChange={e => setPriceCurrency(e.target.value)}>
                  <option value="RUB">RUB</option>
                  <option value="USD">USD</option>
                  <option value="EUR">EUR</option>
                  <option value="PLN">PLN</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Причина изменения * (мин. 5 символов)</label>
                <input type="text" className="form-input"
                  placeholder="Например: обновление прайса поставщика"
                  value={priceReason} onChange={e => setPriceReason(e.target.value)} />
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={() => setPricePart(null)}>Отмена</button>
              <button type="button" className="btn btn-primary" onClick={handleSetPrice}
                disabled={!priceValue || priceReason.trim().length < 5 || setPrice.isPending}>
                {setPrice.isPending ? 'Сохранение...' : 'Сохранить'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Price history modal */}
      {historyPartId !== null && (
        <div className="modal-overlay" onClick={() => setHistoryPartId(null)}>
          <div className="modal" style={{ maxWidth: 600 }} onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>История цен</h3>
              <button className="modal-close" onClick={() => setHistoryPartId(null)}>×</button>
            </div>
            <div className="modal-body">
              {!priceHistory && <div className="loading-center"><span className="spinner" /></div>}
              {priceHistory && priceHistory.length === 0 && (
                <p style={{ color: 'var(--text-muted)', textAlign: 'center' }}>История пуста</p>
              )}
              {priceHistory && priceHistory.length > 0 && (
                <table className="table" style={{ fontSize: 13 }}>
                  <thead>
                    <tr>
                      <th>Дата</th>
                      <th>Старая цена</th>
                      <th>Новая цена</th>
                      <th>Причина</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(priceHistory as PriceHistoryEntry[]).map(h => (
                      <tr key={h.id}>
                        <td>{new Date(h.changed_at).toLocaleString('ru-RU')}</td>
                        <td>{parseFloat(h.old_price).toFixed(2)} {h.currency}</td>
                        <td style={{ fontWeight: 600 }}>{parseFloat(h.new_price).toFixed(2)} {h.currency}</td>
                        <td>{h.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  )
}
```

---

## Task 10: Frontend — TicketDetailPage (фильтр by has_price)

**Files:**
- Modify: `frontend/src/pages/TicketDetailPage.tsx`

- [ ] **Step 1: Изменить запрос запчастей в форме акта**

Найти строку:
```tsx
const { data: partsData } = useParts({ size: 200 })
```

Заменить на:
```tsx
const { data: partsData } = useParts({ size: 200, has_price: true })
```

Это применяет BR-F-122: в форме акта показываются только запчасти с установленной ценой.

---

## Task 11: Сборка и деплой

- [ ] **Step 1: Собрать frontend**

```bash
docker compose build frontend
docker compose up -d frontend nginx
```

- [ ] **Step 2: Проверить что приложение работает**

```bash
# Проверить статус контейнеров
docker compose ps

# Проверить логи если есть ошибки
docker compose logs frontend --tail=20
docker compose logs backend --tail=20
```

- [ ] **Step 3: Открыть в браузере**

Перейти на http://localhost/ и проверить:
- [ ] Меню «Товары» исчезло из боковой панели
- [ ] Страница «Склад запчастей» открывается, в таблице видна колонка «Цена»
- [ ] Кнопки «Уст. цену» / «Изм. цену» видны для admin/svc_mgr
- [ ] Модальное окно установки цены открывается и сохраняет данные
- [ ] После сохранения цены в строке появляется цена и ссылка «история»
- [ ] Клик на «история» — модальное окно с историей цен
- [ ] Форма акта на странице заявки: в дропдауне «Запчасть» только позиции с ценой

- [ ] **Step 4: Финальный коммит**

```bash
git add .
git commit -m "feat: material catalog refactor — remove product_catalog, add price_history, update forms (BR-F-122)"
```

---

## Self-Review

### Spec Coverage

| Требование | Реализовано в |
|---|---|
| Единый каталог матценностей (spare_parts) | Task 1-4: удалена product_catalog |
| История цен (price_history) | Task 1: миграция, Task 2: модель, Task 6: PATCH price создаёт запись |
| BR-F-122: только с ценой в формах | Task 6: has_price фильтр, Task 10: TicketDetailPage |
| UC-102: установить/изменить цену | Task 6: PATCH /{id}/price |
| RBAC: admin/svc_mgr могут менять цену | Task 5/6: require_roles("admin", "svc_mgr") |
| История цен доступна всем кроме client_user | Task 5/6: client_scope check |
| Удалён роут /product-catalog | Task 7: App.tsx, Layout.tsx |

### Нет плейсхолдеров — все шаги содержат полный код.

### Типы согласованы:
- `SparePartPriceUpdate` определён в schemas/__init__.py (Task 3) и types.ts (Task 8)
- `PriceHistoryResponse` определён в schemas/__init__.py (Task 3) и types.ts (Task 8)
- `PriceHistory` модель определена в models/__init__.py (Task 2) — используется в parts.py (Task 6)
