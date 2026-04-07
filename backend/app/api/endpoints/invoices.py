from datetime import datetime, date
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Invoice, InvoiceItem, User, Ticket, WorkAct, WorkActItem
from app.api.deps import get_current_user, require_roles, get_client_scope
from app.schemas import InvoiceCreate, InvoiceUpdate, InvoiceResponse, PaginatedResponse

router = APIRouter()

_READ_ROLES = ("admin", "accountant", "director", "svc_mgr", "client_user")
_WRITE_ROLES = ("admin", "accountant", "svc_mgr")
_ADMIN = ("admin",)


def _next_invoice_number(db: Session) -> str:
    year = datetime.utcnow().year
    count = db.query(Invoice).filter(Invoice.number.like(f"INV-{year}-%")).count()
    return f"INV-{year}-{count + 1:05d}"


def _recalculate(invoice: Invoice) -> None:
    subtotal = sum(item.total for item in invoice.items)
    vat = (subtotal * invoice.vat_rate / 100).quantize(Decimal("0.01"))
    invoice.subtotal = subtotal
    invoice.vat_amount = vat
    invoice.total_amount = subtotal + vat


@router.get("", response_model=PaginatedResponse[InvoiceResponse])
def list_invoices(
    client_id: Optional[int] = Query(None),
    inv_status: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_READ_ROLES)),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    q = db.query(Invoice)
    effective_client_id = client_scope if client_scope is not None else client_id
    if effective_client_id:
        q = q.filter(Invoice.client_id == effective_client_id)
    if inv_status:
        q = q.filter(Invoice.status == inv_status)
    total = q.count()
    skip = (page - 1) * size
    items = q.order_by(Invoice.issue_date.desc()).offset(skip).limit(size).all()
    pages = max(1, (total + size - 1) // size)
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def create_invoice(
    data: InvoiceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_WRITE_ROLES)),
):
    invoice = Invoice(
        number=_next_invoice_number(db),
        client_id=data.client_id,
        ticket_id=data.ticket_id,
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
            description=item_data.description,
            quantity=item_data.quantity,
            unit=item_data.unit,
            unit_price=item_data.unit_price,
            total=total,
            sort_order=item_data.sort_order,
        )
        db.add(item)

    db.flush()
    db.refresh(invoice)
    _recalculate(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_READ_ROLES)),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Счёт не найден"},
        )
    return inv


@router.put("/{invoice_id}", response_model=InvoiceResponse)
def update_invoice(
    invoice_id: int,
    data: InvoiceUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE_ROLES)),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Счёт не найден"},
        )
    update_data = data.model_dump(exclude_none=True)
    items_data = update_data.pop("items", None)
    for k, v in update_data.items():
        setattr(inv, k, v)

    if items_data is not None:
        for old in inv.items:
            db.delete(old)
        db.flush()
        for item_data in items_data:
            total = (item_data["quantity"] * item_data["unit_price"]).quantize(Decimal("0.01"))
            item = InvoiceItem(invoice_id=inv.id, total=total, **item_data)
            db.add(item)
        db.flush()
        db.refresh(inv)
        _recalculate(inv)

    db.commit()
    db.refresh(inv)
    return inv


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_ADMIN)),
):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Счёт не найден"},
        )
    db.delete(inv)
    db.commit()


@router.post("/{invoice_id}/send", response_model=InvoiceResponse)
def send_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE_ROLES)),
):
    inv = _get_or_404(db, invoice_id)
    if inv.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "BR_VIOLATION", "message": "Только черновик можно отправить"},
        )
    inv.status = "sent"
    db.commit()
    db.refresh(inv)
    return inv


@router.post("/{invoice_id}/pay", response_model=InvoiceResponse)
def pay_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE_ROLES)),
):
    inv = _get_or_404(db, invoice_id)
    if inv.status not in ("sent", "overdue"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "BR_VIOLATION", "message": "Оплатить можно только отправленный счёт"},
        )
    inv.status = "paid"
    inv.paid_at = datetime.utcnow()
    db.commit()
    db.refresh(inv)
    return inv


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


def _get_or_404(db: Session, invoice_id: int) -> Invoice:
    inv = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Счёт не найден"},
        )
    return inv
