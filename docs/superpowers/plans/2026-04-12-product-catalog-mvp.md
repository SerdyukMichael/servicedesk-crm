# Product Catalog MVP — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить справочник товаров (ProductCatalog) с полным CRUD на бэкенде и фронтенде, расширить WorkActItem/InvoiceItem для поддержки типа "product", написать тесты, задеплоить на тестовый стенд.

**Architecture:** Новая таблица `product_catalog` (аналог `service_catalog`). Миграция Alembic добавляет таблицу и столбец `product_id` в `work_act_items` / `invoice_items` + значение "product" в enum. Бэкенд: новый роутер `/product-catalog` по аналогии с `/service-catalog`. Фронтенд: новая страница `ProductCatalogPage` + маршрут + боковое меню.

**Tech Stack:** Python 3.11 / FastAPI / SQLAlchemy 2.0 / Alembic / MySQL 8 / React 18 / TypeScript / Vite

---

## Файлы — что создаётся / меняется

| Действие | Файл |
|---|---|
| Изменить | `backend/app/models/__init__.py` — новый класс ProductCatalog, product_id в WorkActItem/InvoiceItem |
| Изменить | `backend/app/schemas/__init__.py` — новые схемы ProductCatalog* |
| Создать | `backend/app/api/endpoints/product_catalog.py` |
| Изменить | `backend/app/api/router.py` — добавить product_catalog роутер |
| Создать | `backend/alembic/versions/010_product_catalog.py` |
| Изменить | `backend/tests/conftest.py` — фабрика make_product_catalog_item |
| Создать | `backend/tests/test_product_catalog.py` |
| Создать | `frontend/src/pages/ProductCatalogPage.tsx` |
| Изменить | `frontend/src/App.tsx` — новый маршрут |
| Изменить | `frontend/src/components/Layout.tsx` — ссылка в меню |
| Изменить | `frontend/src/api/types.ts` — типы ProductCatalog |
| Изменить | `frontend/src/api/endpoints.ts` — API-вызовы |
| Создать | `frontend/src/hooks/useProductCatalog.ts` |

---

## Task 1: Alembic-миграция — таблица product_catalog + расширение enums

**Files:**
- Create: `backend/alembic/versions/010_product_catalog.py`

- [ ] **Шаг 1.1: Создать файл миграции**

Файл `backend/alembic/versions/010_product_catalog.py`:

```python
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
```

- [ ] **Шаг 1.2: Применить миграцию в Docker**

```bash
docker compose exec backend alembic upgrade head
```

Ожидаемый вывод: `Running upgrade 6cd8b51a3e8b -> 010, product_catalog`

---

## Task 2: Backend — модель ProductCatalog + обновление WorkActItem/InvoiceItem

**Files:**
- Modify: `backend/app/models/__init__.py`

- [ ] **Шаг 2.1: Добавить ProductCatalog в models/__init__.py**

Найти блок `# ── Service Catalog` (строка ~303) и добавить после него:

```python
# ── Product Catalog ───────────────────────────────────────────────────────────
class ProductCatalog(Base):
    __tablename__ = "product_catalog"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    code:        Mapped[str]           = mapped_column(String(32), unique=True, nullable=False, index=True)
    name:        Mapped[str]           = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category:    Mapped[str]           = mapped_column(
        Enum("spare_part", "other", name="product_category_enum"),
        default="other", nullable=False
    )
    unit:        Mapped[str]           = mapped_column(
        Enum("pcs", "pack", "kit", name="product_unit_enum"),
        default="pcs", nullable=False
    )
    unit_price:  Mapped[Decimal]       = mapped_column(DECIMAL(12, 2), nullable=False, default=0)
    currency:    Mapped[str]           = mapped_column(String(3), default="RUB", nullable=False)
    is_active:   Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)
    created_at:  Mapped[datetime]      = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at:  Mapped[datetime]      = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    work_act_items: Mapped[List["WorkActItem"]] = relationship("WorkActItem", back_populates="product")
```

- [ ] **Шаг 2.2: Обновить WorkActItem в models/__init__.py**

В классе `WorkActItem` заменить строку с `item_type` Enum и добавить `product_id`:

```python
class WorkActItem(Base):
    __tablename__ = "work_act_items"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_act_id: Mapped[int]           = mapped_column(ForeignKey("work_acts.id", ondelete="CASCADE"), nullable=False)
    item_type:   Mapped[str]           = mapped_column(
        Enum("service", "part", "product", name="work_act_item_type_enum"),
        nullable=False
    )
    service_id:  Mapped[Optional[int]] = mapped_column(ForeignKey("service_catalog.id", ondelete="RESTRICT"), nullable=True)
    part_id:     Mapped[Optional[int]] = mapped_column(ForeignKey("spare_parts.id", ondelete="RESTRICT"), nullable=True)
    product_id:  Mapped[Optional[int]] = mapped_column(ForeignKey("product_catalog.id", ondelete="RESTRICT"), nullable=True)
    name:        Mapped[str]           = mapped_column(String(255), nullable=False)
    quantity:    Mapped[Decimal]       = mapped_column(DECIMAL(10, 3), nullable=False, default=1)
    unit:        Mapped[str]           = mapped_column(String(16), nullable=False, default="шт")
    unit_price:  Mapped[Decimal]       = mapped_column(DECIMAL(12, 2), nullable=False, default=0)
    total:       Mapped[Decimal]       = mapped_column(DECIMAL(14, 2), nullable=False, default=0)
    sort_order:  Mapped[int]           = mapped_column(Integer, default=0, nullable=False)

    work_act: Mapped["WorkAct"]                    = relationship("WorkAct", back_populates="items")
    service:  Mapped[Optional["ServiceCatalog"]]   = relationship("ServiceCatalog", back_populates="work_act_items")
    part:     Mapped[Optional["SparePart"]]        = relationship("SparePart")
    product:  Mapped[Optional["ProductCatalog"]]   = relationship("ProductCatalog", back_populates="work_act_items")
```

- [ ] **Шаг 2.3: Обновить InvoiceItem в models/__init__.py**

В классе `InvoiceItem` заменить enum и добавить `product_id`:

```python
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
        Enum("service", "part", "product", "manual", name="invoice_item_type_enum"),
        nullable=True
    )
    service_id:  Mapped[Optional[int]] = mapped_column(ForeignKey("service_catalog.id", ondelete="RESTRICT"), nullable=True)
    part_id:     Mapped[Optional[int]] = mapped_column(ForeignKey("spare_parts.id", ondelete="RESTRICT"), nullable=True)
    product_id:  Mapped[Optional[int]] = mapped_column(ForeignKey("product_catalog.id", ondelete="RESTRICT"), nullable=True)

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="items")
```

- [ ] **Шаг 2.4: Добавить ProductCatalog в __all__ внизу models/__init__.py**

Найти строку `"ServiceCatalog",` в списке `__all__` и добавить рядом:

```python
"ProductCatalog",
```

---

## Task 3: Backend — схемы ProductCatalog

**Files:**
- Modify: `backend/app/schemas/__init__.py`

- [ ] **Шаг 3.1: Добавить схемы ProductCatalog в schemas/__init__.py**

Найти блок `class ServiceCatalogCreate` (~строка 778) и добавить после `ServiceCatalogResponse`:

```python
# ── Product Catalog ───────────────────────────────────────────────────────────

class ProductCatalogCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    category: str = "other"   # "spare_part" | "other"
    unit: str = "pcs"          # "pcs" | "pack" | "kit"
    unit_price: Decimal = Decimal("0.00")
    currency: str = "RUB"
    is_active: bool = True


class ProductCatalogUpdate(BaseModel):
    code: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None


class ProductCatalogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: Optional[str]
    category: str
    unit: str
    unit_price: Decimal
    currency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
```

- [ ] **Шаг 3.2: Обновить WorkActItemCreate — добавить product_id**

Найти `class WorkActItemCreate` (~строка 473) и добавить поле:

```python
class WorkActItemCreate(BaseModel):
    item_type: str  # "service" | "part" | "product"
    service_id: Optional[int] = None
    part_id: Optional[int] = None
    product_id: Optional[int] = None   # ← добавить
    name: str
    quantity: Decimal = Decimal("1")
    unit: str = "шт"
    unit_price: Decimal = Decimal("0")
    sort_order: int = 0
```

- [ ] **Шаг 3.3: Обновить WorkActItemResponse — добавить product_id**

```python
class WorkActItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    work_act_id: int
    item_type: str
    service_id: Optional[int]
    part_id: Optional[int]
    product_id: Optional[int]   # ← добавить
    name: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    total: Decimal
    sort_order: int
```

- [ ] **Шаг 3.4: Обновить InvoiceItemCreate и InvoiceItemResponse — добавить product_id**

```python
class InvoiceItemCreate(BaseModel):
    description: str
    quantity: Decimal = Decimal("1")
    unit: str = "шт"
    unit_price: Decimal
    item_type: Optional[str] = None   # "service" | "part" | "product" | "manual"
    service_id: Optional[int] = None
    part_id: Optional[int] = None
    product_id: Optional[int] = None  # ← добавить
    sort_order: int = 0


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
    item_type: Optional[str]
    service_id: Optional[int]
    part_id: Optional[int]
    product_id: Optional[int]   # ← добавить
```

- [ ] **Шаг 3.5: Добавить ProductCatalog* в __all__ schemas/__init__.py**

Найти `"ServiceCatalogCreate", "ServiceCatalogUpdate", "ServiceCatalogResponse",` и добавить:

```python
"ProductCatalogCreate", "ProductCatalogUpdate", "ProductCatalogResponse",
```

---

## Task 4: Backend — эндпоинт product_catalog

**Files:**
- Create: `backend/app/api/endpoints/product_catalog.py`

- [ ] **Шаг 4.1: Создать файл product_catalog.py**

```python
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ProductCatalog, WorkActItem, InvoiceItem, User
from app.api.deps import get_current_user, require_roles
from app.schemas import (
    ProductCatalogCreate, ProductCatalogUpdate, ProductCatalogResponse,
    PaginatedResponse,
)

router = APIRouter()

_WRITE_ROLES = ("admin", "svc_mgr")


@router.get("", response_model=PaginatedResponse[ProductCatalogResponse])
def list_product_catalog(
    include_inactive: bool = Query(False),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(ProductCatalog)
    if not include_inactive:
        q = q.filter(ProductCatalog.is_active.is_(True))
    if category:
        q = q.filter(ProductCatalog.category == category)
    total = q.count()
    skip = (page - 1) * size
    items = q.order_by(ProductCatalog.name).offset(skip).limit(size).all()
    pages = max(1, (total + size - 1) // size)
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.post("", response_model=ProductCatalogResponse, status_code=status.HTTP_201_CREATED)
def create_product_catalog_item(
    data: ProductCatalogCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE_ROLES)),
):
    if db.query(ProductCatalog).filter(ProductCatalog.code == data.code).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "CONFLICT", "message": f"Код {data.code} уже используется"},
        )
    item = ProductCatalog(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{item_id}", response_model=ProductCatalogResponse)
def get_product_catalog_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return _get_or_404(db, item_id)


@router.patch("/{item_id}", response_model=ProductCatalogResponse)
def update_product_catalog_item(
    item_id: int,
    data: ProductCatalogUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE_ROLES)),
):
    item = _get_or_404(db, item_id)
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product_catalog_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin",)),
):
    item = _get_or_404(db, item_id)
    # BR-P-006: запрет удаления если используется
    in_acts = db.query(WorkActItem).filter(WorkActItem.product_id == item_id).first()
    in_invoices = db.query(InvoiceItem).filter(InvoiceItem.product_id == item_id).first()
    if in_acts or in_invoices:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "IN_USE", "message": "Позиция используется в документах. Деактивируйте её"},
        )
    db.delete(item)
    db.commit()


def _get_or_404(db: Session, item_id: int) -> ProductCatalog:
    item = db.query(ProductCatalog).filter(ProductCatalog.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Позиция прайс-листа не найдена"},
        )
    return item
```

- [ ] **Шаг 4.2: Добавить роутер в router.py**

Открыть `backend/app/api/router.py`, добавить импорт и регистрацию:

```python
from app.api.endpoints import product_catalog   # добавить рядом с остальными импортами
```

```python
api_router.include_router(product_catalog.router, prefix="/product-catalog", tags=["Прайс-лист товаров"])
```

---

## Task 5: Backend — тесты ProductCatalog

**Files:**
- Modify: `backend/tests/conftest.py` — добавить фабрику
- Create: `backend/tests/test_product_catalog.py`

- [ ] **Шаг 5.1: Добавить фабрику make_product_catalog_item в conftest.py**

Найти функцию `make_service_catalog_item` в `conftest.py` и добавить рядом:

```python
def make_product_catalog_item(
    db,
    code: str = "PROD-001",
    name: str = "Тест товар",
    category: str = "spare_part",
    unit: str = "pcs",
    unit_price: float = 500.0,
    currency: str = "RUB",
    is_active: bool = True,
):
    from app.models import ProductCatalog
    item = ProductCatalog(
        code=code, name=name, category=category, unit=unit,
        unit_price=unit_price, currency=currency, is_active=is_active,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
```

- [ ] **Шаг 5.2: Написать тесты — проверить что файл не существует**

```bash
ls backend/tests/test_product_catalog.py 2>/dev/null || echo "NOT EXISTS"
```

Ожидаемый вывод: `NOT EXISTS`

- [ ] **Шаг 5.3: Создать test_product_catalog.py**

```python
"""
Tests for ProductCatalog (price list for products/spare parts).
BR-F-121 / UC-102
"""
import pytest
from decimal import Decimal
from app.models import ProductCatalog
from app.schemas import ProductCatalogCreate

from tests.conftest import (
    make_admin, make_engineer, admin_headers, auth_headers,
    make_product_catalog_item,
)


# ── Model tests ───────────────────────────────────────────────────────────────

def test_product_catalog_model_created(db):
    item = ProductCatalog(
        code="PROD-001",
        name="Картридж ATM",
        category="spare_part",
        unit="pcs",
        unit_price=2500.00,
        currency="RUB",
        is_active=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    assert item.id is not None
    assert item.code == "PROD-001"
    assert item.is_active is True


# ── Schema tests ──────────────────────────────────────────────────────────────

def test_product_catalog_schema_valid():
    data = ProductCatalogCreate(
        code="PROD-001",
        name="Картридж ATM",
        category="spare_part",
        unit="pcs",
        unit_price=Decimal("2500.00"),
    )
    assert data.code == "PROD-001"
    assert data.currency == "RUB"   # default


def test_product_catalog_schema_requires_name():
    with pytest.raises(Exception):
        ProductCatalogCreate(code="PROD-001", category="other", unit="pcs", unit_price=0)


# ── CRUD API tests ────────────────────────────────────────────────────────────

class TestProductCatalogCRUD:

    def test_list_empty(self, client, db):
        headers = admin_headers(db)
        r = client.get("/api/v1/product-catalog", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert data["total"] == 0

    def test_create_item(self, client, db):
        headers = admin_headers(db)
        r = client.post("/api/v1/product-catalog", json={
            "code": "PROD-001",
            "name": "Картридж банкомата",
            "category": "spare_part",
            "unit": "pcs",
            "unit_price": "2500.00",
        }, headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert data["code"] == "PROD-001"
        assert data["unit_price"] == "2500.00"
        assert data["is_active"] is True

    def test_create_duplicate_code_fails(self, client, db):
        headers = admin_headers(db)
        make_product_catalog_item(db, code="PROD-DUP")
        r = client.post("/api/v1/product-catalog", json={
            "code": "PROD-DUP",
            "name": "Другой",
            "category": "other",
            "unit": "pcs",
            "unit_price": "100",
        }, headers=headers)
        assert r.status_code == 409

    def test_get_item(self, client, db):
        headers = admin_headers(db)
        item = make_product_catalog_item(db, code="PROD-GET")
        r = client.get(f"/api/v1/product-catalog/{item.id}", headers=headers)
        assert r.status_code == 200
        assert r.json()["code"] == "PROD-GET"

    def test_update_item(self, client, db):
        headers = admin_headers(db)
        item = make_product_catalog_item(db, code="PROD-UPD", name="Старое имя")
        r = client.patch(f"/api/v1/product-catalog/{item.id}", json={
            "unit_price": "3000.00",
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["unit_price"] == "3000.00"

    def test_deactivate_item(self, client, db):
        headers = admin_headers(db)
        item = make_product_catalog_item(db, code="PROD-DEACT")
        r = client.patch(f"/api/v1/product-catalog/{item.id}", json={"is_active": False}, headers=headers)
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_deactivated_hidden_in_list_by_default(self, client, db):
        headers = admin_headers(db)
        item = make_product_catalog_item(db, code="PROD-HIDDEN")
        client.patch(f"/api/v1/product-catalog/{item.id}", json={"is_active": False}, headers=headers)
        r = client.get("/api/v1/product-catalog", headers=headers)
        ids = [i["id"] for i in r.json()["items"]]
        assert item.id not in ids

    def test_show_inactive_with_param(self, client, db):
        headers = admin_headers(db)
        item = make_product_catalog_item(db, code="PROD-SHOW")
        client.patch(f"/api/v1/product-catalog/{item.id}", json={"is_active": False}, headers=headers)
        r = client.get("/api/v1/product-catalog?include_inactive=true", headers=headers)
        ids = [i["id"] for i in r.json()["items"]]
        assert item.id in ids

    def test_filter_by_category(self, client, db):
        headers = admin_headers(db)
        make_product_catalog_item(db, code="PROD-SPARE", category="spare_part")
        make_product_catalog_item(db, code="PROD-OTHER", category="other")
        r = client.get("/api/v1/product-catalog?category=spare_part", headers=headers)
        items = r.json()["items"]
        assert all(i["category"] == "spare_part" for i in items)

    def test_engineer_cannot_create(self, client, db):
        eng = make_engineer(db)
        headers = auth_headers(eng.id, eng.roles)
        r = client.post("/api/v1/product-catalog", json={
            "code": "PROD-X",
            "name": "Test",
            "category": "other",
            "unit": "pcs",
            "unit_price": "100",
        }, headers=headers)
        assert r.status_code == 403

    def test_delete_unused_item(self, client, db):
        headers = admin_headers(db)
        item = make_product_catalog_item(db, code="PROD-DEL")
        r = client.delete(f"/api/v1/product-catalog/{item.id}", headers=headers)
        assert r.status_code == 204

    def test_delete_used_item_blocked(self, client, db):
        """BR-P-006: нельзя удалить если используется в работах."""
        from app.models import WorkActItem, WorkAct
        from tests.conftest import make_client, make_equipment_model, make_equipment, make_ticket

        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        prod = make_product_catalog_item(db, code="PROD-USED")
        cli = make_client(db)
        model = make_equipment_model(db)
        equip = make_equipment(db, cli.id, model.id)
        ticket = make_ticket(db, cli.id, equip.id, admin.id)

        act = WorkAct(ticket_id=ticket.id, engineer_id=admin.id)
        db.add(act)
        db.flush()
        act_item = WorkActItem(
            work_act_id=act.id,
            item_type="product",
            product_id=prod.id,
            name=prod.name,
            quantity=Decimal("1"),
            unit="pcs",
            unit_price=Decimal("500"),
            total=Decimal("500"),
        )
        db.add(act_item)
        db.commit()

        r = client.delete(f"/api/v1/product-catalog/{prod.id}", headers=headers)
        assert r.status_code == 409

    def test_unauthenticated_returns_401(self, client):
        r = client.get("/api/v1/product-catalog")
        assert r.status_code == 401
```

- [ ] **Шаг 5.4: Запустить тесты**

```bash
docker compose exec backend pytest tests/test_product_catalog.py -v
```

Ожидаемый вывод: все тесты PASSED.

- [ ] **Шаг 5.5: Запустить полный тест-сьют**

```bash
docker compose exec backend pytest tests/ -v --tb=short
```

Ожидаемый вывод: нет FAILED (только PASSED/SKIPPED).

- [ ] **Шаг 5.6: Коммит бэкенда**

```bash
git add backend/app/models/__init__.py \
        backend/app/schemas/__init__.py \
        backend/app/api/endpoints/product_catalog.py \
        backend/app/api/router.py \
        backend/alembic/versions/010_product_catalog.py \
        backend/tests/conftest.py \
        backend/tests/test_product_catalog.py
git commit -m "feat: product catalog — model, endpoint, migration, tests (UC-102)"
```

---

## Task 6: Frontend — типы и API-клиент

**Files:**
- Modify: `frontend/src/api/types.ts`
- Modify: `frontend/src/api/endpoints.ts`

- [ ] **Шаг 6.1: Добавить типы ProductCatalog в types.ts**

Найти блок `ServiceCatalogItem` и добавить рядом:

```typescript
// ── Product Catalog ───────────────────────────────────────────────────────────

export type ProductCategory = 'spare_part' | 'other'
export type ProductUnit = 'pcs' | 'pack' | 'kit'

export interface ProductCatalogItem {
  id: number
  code: string
  name: string
  description?: string
  category: ProductCategory
  unit: ProductUnit
  unit_price: string
  currency: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ProductCatalogCreate {
  code: string
  name: string
  description?: string
  category: ProductCategory
  unit: ProductUnit
  unit_price: string
  currency?: string
}

export interface ProductCatalogUpdate {
  code?: string
  name?: string
  description?: string
  category?: ProductCategory
  unit?: ProductUnit
  unit_price?: string
  currency?: string
  is_active?: boolean
}
```

- [ ] **Шаг 6.2: Добавить API-функции в endpoints.ts**

Найти блок функций для serviceCatalog и добавить рядом:

```typescript
// ── Product Catalog ───────────────────────────────────────────────────────────

export const productCatalogApi = {
  list: (params?: { include_inactive?: boolean; category?: string; page?: number; size?: number }) =>
    api.get<PaginatedResponse<ProductCatalogItem>>('/product-catalog', { params }),

  get: (id: number) =>
    api.get<ProductCatalogItem>(`/product-catalog/${id}`),

  create: (data: ProductCatalogCreate) =>
    api.post<ProductCatalogItem>('/product-catalog', data),

  update: (id: number, data: ProductCatalogUpdate) =>
    api.patch<ProductCatalogItem>(`/product-catalog/${id}`, data),

  delete: (id: number) =>
    api.delete(`/product-catalog/${id}`),
}
```

---

## Task 7: Frontend — хук useProductCatalog

**Files:**
- Create: `frontend/src/hooks/useProductCatalog.ts`

- [ ] **Шаг 7.1: Создать useProductCatalog.ts**

Взять `useServiceCatalog.ts` как шаблон, создать `useProductCatalog.ts`:

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { productCatalogApi } from '../api/endpoints'
import type { ProductCatalogCreate, ProductCatalogUpdate } from '../api/types'

const QK = 'product-catalog'

export function useProductCatalog(params?: {
  include_inactive?: boolean
  category?: string
  page?: number
  size?: number
}) {
  return useQuery({
    queryKey: [QK, params],
    queryFn: () => productCatalogApi.list(params).then(r => r.data),
  })
}

export function useCreateProductCatalogItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ProductCatalogCreate) =>
      productCatalogApi.create(data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QK] }),
  })
}

export function useUpdateProductCatalogItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ProductCatalogUpdate }) =>
      productCatalogApi.update(id, data).then(r => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QK] }),
  })
}

export function useDeleteProductCatalogItem() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: number) => productCatalogApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: [QK] }),
  })
}
```

---

## Task 8: Frontend — страница ProductCatalogPage

**Files:**
- Create: `frontend/src/pages/ProductCatalogPage.tsx`

- [ ] **Шаг 8.1: Создать ProductCatalogPage.tsx**

```tsx
import { useState } from 'react'
import { useAuth } from '../context/AuthContext'
import {
  useProductCatalog,
  useCreateProductCatalogItem,
  useUpdateProductCatalogItem,
  useDeleteProductCatalogItem,
} from '../hooks/useProductCatalog'
import Pagination from '../components/Pagination'
import type { ProductCatalogItem, ProductCategory, ProductUnit } from '../api/types'

const CATEGORY_LABELS: Record<ProductCategory, string> = {
  spare_part: 'Запчасть',
  other: 'Прочее',
}

const UNIT_LABELS: Record<ProductUnit, string> = {
  pcs: 'шт',
  pack: 'упак',
  kit: 'комплект',
}

interface FormState {
  code: string
  name: string
  description: string
  category: ProductCategory
  unit: ProductUnit
  unit_price: string
}

const EMPTY_FORM: FormState = {
  code: '',
  name: '',
  description: '',
  category: 'spare_part',
  unit: 'pcs',
  unit_price: '',
}

export default function ProductCatalogPage() {
  const { hasRole } = useAuth()
  const canWrite = hasRole('admin', 'svc_mgr')

  const [page, setPage] = useState(1)
  const [category, setCategory] = useState('')
  const [includeInactive, setIncludeInactive] = useState(false)

  const [showForm, setShowForm] = useState(false)
  const [editItem, setEditItem] = useState<ProductCatalogItem | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [formError, setFormError] = useState<string | null>(null)

  const [deleteId, setDeleteId] = useState<number | null>(null)
  const [deleteError, setDeleteError] = useState<string | null>(null)

  const { data, isLoading } = useProductCatalog({
    include_inactive: includeInactive || undefined,
    category: category || undefined,
    page,
    size: 20,
  })
  const createMut = useCreateProductCatalogItem()
  const updateMut = useUpdateProductCatalogItem()
  const deleteMut = useDeleteProductCatalogItem()

  function openCreate() {
    setEditItem(null)
    setForm(EMPTY_FORM)
    setFormError(null)
    setShowForm(true)
  }

  function openEdit(item: ProductCatalogItem) {
    setEditItem(item)
    setForm({
      code: item.code,
      name: item.name,
      description: item.description ?? '',
      category: item.category,
      unit: item.unit,
      unit_price: item.unit_price,
    })
    setFormError(null)
    setShowForm(true)
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setFormError(null)
    if (!form.code.trim() || !form.name.trim() || !form.unit_price) {
      setFormError('Заполните все обязательные поля')
      return
    }
    try {
      if (editItem) {
        await updateMut.mutateAsync({ id: editItem.id, data: { ...form } })
      } else {
        await createMut.mutateAsync({ ...form })
      }
      setShowForm(false)
    } catch (err: any) {
      const msg = err?.response?.data?.detail?.message ?? 'Ошибка сохранения'
      setFormError(msg)
    }
  }

  async function handleDeactivate(item: ProductCatalogItem) {
    await updateMut.mutateAsync({ id: item.id, data: { is_active: false } })
  }

  async function handleActivate(item: ProductCatalogItem) {
    await updateMut.mutateAsync({ id: item.id, data: { is_active: true } })
  }

  async function handleDelete() {
    if (!deleteId) return
    setDeleteError(null)
    try {
      await deleteMut.mutateAsync(deleteId)
      setDeleteId(null)
    } catch (err: any) {
      const msg = err?.response?.data?.detail?.message ?? 'Ошибка удаления'
      setDeleteError(msg)
    }
  }

  const items = data?.items ?? []
  const totalPages = data?.pages ?? 1

  return (
    <div className="page-container">
      <div className="page-header">
        <h1>Прайс-лист товаров</h1>
        {canWrite && (
          <button className="btn btn-primary" onClick={openCreate}>
            + Добавить товар
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="filters-row" style={{ marginBottom: 16, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <select
          value={category}
          onChange={e => { setCategory(e.target.value); setPage(1) }}
          className="form-select"
          style={{ width: 180 }}
        >
          <option value="">Все категории</option>
          {(Object.keys(CATEGORY_LABELS) as ProductCategory[]).map(c => (
            <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
          ))}
        </select>
        <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <input
            type="checkbox"
            checked={includeInactive}
            onChange={e => { setIncludeInactive(e.target.checked); setPage(1) }}
          />
          Показать неактивные
        </label>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="loading">Загрузка...</div>
      ) : items.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon">📦</div>
          <p>Товары не найдены</p>
          {canWrite && <button className="btn btn-primary" onClick={openCreate}>Добавить первый товар</button>}
        </div>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th>Код</th>
              <th>Наименование</th>
              <th>Категория</th>
              <th>Ед.</th>
              <th>Цена</th>
              <th>Валюта</th>
              <th>Статус</th>
              {canWrite && <th>Действия</th>}
            </tr>
          </thead>
          <tbody>
            {items.map(item => (
              <tr key={item.id} style={{ opacity: item.is_active ? 1 : 0.5 }}>
                <td><code>{item.code}</code></td>
                <td>{item.name}</td>
                <td>{CATEGORY_LABELS[item.category] ?? item.category}</td>
                <td>{UNIT_LABELS[item.unit] ?? item.unit}</td>
                <td style={{ textAlign: 'right' }}>{parseFloat(item.unit_price).toLocaleString('ru-RU')}</td>
                <td>{item.currency}</td>
                <td>
                  <span className={`badge ${item.is_active ? 'badge-success' : 'badge-secondary'}`}>
                    {item.is_active ? 'Активен' : 'Неактивен'}
                  </span>
                </td>
                {canWrite && (
                  <td>
                    <button className="btn btn-sm btn-secondary" onClick={() => openEdit(item)}>Изменить</button>
                    {item.is_active
                      ? <button className="btn btn-sm btn-warning" style={{ marginLeft: 4 }} onClick={() => handleDeactivate(item)}>Деактивировать</button>
                      : <button className="btn btn-sm btn-success" style={{ marginLeft: 4 }} onClick={() => handleActivate(item)}>Активировать</button>
                    }
                    <button className="btn btn-sm btn-danger" style={{ marginLeft: 4 }} onClick={() => { setDeleteId(item.id); setDeleteError(null) }}>Удалить</button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <Pagination page={page} pages={totalPages} onPageChange={setPage} />

      {/* Create/Edit Modal */}
      {showForm && (
        <div className="modal-overlay" onClick={() => setShowForm(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>{editItem ? 'Редактировать товар' : 'Добавить товар'}</h2>
              <button className="modal-close" onClick={() => setShowForm(false)}>✕</button>
            </div>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>Код *</label>
                <input
                  className="form-input"
                  value={form.code}
                  onChange={e => setForm(f => ({ ...f, code: e.target.value }))}
                  placeholder="PROD-001"
                  disabled={!!editItem}
                />
              </div>
              <div className="form-group">
                <label>Наименование *</label>
                <input
                  className="form-input"
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="Картридж для ATM"
                />
              </div>
              <div className="form-group">
                <label>Описание</label>
                <textarea
                  className="form-input"
                  rows={2}
                  value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                />
              </div>
              <div className="form-group">
                <label>Категория *</label>
                <select
                  className="form-select"
                  value={form.category}
                  onChange={e => setForm(f => ({ ...f, category: e.target.value as ProductCategory }))}
                >
                  {(Object.keys(CATEGORY_LABELS) as ProductCategory[]).map(c => (
                    <option key={c} value={c}>{CATEGORY_LABELS[c]}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Единица измерения *</label>
                <select
                  className="form-select"
                  value={form.unit}
                  onChange={e => setForm(f => ({ ...f, unit: e.target.value as ProductUnit }))}
                >
                  {(Object.keys(UNIT_LABELS) as ProductUnit[]).map(u => (
                    <option key={u} value={u}>{UNIT_LABELS[u]}</option>
                  ))}
                </select>
              </div>
              <div className="form-group">
                <label>Цена *</label>
                <input
                  className="form-input"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.unit_price}
                  onChange={e => setForm(f => ({ ...f, unit_price: e.target.value }))}
                  placeholder="0.00"
                />
              </div>
              {formError && <div className="error-message">{formError}</div>}
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowForm(false)}>Отмена</button>
                <button type="submit" className="btn btn-primary" disabled={createMut.isPending || updateMut.isPending}>
                  {createMut.isPending || updateMut.isPending ? 'Сохранение...' : 'Сохранить'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirm Modal */}
      {deleteId !== null && (
        <div className="modal-overlay" onClick={() => setDeleteId(null)}>
          <div className="modal modal-sm" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Удалить товар?</h2>
            </div>
            <p>Это действие нельзя отменить. Если товар используется в документах — удаление будет заблокировано.</p>
            {deleteError && <div className="error-message">{deleteError}</div>}
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setDeleteId(null)}>Отмена</button>
              <button className="btn btn-danger" onClick={handleDelete} disabled={deleteMut.isPending}>
                {deleteMut.isPending ? 'Удаление...' : 'Удалить'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
```

---

## Task 9: Frontend — маршрут и меню

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Layout.tsx`

- [ ] **Шаг 9.1: Добавить маршрут в App.tsx**

Добавить импорт:
```typescript
import ProductCatalogPage from './pages/ProductCatalogPage'
```

Добавить маршрут рядом с `/service-catalog`:
```tsx
{/* Product Catalog */}
<Route path="product-catalog" element={<ProductCatalogPage />} />
```

- [ ] **Шаг 9.2: Добавить ссылку в боковое меню Layout.tsx**

Найти строку с `service-catalog` в меню и изменить запись + добавить новую:

```typescript
{ to: '/service-catalog', icon: '💼', label: 'Услуги' },
{ to: '/product-catalog', icon: '📦', label: 'Товары' },
```

---

## Task 10: Сборка фронтенда и деплой на тестовый стенд

- [ ] **Шаг 10.1: Собрать фронтенд локально**

```bash
cd frontend && npm run build
```

Ожидаемый вывод: `✓ built in Xms`, без ошибок TypeScript.

- [ ] **Шаг 10.2: Финальный коммит**

```bash
git add frontend/src/pages/ProductCatalogPage.tsx \
        frontend/src/hooks/useProductCatalog.ts \
        frontend/src/api/types.ts \
        frontend/src/api/endpoints.ts \
        frontend/src/App.tsx \
        frontend/src/components/Layout.tsx
git commit -m "feat: product catalog page + route + sidebar (UC-102)"
git push
```

- [ ] **Шаг 10.3: Дождаться GitHub Actions**

Workflow выполнит:
1. Тесты pytest
2. Build фронтенда (GitHub Actions runner, 7 GB RAM)
3. scp dist/ → /var/www/servicedesk/
4. Перезапуск backend в Docker
5. alembic upgrade head (применит миграцию 010)

Проверить: https://mikes1.fvds.ru — должна открываться без ошибок.

- [ ] **Шаг 10.4: Прогнать тесты в Docker на сервере**

```bash
# Через SSH: ssh root@188.120.243.122
docker compose exec -T backend pytest tests/ -v --tb=short 2>&1 | tail -30
```

- [ ] **Шаг 10.5: Ручная проверка через интерфейс**

1. Открыть https://mikes1.fvds.ru
2. Войти под admin
3. Проверить: в боковом меню появились «Услуги» и «Товары»
4. Перейти в «Товары» → нажать «+ Добавить товар»
5. Создать: Код=PROD-001, Наименование=«Картридж ATM», Категория=Запчасть, Ед=шт, Цена=2500
6. Убедиться: товар появился в списке, статус «Активен»
7. Нажать «Деактивировать» → статус «Неактивен»
8. Включить «Показать неактивные» → товар виден
9. Нажать «Активировать» → статус снова «Активен»
10. Нажать «Удалить» → подтвердить → товар удалён
