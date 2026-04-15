# Price Lists & Act Items Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить справочник услуг (ServiceCatalog), структурированные позиции акта (WorkActItem), привязку строк счёта к справочникам, и эндпоинт создания счёта из акта.

**Architecture:** Три новые таблицы (`service_catalog`, `work_act_items`) + расширение `invoice_items`. Поле `WorkAct.parts_used` (JSON) оставляем для совместимости — новые позиции хранятся в `work_act_items`. Старый JSON не мигрируем. API полностью backwards-compatible: существующие тесты не ломаются.

**Tech Stack:** Python 3.11, FastAPI 0.111, SQLAlchemy 2.0, Alembic, Pydantic v2, pytest + httpx (SQLite in-memory для тестов).

---

## File Map

### Создать новые файлы

- `backend/app/api/endpoints/service_catalog.py` — CRUD для ServiceCatalog
- `backend/alembic/versions/010_service_catalog_and_act_items.py` — миграция
- `backend/tests/test_service_catalog.py` — тесты справочника услуг
- `backend/tests/test_work_act_items.py` — тесты позиций акта
- `backend/tests/test_invoice_from_act.py` — тест создания счёта из акта

### Изменить существующие файлы

- `backend/app/models/__init__.py` — добавить `ServiceCatalog`, `WorkActItem`; расширить `InvoiceItem`
- `backend/app/schemas/__init__.py` — добавить схемы для `ServiceCatalog`, `WorkActItem`; расширить `InvoiceItemCreate/Response`
- `backend/app/api/endpoints/tickets.py` — обновить эндпоинт work-act (принимать `items`)
- `backend/app/api/endpoints/invoices.py` — добавить `POST /invoices/from-act/{ticket_id}`
- `backend/app/api/router.py` — зарегистрировать `service_catalog` router
- `backend/tests/conftest.py` — добавить фабрику `make_service_catalog_item`

---

## Task 1: Модели ServiceCatalog и WorkActItem

**Files:**
- Modify: `backend/app/models/__init__.py`

- [ ] **Step 1.1: Написать тест — модели создаются и сохраняются в БД**

```python
# backend/tests/test_service_catalog.py
import pytest
from tests.conftest import make_admin, admin_headers
from app.models import ServiceCatalog, WorkActItem, WorkAct

def test_service_catalog_model_created(db):
    item = ServiceCatalog(
        code="SRV-001",
        name="Диагностика",
        category="diagnostics",
        unit="шт",
        unit_price=1500.00,
        currency="RUB",
        is_active=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    assert item.id is not None
    assert item.code == "SRV-001"
    assert item.is_active is True
```

- [ ] **Step 1.2: Запустить тест — убедиться, что FAIL (модель не существует)**

```bash
docker compose exec backend pytest tests/test_service_catalog.py::test_service_catalog_model_created -v
```

Ожидаем: `ImportError` или `FAILED`

- [ ] **Step 1.3: Добавить модели в `backend/app/models/__init__.py`**

Добавить после блока `# ── Work Acts` (после строки 300):

```python
# ── Service Catalog ───────────────────────────────────────────────────────────
class ServiceCatalog(Base):
    __tablename__ = "service_catalog"

    id:          Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    code:        Mapped[str]            = mapped_column(String(32), unique=True, nullable=False, index=True)
    name:        Mapped[str]            = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]]  = mapped_column(Text)
    category:    Mapped[str]            = mapped_column(
        Enum("repair", "maintenance", "diagnostics", "visit", "other",
             name="service_category_enum"),
        default="other", nullable=False
    )
    unit:        Mapped[str]            = mapped_column(
        Enum("pcs", "hour", "visit", "kit", name="service_unit_enum"),
        default="pcs", nullable=False
    )
    unit_price:  Mapped[Decimal]        = mapped_column(DECIMAL(12, 2), nullable=False, default=0)
    currency:    Mapped[str]            = mapped_column(String(3), default="RUB", nullable=False)
    is_active:   Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    created_at:  Mapped[datetime]       = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at:  Mapped[datetime]       = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    work_act_items: Mapped[List["WorkActItem"]] = relationship("WorkActItem", back_populates="service")


# ── Work Act Items ─────────────────────────────────────────────────────────────
class WorkActItem(Base):
    __tablename__ = "work_act_items"

    id:           Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_act_id:  Mapped[int]            = mapped_column(ForeignKey("work_acts.id", ondelete="CASCADE"), nullable=False)
    item_type:    Mapped[str]            = mapped_column(
        Enum("service", "part", name="work_act_item_type_enum"),
        nullable=False
    )
    service_id:   Mapped[Optional[int]]  = mapped_column(ForeignKey("service_catalog.id", ondelete="RESTRICT"), nullable=True)
    part_id:      Mapped[Optional[int]]  = mapped_column(ForeignKey("spare_parts.id", ondelete="RESTRICT"), nullable=True)
    name:         Mapped[str]            = mapped_column(String(255), nullable=False)
    quantity:     Mapped[Decimal]        = mapped_column(DECIMAL(10, 3), nullable=False, default=1)
    unit:         Mapped[str]            = mapped_column(String(16), nullable=False, default="шт")
    unit_price:   Mapped[Decimal]        = mapped_column(DECIMAL(12, 2), nullable=False, default=0)
    total:        Mapped[Decimal]        = mapped_column(DECIMAL(14, 2), nullable=False, default=0)
    sort_order:   Mapped[int]            = mapped_column(Integer, default=0, nullable=False)

    work_act: Mapped["WorkAct"]                = relationship("WorkAct", back_populates="items")
    service:  Mapped[Optional["ServiceCatalog"]] = relationship("ServiceCatalog", back_populates="work_act_items")
    part:     Mapped[Optional["SparePart"]]      = relationship("SparePart")
```

Добавить в `WorkAct` relationship (после строки signer):

```python
    items: Mapped[List["WorkActItem"]] = relationship("WorkActItem", back_populates="work_act", cascade="all, delete-orphan", order_by="WorkActItem.sort_order")
```

Расширить `InvoiceItem` — добавить поля `item_type`, `service_id`, `part_id` (после поля `sort_order`):

```python
    item_type:   Mapped[Optional[str]] = mapped_column(
        Enum("service", "part", "manual", name="invoice_item_type_enum"),
        nullable=True
    )
    service_id:  Mapped[Optional[int]] = mapped_column(ForeignKey("service_catalog.id", ondelete="RESTRICT"), nullable=True)
    part_id:     Mapped[Optional[int]] = mapped_column(ForeignKey("spare_parts.id", ondelete="RESTRICT"), nullable=True)
```

Добавить в `__all__` в конце файла:
```python
    "ServiceCatalog",
    "WorkActItem",
```

- [ ] **Step 1.4: Запустить тест — убедиться, что PASS**

```bash
docker compose exec backend pytest tests/test_service_catalog.py::test_service_catalog_model_created -v
```

Ожидаем: `PASSED`

- [ ] **Step 1.5: Commit**

```bash
git add backend/app/models/__init__.py backend/tests/test_service_catalog.py
git commit -m "feat: add ServiceCatalog and WorkActItem models"
```

---

## Task 2: Миграция Alembic

**Files:**
- Create: `backend/alembic/versions/010_service_catalog_and_act_items.py`

- [ ] **Step 2.1: Создать файл миграции**

```bash
docker compose exec backend alembic revision --autogenerate -m "service_catalog_and_act_items"
```

Переименовать сгенерированный файл в `010_service_catalog_and_act_items.py` (или взять имя как есть).

- [ ] **Step 2.2: Проверить содержимое миграции**

Миграция должна содержать создание таблиц `service_catalog`, `work_act_items` и добавление колонок `item_type`, `service_id`, `part_id` в `invoice_items`.

Если миграция пустая — проверить, что модели импортированы в `app/models/__init__.py` и `alembic/env.py` импортирует `Base` из `app.core.database`.

- [ ] **Step 2.3: Применить миграцию**

```bash
docker compose exec backend alembic upgrade head
```

Ожидаем: `Running upgrade ... -> ...` без ошибок.

- [ ] **Step 2.4: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat: migration 010 — service_catalog, work_act_items, invoice_item_type"
```

---

## Task 3: Схемы Pydantic

**Files:**
- Modify: `backend/app/schemas/__init__.py`
- Modify: `backend/tests/conftest.py`

- [ ] **Step 3.1: Написать тест — схемы валидируют данные корректно**

Добавить в `backend/tests/test_service_catalog.py`:

```python
from app.schemas import ServiceCatalogCreate, ServiceCatalogResponse

def test_service_catalog_schema_valid():
    data = ServiceCatalogCreate(
        code="SRV-001",
        name="Диагностика",
        category="diagnostics",
        unit="pcs",
        unit_price=1500.00,
    )
    assert data.code == "SRV-001"
    assert data.currency == "RUB"  # default

def test_service_catalog_schema_requires_name():
    with pytest.raises(Exception):
        ServiceCatalogCreate(code="SRV-001", category="other", unit="pcs", unit_price=0)
```

- [ ] **Step 3.2: Запустить — убедиться, что FAIL**

```bash
docker compose exec backend pytest tests/test_service_catalog.py::test_service_catalog_schema_valid -v
```

Ожидаем: `ImportError`

- [ ] **Step 3.3: Добавить схемы в `backend/app/schemas/__init__.py`**

Добавить после блока `# ── Invoices`:

```python
# ── Service Catalog ───────────────────────────────────────────────────────────

class ServiceCatalogCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    category: str = "other"
    unit: str = "pcs"
    unit_price: Decimal = Decimal("0")
    currency: str = "RUB"
    is_active: bool = True


class ServiceCatalogUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None


class ServiceCatalogResponse(BaseModel):
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


# ── Work Act Items ─────────────────────────────────────────────────────────────

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

Расширить `WorkActCreate` — добавить поле `items`:

```python
class WorkActCreate(BaseModel):
    work_description: Optional[str] = None
    parts_used: Optional[Any] = None       # оставить для совместимости
    total_time_minutes: Optional[int] = None
    items: List[WorkActItemCreate] = []    # новые структурированные позиции
```

Расширить `WorkActResponse` — добавить поле `items`:

```python
class WorkActResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    engineer_id: int
    work_description: Optional[str]
    parts_used: Optional[Any]
    total_time_minutes: Optional[int]
    signed_by: Optional[int]
    signed_at: Optional[datetime]
    created_at: datetime
    items: List[WorkActItemResponse] = []
```

Расширить `InvoiceItemCreate` — добавить опциональные поля:

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
```

Расширить `InvoiceItemResponse` — добавить поля:

```python
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
```

- [ ] **Step 3.4: Добавить фабрику в `backend/tests/conftest.py`**

```python
from app.models import ServiceCatalog  # добавить в импорт

def make_service_catalog_item(db, code="SRV-001", name="Диагностика", unit_price=1500.00):
    item = ServiceCatalog(
        code=code,
        name=name,
        category="diagnostics",
        unit="pcs",
        unit_price=unit_price,
        currency="RUB",
        is_active=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
```

- [ ] **Step 3.5: Запустить тест — убедиться, что PASS**

```bash
docker compose exec backend pytest tests/test_service_catalog.py -v
```

Ожидаем: все PASSED

- [ ] **Step 3.6: Убедиться, что старые тесты не сломались**

```bash
docker compose exec backend pytest tests/ -v --tb=short 2>&1 | tail -20
```

Ожидаем: все старые тесты PASSED

- [ ] **Step 3.7: Commit**

```bash
git add backend/app/schemas/__init__.py backend/tests/conftest.py backend/tests/test_service_catalog.py
git commit -m "feat: schemas for ServiceCatalog, WorkActItem, extend InvoiceItem"
```

---

## Task 4: API — CRUD ServiceCatalog

**Files:**
- Create: `backend/app/api/endpoints/service_catalog.py`
- Modify: `backend/app/api/router.py`

- [ ] **Step 4.1: Написать тесты для CRUD**

Добавить в `backend/tests/test_service_catalog.py`:

```python
from tests.conftest import make_admin, make_engineer, admin_headers, auth_headers, make_service_catalog_item

class TestServiceCatalogCRUD:
    def test_list_empty(self, client, db):
        headers = admin_headers(db)
        r = client.get("/api/v1/service-catalog", headers=headers)
        assert r.status_code == 200
        data = r.json()
        assert data["items"] == []
        assert data["total"] == 0

    def test_create_item(self, client, db):
        headers = admin_headers(db)
        r = client.post("/api/v1/service-catalog", json={
            "code": "SRV-001",
            "name": "Диагностика банкомата",
            "category": "diagnostics",
            "unit": "pcs",
            "unit_price": "1500.00",
        }, headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert data["code"] == "SRV-001"
        assert data["unit_price"] == "1500.00"
        assert data["is_active"] is True

    def test_create_duplicate_code_fails(self, client, db):
        headers = admin_headers(db)
        make_service_catalog_item(db, code="SRV-001")
        r = client.post("/api/v1/service-catalog", json={
            "code": "SRV-001",
            "name": "Другое",
            "category": "other",
            "unit": "pcs",
            "unit_price": "100",
        }, headers=headers)
        assert r.status_code == 409

    def test_update_item(self, client, db):
        headers = admin_headers(db)
        item = make_service_catalog_item(db, code="SRV-002", name="Выезд")
        r = client.patch(f"/api/v1/service-catalog/{item.id}", json={
            "unit_price": "2000.00",
        }, headers=headers)
        assert r.status_code == 200
        assert r.json()["unit_price"] == "2000.00"

    def test_deactivate_item(self, client, db):
        headers = admin_headers(db)
        item = make_service_catalog_item(db, code="SRV-003")
        r = client.patch(f"/api/v1/service-catalog/{item.id}", json={"is_active": False}, headers=headers)
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    def test_deactivated_hidden_in_list_by_default(self, client, db):
        headers = admin_headers(db)
        item = make_service_catalog_item(db, code="SRV-004")
        client.patch(f"/api/v1/service-catalog/{item.id}", json={"is_active": False}, headers=headers)
        r = client.get("/api/v1/service-catalog", headers=headers)
        ids = [i["id"] for i in r.json()["items"]]
        assert item.id not in ids

    def test_show_inactive_with_param(self, client, db):
        headers = admin_headers(db)
        item = make_service_catalog_item(db, code="SRV-005")
        client.patch(f"/api/v1/service-catalog/{item.id}", json={"is_active": False}, headers=headers)
        r = client.get("/api/v1/service-catalog?include_inactive=true", headers=headers)
        ids = [i["id"] for i in r.json()["items"]]
        assert item.id in ids

    def test_engineer_cannot_create(self, client, db):
        eng = make_engineer(db)
        headers = auth_headers(eng.id, eng.roles)
        r = client.post("/api/v1/service-catalog", json={
            "code": "SRV-X",
            "name": "Test",
            "category": "other",
            "unit": "pcs",
            "unit_price": "100",
        }, headers=headers)
        assert r.status_code == 403
```

- [ ] **Step 4.2: Запустить — убедиться, что FAIL (роутер не существует)**

```bash
docker compose exec backend pytest tests/test_service_catalog.py::TestServiceCatalogCRUD -v
```

Ожидаем: `404` или `ImportError`

- [ ] **Step 4.3: Создать `backend/app/api/endpoints/service_catalog.py`**

```python
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ServiceCatalog, WorkActItem, InvoiceItem, User
from app.api.deps import get_current_user, require_roles
from app.schemas import (
    ServiceCatalogCreate, ServiceCatalogUpdate, ServiceCatalogResponse,
    PaginatedResponse,
)

router = APIRouter()

_WRITE_ROLES = ("admin", "svc_mgr")


@router.get("", response_model=PaginatedResponse[ServiceCatalogResponse])
def list_service_catalog(
    include_inactive: bool = Query(False),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(ServiceCatalog)
    if not include_inactive:
        q = q.filter(ServiceCatalog.is_active.is_(True))
    if category:
        q = q.filter(ServiceCatalog.category == category)
    total = q.count()
    skip = (page - 1) * size
    items = q.order_by(ServiceCatalog.name).offset(skip).limit(size).all()
    pages = max(1, (total + size - 1) // size)
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.post("", response_model=ServiceCatalogResponse, status_code=status.HTTP_201_CREATED)
def create_service_catalog_item(
    data: ServiceCatalogCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE_ROLES)),
):
    if db.query(ServiceCatalog).filter(ServiceCatalog.code == data.code).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "CONFLICT", "message": f"Код {data.code} уже используется"},
        )
    item = ServiceCatalog(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("/{item_id}", response_model=ServiceCatalogResponse)
def get_service_catalog_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return _get_or_404(db, item_id)


@router.patch("/{item_id}", response_model=ServiceCatalogResponse)
def update_service_catalog_item(
    item_id: int,
    data: ServiceCatalogUpdate,
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
def delete_service_catalog_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin",)),
):
    item = _get_or_404(db, item_id)
    # Check if used in any work act items or invoice items (BR-P-006)
    in_acts = db.query(WorkActItem).filter(WorkActItem.service_id == item_id).first()
    in_invoices = db.query(InvoiceItem).filter(InvoiceItem.service_id == item_id).first()
    if in_acts or in_invoices:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "IN_USE", "message": "Позиция используется в документах. Деактивируйте её"},
        )
    db.delete(item)
    db.commit()


def _get_or_404(db: Session, item_id: int) -> ServiceCatalog:
    item = db.query(ServiceCatalog).filter(ServiceCatalog.id == item_id).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Позиция прайс-листа не найдена"},
        )
    return item
```

- [ ] **Step 4.4: Зарегистрировать роутер в `backend/app/api/router.py`**

```python
from app.api.endpoints import (
    auth, users, clients, equipment, tickets,
    work_templates, parts, vendors, invoices, notifications,
    service_catalog,  # добавить
)

# добавить строку:
api_router.include_router(service_catalog.router, prefix="/service-catalog", tags=["Прайс-лист услуг"])
```

- [ ] **Step 4.5: Запустить тесты — убедиться, что PASS**

```bash
docker compose exec backend pytest tests/test_service_catalog.py -v
```

Ожидаем: все PASSED

- [ ] **Step 4.6: Убедиться, что старые тесты не сломались**

```bash
docker compose exec backend pytest tests/ -v --tb=short 2>&1 | tail -20
```

- [ ] **Step 4.7: Commit**

```bash
git add backend/app/api/endpoints/service_catalog.py backend/app/api/router.py backend/tests/test_service_catalog.py
git commit -m "feat: service catalog CRUD endpoint with BR-P-006 delete guard"
```

---

## Task 5: Позиции акта (WorkActItem) в эндпоинте work-act

**Files:**
- Modify: `backend/app/api/endpoints/tickets.py`
- Create: `backend/tests/test_work_act_items.py`

- [ ] **Step 5.1: Написать тесты**

```python
# backend/tests/test_work_act_items.py
import pytest
from decimal import Decimal
from tests.conftest import (
    make_admin, make_engineer, admin_headers, auth_headers,
    make_client, make_equipment_model, make_equipment, make_ticket,
    make_spare_part, make_service_catalog_item,
)


def _make_ticket_in_progress(db, client, admin):
    """Helper: создать заявку и перевести в in_progress."""
    model = make_equipment_model(db)
    equip = make_equipment(db, client.id, model.id)
    ticket = make_ticket(db, client.id, equip.id, admin.id)
    db.execute(
        __import__('sqlalchemy').text("UPDATE tickets SET status='in_progress' WHERE id=:id"),
        {"id": ticket.id}
    )
    db.commit()
    db.refresh(ticket)
    return ticket


class TestWorkActItems:
    def test_create_act_with_service_item(self, client, db):
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        ticket = _make_ticket_in_progress(db, cli, admin)
        svc = make_service_catalog_item(db, code="SRV-001", unit_price=1500.00)

        r = client.post(f"/api/v1/tickets/{ticket.id}/work-act", json={
            "work_description": "Диагностика проведена",
            "items": [
                {
                    "item_type": "service",
                    "service_id": svc.id,
                    "name": "Диагностика банкомата",
                    "quantity": "1",
                    "unit": "шт",
                    "unit_price": "1500.00",
                }
            ]
        }, headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["item_type"] == "service"
        assert data["items"][0]["total"] == "1500.00"

    def test_create_act_with_part_item(self, client, db):
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        ticket = _make_ticket_in_progress(db, cli, admin)
        part = make_spare_part(db, sku="PART-001", quantity=5)

        r = client.post(f"/api/v1/tickets/{ticket.id}/work-act", json={
            "work_description": "Замена ролика",
            "items": [
                {
                    "item_type": "part",
                    "part_id": part.id,
                    "name": "Ролик подачи",
                    "quantity": "2",
                    "unit": "шт",
                    "unit_price": "500.00",
                }
            ]
        }, headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert len(data["items"]) == 1
        assert data["items"][0]["total"] == "1000.00"

    def test_create_act_with_mixed_items(self, client, db):
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        ticket = _make_ticket_in_progress(db, cli, admin)
        svc = make_service_catalog_item(db, code="SRV-002", unit_price=2000.00)
        part = make_spare_part(db, sku="PART-002", quantity=10)

        r = client.post(f"/api/v1/tickets/{ticket.id}/work-act", json={
            "work_description": "Полный ремонт",
            "items": [
                {
                    "item_type": "service",
                    "service_id": svc.id,
                    "name": "Ремонт",
                    "quantity": "1",
                    "unit": "шт",
                    "unit_price": "2000.00",
                },
                {
                    "item_type": "part",
                    "part_id": part.id,
                    "name": "Картридж",
                    "quantity": "3",
                    "unit": "шт",
                    "unit_price": "300.00",
                }
            ]
        }, headers=headers)
        assert r.status_code == 201
        assert len(r.json()["items"]) == 2

    def test_get_act_returns_items(self, client, db):
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        ticket = _make_ticket_in_progress(db, cli, admin)
        svc = make_service_catalog_item(db, code="SRV-003", unit_price=500.00)

        client.post(f"/api/v1/tickets/{ticket.id}/work-act", json={
            "work_description": "Test",
            "items": [{
                "item_type": "service",
                "service_id": svc.id,
                "name": "Выезд",
                "quantity": "1",
                "unit": "шт",
                "unit_price": "500.00",
            }]
        }, headers=headers)

        r = client.get(f"/api/v1/tickets/{ticket.id}/work-act", headers=headers)
        assert r.status_code == 200
        assert len(r.json()["items"]) == 1

    def test_act_without_items_still_works(self, client, db):
        """Backward compatibility: акт можно сохранить без items."""
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        ticket = _make_ticket_in_progress(db, cli, admin)

        r = client.post(f"/api/v1/tickets/{ticket.id}/work-act", json={
            "work_description": "Только описание, без позиций",
        }, headers=headers)
        assert r.status_code == 201
        assert r.json()["items"] == []
```

- [ ] **Step 5.2: Запустить — убедиться, что FAIL**

```bash
docker compose exec backend pytest tests/test_work_act_items.py -v
```

Ожидаем: FAILED (items не возвращаются)

- [ ] **Step 5.3: Найти в `backend/app/api/endpoints/tickets.py` эндпоинт создания work-act**

Найти функцию `create_work_act` (ищи `POST.*work-act` или `work_act`). В ней нужно после сохранения `WorkAct` добавить сохранение `WorkActItem`:

```python
from app.models import WorkActItem  # добавить в импорт

# В функции create_work_act, после db.add(work_act) и db.flush():
for i, item_data in enumerate(data.items):
    total = (item_data.quantity * item_data.unit_price).quantize(Decimal("0.01"))
    act_item = WorkActItem(
        work_act_id=work_act.id,
        item_type=item_data.item_type,
        service_id=item_data.service_id,
        part_id=item_data.part_id,
        name=item_data.name,
        quantity=item_data.quantity,
        unit=item_data.unit,
        unit_price=item_data.unit_price,
        total=total,
        sort_order=item_data.sort_order if item_data.sort_order else i,
    )
    db.add(act_item)
```

Также добавить импорт `Decimal` если его нет: `from decimal import Decimal`

- [ ] **Step 5.4: Убедиться, что GET work-act возвращает items**

Найти функцию `get_work_act`. Убедиться что `WorkAct` загружается с relationship `items`. Если нет — добавить `joinedload`:

```python
from sqlalchemy.orm import joinedload

work_act = (
    db.query(WorkAct)
    .options(joinedload(WorkAct.items))
    .filter(WorkAct.ticket_id == ticket_id)
    .first()
)
```

- [ ] **Step 5.5: Запустить тесты — убедиться, что PASS**

```bash
docker compose exec backend pytest tests/test_work_act_items.py -v
```

Ожидаем: все PASSED

- [ ] **Step 5.6: Убедиться, что старые тесты не сломались**

```bash
docker compose exec backend pytest tests/ -v --tb=short 2>&1 | tail -20
```

- [ ] **Step 5.7: Commit**

```bash
git add backend/app/api/endpoints/tickets.py backend/tests/test_work_act_items.py
git commit -m "feat: work act items — structured service/part lines with prices"
```

---

## Task 6: Эндпоинт создания счёта из акта

**Files:**
- Modify: `backend/app/api/endpoints/invoices.py`
- Create: `backend/tests/test_invoice_from_act.py`

- [ ] **Step 6.1: Написать тесты**

```python
# backend/tests/test_invoice_from_act.py
import pytest
from tests.conftest import (
    make_admin, auth_headers, make_client, make_equipment_model,
    make_equipment, make_ticket, make_service_catalog_item, make_spare_part,
)


def _create_act_with_items(client_fixture, db, ticket_id, headers, svc_id, part_id):
    return client_fixture.post(f"/api/v1/tickets/{ticket_id}/work-act", json={
        "work_description": "Ремонт завершён",
        "items": [
            {
                "item_type": "service",
                "service_id": svc_id,
                "name": "Диагностика",
                "quantity": "1",
                "unit": "шт",
                "unit_price": "1500.00",
            },
            {
                "item_type": "part",
                "part_id": part_id,
                "name": "Ролик",
                "quantity": "2",
                "unit": "шт",
                "unit_price": "500.00",
            }
        ]
    }, headers=headers)


class TestInvoiceFromAct:
    def test_create_invoice_from_act(self, client, db):
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        model = make_equipment_model(db)
        equip = make_equipment(db, cli.id, model.id)
        ticket = make_ticket(db, cli.id, equip.id, admin.id)

        from sqlalchemy import text
        db.execute(text("UPDATE tickets SET status='in_progress' WHERE id=:id"), {"id": ticket.id})
        db.commit()

        svc = make_service_catalog_item(db, code="SRV-INV-01", unit_price=1500.00)
        part = make_spare_part(db, sku="PART-INV-01", quantity=10)

        _create_act_with_items(client, db, ticket.id, headers, svc.id, part.id)

        r = client.post(f"/api/v1/invoices/from-act/{ticket.id}", headers=headers)
        assert r.status_code == 201
        data = r.json()
        assert data["client_id"] == cli.id
        assert data["ticket_id"] == ticket.id
        assert data["status"] == "draft"
        assert len(data["items"]) == 2
        # проверяем суммы
        totals = {item["name"]: item["total"] for item in data["items"]}
        assert totals["Диагностика"] == "1500.00"
        assert totals["Ролик"] == "1000.00"

    def test_cannot_create_invoice_without_act(self, client, db):
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        model = make_equipment_model(db)
        equip = make_equipment(db, cli.id, model.id)
        ticket = make_ticket(db, cli.id, equip.id, admin.id)

        r = client.post(f"/api/v1/invoices/from-act/{ticket.id}", headers=headers)
        assert r.status_code == 404

    def test_invoice_from_act_preserves_prices(self, client, db):
        """Изменение прайса после создания акта не влияет на счёт (BR-P-003)."""
        admin = make_admin(db)
        headers = auth_headers(admin.id, admin.roles)
        cli = make_client(db)
        model = make_equipment_model(db)
        equip = make_equipment(db, cli.id, model.id)
        ticket = make_ticket(db, cli.id, equip.id, admin.id)

        from sqlalchemy import text
        db.execute(text("UPDATE tickets SET status='in_progress' WHERE id=:id"), {"id": ticket.id})
        db.commit()

        svc = make_service_catalog_item(db, code="SRV-INV-02", unit_price=1500.00)

        client.post(f"/api/v1/tickets/{ticket.id}/work-act", json={
            "work_description": "Test",
            "items": [{
                "item_type": "service",
                "service_id": svc.id,
                "name": "Диагностика",
                "quantity": "1",
                "unit": "шт",
                "unit_price": "1500.00",
            }]
        }, headers=headers)

        # Меняем цену в прайсе
        client.patch(f"/api/v1/service-catalog/{svc.id}", json={"unit_price": "9999.00"}, headers=headers)

        # Создаём счёт из акта — цены должны быть из акта (1500), не из прайса (9999)
        r = client.post(f"/api/v1/invoices/from-act/{ticket.id}", headers=headers)
        assert r.status_code == 201
        assert r.json()["items"][0]["unit_price"] == "1500.00"
```

- [ ] **Step 6.2: Запустить — убедиться, что FAIL**

```bash
docker compose exec backend pytest tests/test_invoice_from_act.py -v
```

Ожидаем: `404` на `POST /invoices/from-act/{ticket_id}`

- [ ] **Step 6.3: Добавить эндпоинт в `backend/app/api/endpoints/invoices.py`**

Добавить импорты в начало файла:

```python
from app.models import Invoice, InvoiceItem, User, Ticket, WorkAct, WorkActItem  # добавить Ticket, WorkAct, WorkActItem
```

Добавить эндпоинт перед функцией `_get_or_404`:

```python
@router.post("/from-act/{ticket_id}", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice_from_act(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_WRITE_ROLES)),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.is_deleted.is_(False)).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Заявка не найдена"},
        )
    work_act = db.query(WorkAct).filter(WorkAct.ticket_id == ticket_id).first()
    if not work_act:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Акт выполненных работ не найден. Сначала сохраните акт"},
        )

    invoice = Invoice(
        number=_next_invoice_number(db),
        client_id=ticket.client_id,
        ticket_id=ticket_id,
        type="mixed",
        issue_date=date.today(),
        vat_rate=Decimal("20.00"),
        created_by=current_user.id,
        subtotal=Decimal("0"),
        vat_amount=Decimal("0"),
        total_amount=Decimal("0"),
    )
    db.add(invoice)
    db.flush()

    act_items = (
        db.query(WorkActItem)
        .filter(WorkActItem.work_act_id == work_act.id)
        .order_by(WorkActItem.sort_order)
        .all()
    )
    for i, act_item in enumerate(act_items):
        inv_item = InvoiceItem(
            invoice_id=invoice.id,
            description=act_item.name,
            quantity=act_item.quantity,
            unit=act_item.unit,
            unit_price=act_item.unit_price,
            total=act_item.total,
            sort_order=i,
            item_type=act_item.item_type,
            service_id=act_item.service_id,
            part_id=act_item.part_id,
        )
        db.add(inv_item)

    db.flush()
    db.refresh(invoice)
    _recalculate(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice
```

- [ ] **Step 6.4: Запустить тесты — убедиться, что PASS**

```bash
docker compose exec backend pytest tests/test_invoice_from_act.py -v
```

Ожидаем: все PASSED

- [ ] **Step 6.5: Запустить все тесты**

```bash
docker compose exec backend pytest tests/ -v --tb=short 2>&1 | tail -30
```

Ожидаем: все PASSED (или только старые падают по несвязанным причинам)

- [ ] **Step 6.6: Commit**

```bash
git add backend/app/api/endpoints/invoices.py backend/tests/test_invoice_from_act.py
git commit -m "feat: POST /invoices/from-act/{ticket_id} — create invoice from work act"
```

---

## Task 7: Финальная проверка и обновление CURRENT_TASK.md

- [ ] **Step 7.1: Прогнать все тесты**

```bash
docker compose exec backend pytest tests/ -v 2>&1 | tail -30
```

Ожидаем: все PASSED. Если есть FAILED — разобраться и починить перед завершением.

- [ ] **Step 7.2: Обновить CURRENT_TASK.md**

Записать: реализация завершена, следующий шаг — frontend.

- [ ] **Step 7.3: Финальный коммит**

```bash
git add CURRENT_TASK.md
git commit -m "docs: update CURRENT_TASK after pricelists backend implementation"
```

---

## Self-Review Checklist

- [x] **BR-F-110** (ServiceCatalog) — Task 1, Task 3, Task 4
- [x] **BR-F-111** (автоподстановка цены из прайса на фронте — через GET /service-catalog и GET /parts) — Task 4
- [x] **BR-F-112** (запрет удаления используемых позиций) — Task 4, шаг 4.3 (`DELETE` guard)
- [x] **BR-F-113** (структурированные строки акта с фиксацией цен) — Task 5
- [x] **BR-F-410** (счёт из акта) — Task 6
- [x] **BR-F-411** (item_type/service_id/part_id в invoice_items) — Task 3, Task 6
- [x] **BR-P-001** (услуги и запчасти в акте) — Task 5
- [x] **BR-P-002** (услуги и запчасти в счёте) — Task 6
- [x] **BR-P-003** (цены фиксируются в акте) — тест `test_invoice_from_act_preserves_prices`
- [x] **BR-P-004** (счёт из акта копирует позиции) — Task 6
- [x] **BR-P-006** (запрет удаления при наличии связей) — Task 4
- [x] Backwards compatibility: `WorkAct.parts_used` остаётся, `items=[]` по умолчанию — Task 5 тест `test_act_without_items_still_works`
- [x] RBAC: только admin/svc_mgr могут создавать/редактировать справочник — Task 4 тест `test_engineer_cannot_create`
