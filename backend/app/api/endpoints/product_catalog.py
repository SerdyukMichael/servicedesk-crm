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
