from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import SparePart, User
from app.api.deps import get_current_user, require_roles, get_client_scope
from app.schemas import SparePartCreate, SparePartUpdate, SparePartResponse, StockAdjust, PaginatedResponse

router = APIRouter()

_WRITE_ROLES = ("admin", "warehouse")
_ADMIN = ("admin",)


@router.get("", response_model=PaginatedResponse[SparePartResponse])
def list_parts(
    category: Optional[str] = Query(None),
    low_stock: bool = Query(False),
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
    total = q.count()
    skip = (page - 1) * size
    items = q.order_by(SparePart.name).offset(skip).limit(size).all()
    pages = max(1, (total + size - 1) // size)
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.post("", response_model=SparePartResponse, status_code=status.HTTP_201_CREATED)
def create_part(
    data: SparePartCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE_ROLES)),
):
    if db.query(SparePart).filter(SparePart.sku == data.sku).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "CONFLICT", "message": "SKU уже используется"},
        )
    part = SparePart(**data.model_dump())
    db.add(part)
    db.commit()
    db.refresh(part)
    return part


@router.get("/{part_id}", response_model=SparePartResponse)
def get_part(
    part_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    if client_scope is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Нет доступа к складу запчастей"},
        )
    part = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Запчасть не найдена"},
        )
    return part


@router.put("/{part_id}", response_model=SparePartResponse)
def update_part(
    part_id: int,
    data: SparePartUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE_ROLES)),
):
    part = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Запчасть не найдена"},
        )
    update_data = data.model_dump(exclude_none=True)
    if "sku" in update_data:
        conflict = db.query(SparePart).filter(SparePart.sku == update_data["sku"], SparePart.id != part_id).first()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "CONFLICT", "message": "SKU уже используется"},
            )
    for k, v in update_data.items():
        setattr(part, k, v)
    db.commit()
    db.refresh(part)
    return part


@router.delete("/{part_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_part(
    part_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_ADMIN)),
):
    part = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Запчасть не найдена"},
        )
    part.is_active = False
    db.commit()


@router.post("/{part_id}/adjust", response_model=SparePartResponse)
def adjust_stock(
    part_id: int,
    data: StockAdjust,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE_ROLES)),
):
    part = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not part:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Запчасть не найдена"},
        )
    new_qty = part.quantity + data.delta
    if new_qty < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "BR_VIOLATION",
                "message": f"Недостаточно на складе: доступно {part.quantity} {part.unit}",
            },
        )
    part.quantity = new_qty
    db.commit()
    db.refresh(part)
    return part
