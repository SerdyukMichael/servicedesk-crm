from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.models import Vendor, PurchaseOrder, PurchaseOrderItem
from app.api.deps import get_current_user, require_manager

router = APIRouter()


# ─── Helpers ────────────────────────────────────────────────────────────────

def _next_po_number(db: Session) -> str:
    year = datetime.now().year
    count = db.query(PurchaseOrder).filter(
        PurchaseOrder.number.like(f"PO-{year}-%")
    ).count()
    return f"PO-{year}-{count + 1:05d}"


PO_TRANSITIONS = {
    "draft":     ["sent", "cancelled"],
    "sent":      ["confirmed", "cancelled"],
    "confirmed": ["received", "cancelled"],
    "received":  [],
    "cancelled": [],
}


# ─── Schemas ────────────────────────────────────────────────────────────────

class VendorCreate(BaseModel):
    name: str
    country: Optional[str] = None
    inn: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None


class VendorOut(BaseModel):
    id: int
    name: str
    country: Optional[str]
    inn: Optional[str]
    contact_name: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    website: Optional[str]

    class Config:
        from_attributes = True


class POItemCreate(BaseModel):
    item_type: str = "part"
    catalog_id: Optional[int] = None
    part_id: Optional[int] = None
    description: str
    quantity: int
    unit_price: Decimal


class POCreate(BaseModel):
    vendor_id: int
    order_date: date
    expected_date: Optional[date] = None
    currency: str = "RUB"
    notes: Optional[str] = None
    items: List[POItemCreate] = []


class POStatusUpdate(BaseModel):
    status: str
    received_date: Optional[date] = None


class POItemOut(BaseModel):
    id: int
    item_type: str
    catalog_id: Optional[int]
    part_id: Optional[int]
    description: str
    quantity: int
    unit_price: Decimal
    total: Decimal

    class Config:
        from_attributes = True


class POOut(BaseModel):
    id: int
    number: str
    vendor_id: int
    status: str
    order_date: date
    expected_date: Optional[date]
    received_date: Optional[date]
    total_amount: Optional[Decimal]
    currency: str
    notes: Optional[str]
    items: List[POItemOut]

    class Config:
        from_attributes = True


# ─── Vendor Endpoints ────────────────────────────────────────────────────────

@router.get("/", response_model=List[VendorOut])
def list_vendors(
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(Vendor)
    if search:
        q = q.filter(Vendor.name.ilike(f"%{search}%"))
    return q.order_by(Vendor.name).all()


@router.post("/", response_model=VendorOut)
def create_vendor(
    data: VendorCreate,
    db: Session = Depends(get_db),
    _=Depends(require_manager),
):
    obj = Vendor(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{vendor_id}", response_model=VendorOut)
def get_vendor(
    vendor_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not obj:
        raise HTTPException(404, "Вендор не найден")
    return obj


@router.put("/{vendor_id}", response_model=VendorOut)
def update_vendor(
    vendor_id: int,
    data: VendorCreate,
    db: Session = Depends(get_db),
    _=Depends(require_manager),
):
    obj = db.query(Vendor).filter(Vendor.id == vendor_id).first()
    if not obj:
        raise HTTPException(404, "Вендор не найден")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{vendor_id}/orders", response_model=List[POOut])
def list_vendor_orders(
    vendor_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    return (
        db.query(PurchaseOrder)
        .filter(PurchaseOrder.vendor_id == vendor_id)
        .order_by(PurchaseOrder.order_date.desc())
        .all()
    )


# ─── Purchase Order Endpoints ────────────────────────────────────────────────

@router.post("/orders", response_model=POOut)
def create_order(
    data: POCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_manager),
):
    order = PurchaseOrder(
        number=_next_po_number(db),
        vendor_id=data.vendor_id,
        order_date=data.order_date,
        expected_date=data.expected_date,
        currency=data.currency,
        notes=data.notes,
        created_by=current_user.id,
    )
    db.add(order)
    db.flush()

    total = Decimal("0")
    for item_data in data.items:
        item_total = (
            Decimal(str(item_data.quantity)) * item_data.unit_price
        ).quantize(Decimal("0.01"))
        total += item_total
        item = PurchaseOrderItem(
            order_id=order.id,
            total=item_total,
            **item_data.model_dump(),
        )
        db.add(item)

    order.total_amount = total
    db.commit()
    db.refresh(order)
    return order


@router.get("/orders", response_model=List[POOut])
def list_orders(
    status: Optional[str] = Query(None),
    vendor_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(PurchaseOrder)
    if status:
        q = q.filter(PurchaseOrder.status == status)
    if vendor_id:
        q = q.filter(PurchaseOrder.vendor_id == vendor_id)
    return q.order_by(PurchaseOrder.order_date.desc()).all()


@router.get("/orders/{order_id}", response_model=POOut)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not obj:
        raise HTTPException(404, "Заказ поставщику не найден")
    return obj


@router.patch("/orders/{order_id}/status", response_model=POOut)
def update_order_status(
    order_id: int,
    data: POStatusUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_manager),
):
    obj = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not obj:
        raise HTTPException(404, "Заказ поставщику не найден")
    allowed = PO_TRANSITIONS.get(obj.status, [])
    if data.status not in allowed:
        raise HTTPException(
            400, f"Переход из статуса '{obj.status}' в '{data.status}' недопустим"
        )
    obj.status = data.status
    if data.status == "received" and data.received_date:
        obj.received_date = data.received_date
    db.commit()
    db.refresh(obj)
    return obj
