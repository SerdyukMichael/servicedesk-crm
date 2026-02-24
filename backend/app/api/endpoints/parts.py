from typing import List, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.models import SparePart, PartsUsage, ServiceRequest
from app.api.deps import get_current_user

router = APIRouter()


# ─── Schemas ────────────────────────────────────────────────────────────────

class PartCreate(BaseModel):
    name: str
    part_number: Optional[str] = None
    catalog_id: Optional[int] = None
    vendor_id: Optional[int] = None
    quantity: int = 0
    unit: str = "шт"
    cost_price: Optional[Decimal] = None
    sale_price: Optional[Decimal] = None
    min_quantity: int = 0
    location: Optional[str] = None
    notes: Optional[str] = None


class PartOut(BaseModel):
    id: int
    name: str
    part_number: Optional[str]
    catalog_id: Optional[int]
    vendor_id: Optional[int]
    quantity: int
    unit: str
    cost_price: Optional[Decimal]
    sale_price: Optional[Decimal]
    min_quantity: int
    location: Optional[str]

    class Config:
        from_attributes = True


class UsePartRequest(BaseModel):
    request_id: int
    quantity: int
    unit_price: Decimal
    notes: Optional[str] = None


class ReceiveRequest(BaseModel):
    quantity: int
    notes: Optional[str] = None


class UsageOut(BaseModel):
    id: int
    request_id: int
    part_id: int
    quantity: int
    unit_price: Decimal
    used_by: int
    notes: Optional[str]

    class Config:
        from_attributes = True


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/", response_model=List[PartOut])
def list_parts(
    search: Optional[str] = Query(None),
    low_stock: bool = Query(False, description="Только позиции с остатком ниже минимума"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(SparePart)
    if search:
        q = q.filter(
            SparePart.name.ilike(f"%{search}%") |
            SparePart.part_number.ilike(f"%{search}%")
        )
    if low_stock:
        q = q.filter(SparePart.quantity <= SparePart.min_quantity)
    return q.order_by(SparePart.name).all()


@router.post("/", response_model=PartOut)
def create_part(
    data: PartCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = SparePart(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/low-stock", response_model=List[PartOut])
def get_low_stock(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return (
        db.query(SparePart)
        .filter(SparePart.quantity <= SparePart.min_quantity)
        .order_by(SparePart.name)
        .all()
    )


@router.get("/{part_id}", response_model=PartOut)
def get_part(
    part_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not obj:
        raise HTTPException(404, "Запчасть не найдена")
    return obj


@router.put("/{part_id}", response_model=PartOut)
def update_part(
    part_id: int,
    data: PartCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not obj:
        raise HTTPException(404, "Запчасть не найдена")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{part_id}/receive", response_model=PartOut)
def receive_parts(
    part_id: int,
    data: ReceiveRequest,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """Поступление запчастей на склад."""
    part = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not part:
        raise HTTPException(404, "Запчасть не найдена")
    if data.quantity <= 0:
        raise HTTPException(400, "Количество должно быть больше нуля")
    part.quantity += data.quantity
    db.commit()
    db.refresh(part)
    return part


@router.post("/{part_id}/use", response_model=UsageOut)
def use_part(
    part_id: int,
    data: UsePartRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Списание запчасти на заявку."""
    part = db.query(SparePart).filter(SparePart.id == part_id).first()
    if not part:
        raise HTTPException(404, "Запчасть не найдена")
    if data.quantity <= 0:
        raise HTTPException(400, "Количество должно быть больше нуля")
    if part.quantity < data.quantity:
        raise HTTPException(
            400, f"Недостаточно на складе: доступно {part.quantity} {part.unit}"
        )
    req = db.query(ServiceRequest).filter(ServiceRequest.id == data.request_id).first()
    if not req:
        raise HTTPException(404, "Заявка не найдена")

    usage = PartsUsage(
        part_id=part_id,
        request_id=data.request_id,
        quantity=data.quantity,
        unit_price=data.unit_price,
        used_by=current_user.id,
        notes=data.notes,
    )
    part.quantity -= data.quantity
    db.add(usage)
    db.commit()
    db.refresh(usage)
    return usage


@router.get("/{part_id}/usages", response_model=List[UsageOut])
def get_part_usages(
    part_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return (
        db.query(PartsUsage)
        .filter(PartsUsage.part_id == part_id)
        .order_by(PartsUsage.used_at.desc())
        .all()
    )
