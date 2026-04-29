from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Warehouse, WarehouseStock, SparePart, User
from app.api.deps import get_current_user, require_roles
from app.schemas import (
    WarehouseCreate, WarehouseUpdate, WarehouseResponse,
    WarehouseStockResponse, PaginatedResponse,
)

router = APIRouter()

_ADMIN = ("admin",)
_WRITE = ("admin", "svc_mgr")


@router.get("", response_model=List[WarehouseResponse])
def list_warehouses(
    type: Optional[str] = Query(None),
    active_only: bool = Query(True),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Warehouse)
    if active_only:
        q = q.filter(Warehouse.is_active.is_(True))
    if type:
        q = q.filter(Warehouse.type == type)
    return q.order_by(Warehouse.type, Warehouse.name).all()


@router.post("", response_model=WarehouseResponse, status_code=status.HTTP_201_CREATED)
def create_warehouse(
    data: WarehouseCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_ADMIN)),
):
    wh = Warehouse(**data.model_dump())
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh


@router.get("/{warehouse_id}", response_model=WarehouseResponse)
def get_warehouse(
    warehouse_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not wh:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            detail={"error": "NOT_FOUND", "message": "Склад не найден"})
    return wh


@router.put("/{warehouse_id}", response_model=WarehouseResponse)
def update_warehouse(
    warehouse_id: int,
    data: WarehouseUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_ADMIN)),
):
    wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not wh:
        raise HTTPException(status.HTTP_404_NOT_FOUND,
                            detail={"error": "NOT_FOUND", "message": "Склад не найден"})
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(wh, k, v)
    db.commit()
    db.refresh(wh)
    return wh


# ── Stock view ────────────────────────────────────────────────────────────────

@router.get("/stock/list", response_model=PaginatedResponse[WarehouseStockResponse])
def list_warehouse_stock(
    warehouse_id: Optional[int] = Query(None),
    part_id: Optional[int] = Query(None),
    low_stock: bool = Query(False),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = (
        db.query(WarehouseStock)
        .join(Warehouse, WarehouseStock.warehouse_id == Warehouse.id)
        .join(SparePart, WarehouseStock.part_id == SparePart.id)
        .filter(Warehouse.is_active.is_(True), SparePart.is_active.is_(True))
    )
    if warehouse_id:
        q = q.filter(WarehouseStock.warehouse_id == warehouse_id)
    if part_id:
        q = q.filter(WarehouseStock.part_id == part_id)
    if low_stock:
        q = q.filter(WarehouseStock.quantity <= SparePart.min_quantity)

    total = q.count()
    skip = (page - 1) * size
    rows = q.order_by(SparePart.name).offset(skip).limit(size).all()
    pages = max(1, (total + size - 1) // size)

    items = []
    for row in rows:
        items.append(WarehouseStockResponse(
            id=row.id,
            warehouse_id=row.warehouse_id,
            warehouse_name=row.warehouse.name,
            warehouse_type=row.warehouse.type,
            part_id=row.part_id,
            part_sku=row.part.sku,
            part_name=row.part.name,
            part_unit=row.part.unit,
            part_category=row.part.category,
            part_min_quantity=row.part.min_quantity,
            quantity=row.quantity,
            unit_price_snapshot=row.unit_price_snapshot,
        ))
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)
