from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.models import Invoice, InvoiceItem
from app.api.deps import get_current_user, require_manager

router = APIRouter()


# ─── Helpers ────────────────────────────────────────────────────────────────

def _next_invoice_number(db: Session) -> str:
    year = datetime.now().year
    count = db.query(Invoice).filter(Invoice.number.like(f"SCH-{year}-%")).count()
    return f"SCH-{year}-{count + 1:05d}"


INVOICE_TRANSITIONS = {
    "draft":     ["sent", "cancelled"],
    "sent":      ["paid", "cancelled"],
    "paid":      [],
    "cancelled": [],
}


def _recalculate(invoice: Invoice) -> None:
    subtotal = sum(item.total for item in invoice.items)
    vat = (subtotal * invoice.vat_rate / 100).quantize(Decimal("0.01"))
    invoice.subtotal = subtotal
    invoice.vat_amount = vat
    invoice.total_amount = subtotal + vat


# ─── Schemas ────────────────────────────────────────────────────────────────

class ItemCreate(BaseModel):
    description: str
    quantity: Decimal = Decimal("1")
    unit: str = "шт"
    unit_price: Decimal
    sort_order: int = 0


class InvoiceCreate(BaseModel):
    client_id: int
    type: str = "service"
    issue_date: date
    due_date: Optional[date] = None
    vat_rate: Decimal = Decimal("20")
    notes: Optional[str] = None
    items: List[ItemCreate] = []


class InvoiceStatusUpdate(BaseModel):
    status: str


class ItemOut(BaseModel):
    id: int
    description: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    total: Decimal
    sort_order: int

    class Config:
        from_attributes = True


class InvoiceOut(BaseModel):
    id: int
    number: str
    client_id: int
    type: str
    status: str
    issue_date: date
    due_date: Optional[date]
    subtotal: Decimal
    vat_rate: Decimal
    vat_amount: Decimal
    total_amount: Decimal
    notes: Optional[str]
    created_by: int
    items: List[ItemOut]

    class Config:
        from_attributes = True


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/", response_model=List[InvoiceOut])
def list_invoices(
    client_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(Invoice)
    if client_id:
        q = q.filter(Invoice.client_id == client_id)
    if status:
        q = q.filter(Invoice.status == status)
    return q.order_by(Invoice.issue_date.desc()).all()


@router.post("/", response_model=InvoiceOut)
def create_invoice(
    data: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    invoice = Invoice(
        number=_next_invoice_number(db),
        client_id=data.client_id,
        type=data.type,
        issue_date=data.issue_date,
        due_date=data.due_date,
        vat_rate=data.vat_rate,
        notes=data.notes,
        created_by=current_user.id,
        subtotal=Decimal("0"),
        vat_amount=Decimal("0"),
        total_amount=Decimal("0"),
    )
    db.add(invoice)
    db.flush()

    for item_data in data.items:
        total = (item_data.quantity * item_data.unit_price).quantize(Decimal("0.01"))
        item = InvoiceItem(
            invoice_id=invoice.id,
            total=total,
            **item_data.model_dump(),
        )
        db.add(item)

    db.flush()
    db.refresh(invoice)
    _recalculate(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not obj:
        raise HTTPException(404, "Счёт не найден")
    return obj


@router.patch("/{invoice_id}/status", response_model=InvoiceOut)
def update_invoice_status(
    invoice_id: int,
    data: InvoiceStatusUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_manager),
):
    obj = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not obj:
        raise HTTPException(404, "Счёт не найден")
    allowed = INVOICE_TRANSITIONS.get(obj.status, [])
    if data.status not in allowed:
        raise HTTPException(
            400, f"Переход из статуса '{obj.status}' в '{data.status}' недопустим"
        )
    obj.status = data.status
    if data.status == "paid":
        obj.paid_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{invoice_id}/items", response_model=InvoiceOut)
def add_invoice_item(
    invoice_id: int,
    data: ItemCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(404, "Счёт не найден")
    if invoice.status != "draft":
        raise HTTPException(400, "Редактировать можно только счета в статусе 'Черновик'")
    total = (data.quantity * data.unit_price).quantize(Decimal("0.01"))
    item = InvoiceItem(invoice_id=invoice_id, total=total, **data.model_dump())
    db.add(item)
    db.flush()
    db.refresh(invoice)
    _recalculate(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.delete("/{invoice_id}/items/{item_id}", response_model=InvoiceOut)
def remove_invoice_item(
    invoice_id: int,
    item_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(404, "Счёт не найден")
    if invoice.status != "draft":
        raise HTTPException(400, "Редактировать можно только счета в статусе 'Черновик'")
    item = (
        db.query(InvoiceItem)
        .filter(InvoiceItem.id == item_id, InvoiceItem.invoice_id == invoice_id)
        .first()
    )
    if not item:
        raise HTTPException(404, "Позиция счёта не найдена")
    db.delete(item)
    db.flush()
    db.refresh(invoice)
    _recalculate(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice
