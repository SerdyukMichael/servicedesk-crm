"""
Ticket management endpoint — full CRUD + sub-resources.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional
from urllib.parse import quote

import magic as _magic

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.models import Ticket, TicketComment, TicketFile, WorkAct, WorkActItem, User, RepairHistory, Equipment, EquipmentModel, TicketStatusHistory, Invoice, InvoiceItem

# MIME-типы, запрещённые к загрузке (хранимый XSS через SVG/HTML/JS)
_BLOCKED_MIME_TYPES = frozenset({
    "text/html",
    "image/svg+xml",
    "application/javascript",
    "text/javascript",
    "application/x-javascript",
    "application/xhtml+xml",
})

# MIME-типы, которые браузер открывает inline (остальные — attachment)
_SAFE_INLINE_TYPES = frozenset({
    "image/jpeg",
    "image/png",
    "image/gif",
    "application/pdf",
})


def _validate_and_detect_mime(data: bytes) -> str:
    """Определить реальный MIME по содержимому файла. Отклонить опасные типы."""
    detected = _magic.from_buffer(data, mime=True) or "application/octet-stream"
    if detected in _BLOCKED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "VALIDATION_ERROR",
                "message": "Тип файла не разрешён для загрузки",
            },
        )
    # Дополнительная проверка: блокировать SVG/скриптовый контент в текстовых файлах
    if detected.startswith("text/"):
        sample = data[:2048].lower()
        if b"<svg" in sample or b"<script" in sample or b"<!doctype html" in sample:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "VALIDATION_ERROR",
                    "message": "Тип файла не разрешён для загрузки",
                },
            )
    return detected


# Ticket type → repair history work_type
_TICKET_TYPE_TO_WORK_TYPE = {
    "repair":       "unplanned_repair",
    "maintenance":  "planned_maintenance",
    "installation": "installation",
    "diagnostics":  "unplanned_repair",
}
from app.api.deps import get_current_user, require_roles, _get_user_roles, get_client_scope
from app.core.email import send_email
from app.schemas import (
    TicketCreate, TicketUpdate, TicketResponse, TicketAssign,
    TicketStatusChange, CommentCreate, CommentResponse,
    WorkActCreate, WorkActUpdate, WorkActResponse, PaginatedResponse,
    TicketStatusHistoryResponse,
)

router = APIRouter()

_MANAGE_ROLES = ("admin", "svc_mgr", "client_user")
_ADMIN = ("admin",)

# SLA hours by priority
_SLA_HOURS = {"critical": 4, "high": 8, "medium": 24, "low": 72}

# Valid status transitions
_TRANSITIONS = {
    "new":          ["assigned", "cancelled"],
    "assigned":     ["in_progress", "cancelled"],
    "in_progress":  ["waiting_part", "on_review", "completed"],
    "waiting_part": ["in_progress", "cancelled"],
    "on_review":    ["completed", "in_progress"],
    "completed":    ["closed", "in_progress"],
    "closed":       ["in_progress"],   # BR-F-125: возобновление
    "cancelled":    [],
}

# BR-F-125: роли, которым разрешено возобновлять заявку (closed/completed → in_progress)
_REOPEN_ROLES = frozenset({"admin", "svc_mgr", "client_user"})
_REOPEN_SOURCES = frozenset({"closed", "completed"})


def _next_ticket_number(db: Session) -> str:
    today = datetime.utcnow().strftime("%Y%m%d")
    count = db.query(Ticket).filter(Ticket.number.like(f"T-{today}-%")).count()
    return f"T-{today}-{count + 1:04d}"


def _calc_sla(priority: str, created_at: datetime) -> datetime:
    hours = _SLA_HOURS.get(priority, 24)
    return created_at + timedelta(hours=hours)


# ─── Tickets ─────────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[TicketResponse])
def list_tickets(
    ticket_status: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = Query(None),
    client_id: Optional[int] = Query(None),
    equipment_id: Optional[int] = Query(None),
    assigned_to: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    user_roles = _get_user_roles(current_user)
    q = db.query(Ticket).options(joinedload(Ticket.client), joinedload(Ticket.assignee), joinedload(Ticket.creator), joinedload(Ticket.equipment).joinedload(Equipment.model)).filter(Ticket.is_deleted.is_(False))

    # client_user sees only their organisation's tickets
    if client_scope is not None:
        q = q.filter(Ticket.client_id == client_scope)
    # Engineers see only their own tickets
    elif not any(r in user_roles for r in ("admin", "svc_mgr", "director", "manager", "sales_mgr")):
        q = q.filter(Ticket.assigned_to == current_user.id)

    if ticket_status:
        q = q.filter(Ticket.status == ticket_status)
    if priority:
        q = q.filter(Ticket.priority == priority)
    if client_id:
        q = q.filter(Ticket.client_id == client_id)
    if equipment_id:
        q = q.filter(Ticket.equipment_id == equipment_id)
    if assigned_to:
        q = q.filter(Ticket.assigned_to == assigned_to)
    if search:
        q = q.filter(Ticket.title.ilike(f"%{search}%"))

    total = q.count()
    skip = (page - 1) * size
    items = q.order_by(Ticket.created_at.desc()).offset(skip).limit(size).all()
    pages = max(1, (total + size - 1) // size)
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.post("", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(
    data: TicketCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    # client_user can only create tickets for their own organisation
    if client_scope is not None and data.client_id != client_scope:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Можно создавать заявки только для своей организации"},
        )
    now = datetime.utcnow()
    ticket = Ticket(
        number=_next_ticket_number(db),
        client_id=data.client_id,
        equipment_id=data.equipment_id,
        created_by=current_user.id,
        title=data.title,
        description=data.description,
        type=data.type,
        priority=data.priority,
        status="new",
        sla_deadline=_calc_sla(data.priority, now),
        work_template_id=data.work_template_id,
    )
    db.add(ticket)
    db.flush()  # get ticket.id before commit
    db.add(TicketStatusHistory(
        ticket_id=ticket.id,
        from_status=None,
        to_status="new",
        changed_by=current_user.id,
    ))
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/{ticket_id}", response_model=TicketResponse)
def get_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    q = (
        db.query(Ticket)
        .options(joinedload(Ticket.client), joinedload(Ticket.assignee), joinedload(Ticket.creator), joinedload(Ticket.equipment).joinedload(Equipment.model))
        .filter(Ticket.id == ticket_id, Ticket.is_deleted.is_(False))
    )
    if client_scope is not None:
        q = q.filter(Ticket.client_id == client_scope)
    ticket = q.first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Заявка не найдена"},
        )
    return ticket


@router.put("/{ticket_id}", response_model=TicketResponse)
def update_ticket(
    ticket_id: int,
    data: TicketUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_MANAGE_ROLES)),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    ticket = _require_ticket(db, ticket_id, client_scope)
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(ticket, k, v)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_ADMIN)),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.is_deleted.is_(False)).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Заявка не найдена"},
        )
    ticket.is_deleted = True
    db.commit()


@router.patch("/{ticket_id}/assign", response_model=TicketResponse)
@router.post("/{ticket_id}/assign", response_model=TicketResponse)
def assign_ticket(
    ticket_id: int,
    data: TicketAssign,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin", "svc_mgr")),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    ticket = _require_ticket(db, ticket_id, client_scope)
    engineer = db.query(User).filter(User.id == data.engineer_id, User.is_deleted.is_(False)).first()
    if not engineer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Инженер не найден"},
        )
    ticket.assigned_to = data.engineer_id
    if ticket.status == "new":
        db.add(TicketStatusHistory(
            ticket_id=ticket_id,
            from_status="new",
            to_status="assigned",
            changed_by=_.id,
        ))
        ticket.status = "assigned"
    db.commit()
    ticket = db.query(Ticket).options(joinedload(Ticket.client), joinedload(Ticket.assignee), joinedload(Ticket.creator), joinedload(Ticket.equipment).joinedload(Equipment.model)).filter(Ticket.id == ticket_id).first()
    return ticket


_STATUS_ROLES = ("admin", "svc_mgr", "engineer", "client_user")

@router.patch("/{ticket_id}/status", response_model=TicketResponse)
@router.post("/{ticket_id}/status", response_model=TicketResponse)
def change_ticket_status(
    ticket_id: int,
    data: TicketStatusChange,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_STATUS_ROLES)),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    ticket = _require_ticket(db, ticket_id, client_scope)
    allowed = _TRANSITIONS.get(ticket.status, [])
    if data.status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "BR_VIOLATION",
                "message": f"Переход из '{ticket.status}' в '{data.status}' недопустим",
            },
        )
    if data.status == "assigned" and not ticket.assigned_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "BR_VIOLATION",
                "message": "Необходимо назначить инженера на заявку",
            },
        )
    # BR-F-125: возобновление заявки — только привилегированные роли
    if data.status == "in_progress" and ticket.status in _REOPEN_SOURCES:
        user_roles = set(_get_user_roles(current_user))
        if not user_roles & _REOPEN_ROLES:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "FORBIDDEN",
                    "message": "Возобновить заявку могут только администратор, менеджер или клиент",
                },
            )
    prev_status = ticket.status
    ticket.status = data.status
    if data.status in ("closed", "completed"):
        ticket.closed_at = datetime.utcnow()
    # BR-F-125: сброс closed_at при возобновлении
    if data.status == "in_progress" and prev_status in _REOPEN_SOURCES:
        ticket.closed_at = None
    db.add(TicketStatusHistory(
        ticket_id=ticket_id,
        from_status=prev_status,
        to_status=data.status,
        changed_by=current_user.id,
        comment=data.comment if data.comment else None,
    ))
    # BR-F-906: авто-создание записи истории ремонтов при завершении заявки
    if data.status == "completed" and ticket.equipment_id:
        already_exists = db.query(RepairHistory).filter(
            RepairHistory.ticket_id == ticket_id
        ).first()
        if not already_exists:
            work_act = db.query(WorkAct).filter(WorkAct.ticket_id == ticket_id).first()
            description = (
                (work_act.work_description if work_act else None)
                or ticket.description
            )
            parts = work_act.parts_used if work_act else None
            db.add(RepairHistory(
                ticket_id=ticket_id,
                equipment_id=ticket.equipment_id,
                action_type=_TICKET_TYPE_TO_WORK_TYPE.get(ticket.type, "unplanned_repair"),
                description=description,
                performed_by=ticket.assigned_to,
                performed_at=datetime.utcnow(),
                parts_used=parts,
            ))
    db.commit()
    ticket = db.query(Ticket).options(
        joinedload(Ticket.client),
        joinedload(Ticket.assignee),
        joinedload(Ticket.creator),
        joinedload(Ticket.equipment).joinedload(Equipment.model),
    ).filter(Ticket.id == ticket_id).first()

    # BR-F-125: email-уведомление при возобновлении заявки
    if data.status == "in_progress" and prev_status in _REOPEN_SOURCES and ticket:
        recipients: list[str] = []
        if ticket.creator and ticket.creator.email:
            recipients.append(ticket.creator.email)
        if ticket.assignee and ticket.assignee.email and ticket.assignee.email not in recipients:
            recipients.append(ticket.assignee.email)
        # Инициатор-менеджер/admin также получает копию, если не дублирует
        if current_user.email and current_user.email not in recipients:
            initiator_roles = set(_get_user_roles(current_user))
            if initiator_roles & {"admin", "svc_mgr"}:
                recipients.append(current_user.email)
        subject = f"Заявка {ticket.number} возобновлена"
        body = (
            f"<p>Заявка <b>{ticket.number}</b> «{ticket.title}» "
            f"возобновлена и переведена в статус <b>В работе</b>.</p>"
            f"<p>Инициатор: {current_user.full_name}</p>"
            f"<p><a href=\"https://mikes1.fvds.ru/tickets/{ticket.id}\">Открыть заявку</a></p>"
        )
        background_tasks.add_task(send_email, recipients, subject, body)

    return ticket


# ─── Status History ───────────────────────────────────────────────────────────

@router.get("/{ticket_id}/status-history", response_model=list[TicketStatusHistoryResponse])
def get_status_history(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    ticket = _require_ticket(db, ticket_id, client_scope)
    return (
        db.query(TicketStatusHistory)
        .options(joinedload(TicketStatusHistory.changer))
        .filter(TicketStatusHistory.ticket_id == ticket_id)
        .order_by(TicketStatusHistory.changed_at)
        .all()
    )


# ─── Comments ─────────────────────────────────────────────────────────────────

@router.get("/{ticket_id}/comments", response_model=list[CommentResponse])
def list_comments(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    _require_ticket(db, ticket_id, client_scope)
    q = (
        db.query(TicketComment)
        .options(joinedload(TicketComment.user))
        .filter(TicketComment.ticket_id == ticket_id)
    )
    # client_user does not see internal comments
    if client_scope is not None:
        q = q.filter(TicketComment.is_internal.is_(False))
    return q.order_by(TicketComment.created_at).all()


@router.post("/{ticket_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(
    ticket_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    _require_ticket(db, ticket_id, client_scope)
    comment = TicketComment(
        ticket_id=ticket_id,
        user_id=current_user.id,
        text=data.text,
        is_internal=data.is_internal,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    db.refresh(comment, attribute_names=["user"])
    return comment


# ─── Attachments ─────────────────────────────────────────────────────────────

@router.post("/{ticket_id}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    _require_ticket(db, ticket_id, client_scope)
    max_bytes = settings.max_file_size_mb * 1024 * 1024
    data = await file.read()
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "VALIDATION_ERROR",
                "message": f"Файл превышает максимальный размер {settings.max_file_size_mb} МБ",
            },
        )
    detected_mime = _validate_and_detect_mime(data)
    attachment = TicketFile(
        ticket_id=ticket_id,
        uploaded_by=current_user.id,
        file_name=file.filename or "file",
        file_type=detected_mime,
        file_size=len(data),
        file_data=data,
    )
    db.add(attachment)
    db.commit()
    db.refresh(attachment)
    return {
        "id": attachment.id,
        "ticket_id": ticket_id,
        "filename": attachment.file_name,
        "file_name": attachment.file_name,
        "file_type": attachment.file_type,
        "file_size": attachment.file_size,
        "file_url": f"/api/v1/tickets/{ticket_id}/attachments/{attachment.id}/download",
        "uploaded_by_id": attachment.uploaded_by,
        "created_at": attachment.created_at,
    }


@router.get("/{ticket_id}/attachments")
def list_attachments(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    _require_ticket(db, ticket_id, client_scope)
    files = (
        db.query(TicketFile)
        .filter(TicketFile.ticket_id == ticket_id)
        .order_by(TicketFile.created_at)
        .all()
    )
    return [
        {
            "id": f.id,
            "ticket_id": ticket_id,
            "filename": f.file_name,
            "file_name": f.file_name,
            "file_type": f.file_type,
            "file_size": f.file_size,
            "file_url": f"/api/v1/tickets/{ticket_id}/attachments/{f.id}/download",
            "uploaded_by_id": f.uploaded_by,
            "uploaded_by": f.uploaded_by,
            "created_at": f.created_at,
        }
        for f in files
    ]


@router.get("/{ticket_id}/attachments/{file_id}")
def download_attachment(
    ticket_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    f = db.query(TicketFile).filter(TicketFile.id == file_id, TicketFile.ticket_id == ticket_id).first()
    if not f:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Файл не найден"},
        )
    mime = f.file_type or "application/octet-stream"
    disposition = "inline" if mime in _SAFE_INLINE_TYPES else "attachment"
    encoded_name = quote(f.file_name, safe="")
    return Response(
        content=f.file_data,
        media_type=mime,
        headers={"Content-Disposition": f"{disposition}; filename*=UTF-8''{encoded_name}"},
    )


@router.get("/{ticket_id}/attachments/{file_id}/download")
def download_attachment_direct(
    ticket_id: int,
    file_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    """Download attachment. Requires authentication."""
    _require_ticket(db, ticket_id, client_scope)
    f = db.query(TicketFile).filter(TicketFile.id == file_id, TicketFile.ticket_id == ticket_id).first()
    if not f:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Файл не найден"},
        )
    mime = f.file_type or "application/octet-stream"
    # Только явно безопасные типы открываются inline; всё остальное — attachment
    disposition = "inline" if mime in _SAFE_INLINE_TYPES else "attachment"
    # RFC 5987: encode non-ASCII filename so Cyrillic/etc. don't crash latin-1 header encoding
    encoded_name = quote(f.file_name, safe="")
    content_disposition = f"{disposition}; filename*=UTF-8''{encoded_name}"
    return Response(
        content=f.file_data,
        media_type=mime,
        headers={"Content-Disposition": content_disposition},
    )


# ─── Work Acts ────────────────────────────────────────────────────────────────

@router.post("/{ticket_id}/work-act", response_model=WorkActResponse, status_code=status.HTTP_201_CREATED)
def create_work_act(
    ticket_id: int,
    data: WorkActCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("engineer", "svc_mgr", "admin")),
):
    _require_ticket(db, ticket_id)
    existing = db.query(WorkAct).filter(WorkAct.ticket_id == ticket_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "CONFLICT", "message": "Акт для этой заявки уже существует"},
        )
    act = WorkAct(
        ticket_id=ticket_id,
        engineer_id=current_user.id,
        work_description=data.work_description,
        parts_used=data.parts_used,
        total_time_minutes=data.total_time_minutes,
    )
    db.add(act)
    db.flush()

    for i, item_data in enumerate(data.items):
        total = (item_data.quantity * item_data.unit_price).quantize(Decimal("0.01"))
        act_item = WorkActItem(
            work_act_id=act.id,
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

    db.commit()
    db.refresh(act)
    return act


@router.get("/{ticket_id}/work-act", response_model=WorkActResponse)
def get_work_act(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    _require_ticket(db, ticket_id, client_scope)
    act = (
        db.query(WorkAct)
        .options(joinedload(WorkAct.items))
        .filter(WorkAct.ticket_id == ticket_id)
        .first()
    )
    if not act:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Акт выполненных работ не найден"},
        )
    return act


def _calc_act_total(items: list) -> Decimal:
    """Сумма позиций акта без НДС."""
    return sum((i.total for i in items), Decimal("0"))


def _sync_invoice_from_act(invoice: Invoice, act_items: list, db: Session) -> None:
    """Заменить позиции счёта позициями акта и пересчитать итоги."""
    db.query(InvoiceItem).filter(InvoiceItem.invoice_id == invoice.id).delete()
    db.flush()
    subtotal = Decimal("0")
    for i, act_item in enumerate(act_items):
        total = act_item.total
        db.add(InvoiceItem(
            invoice_id=invoice.id,
            description=act_item.name,
            quantity=act_item.quantity,
            unit=act_item.unit,
            unit_price=act_item.unit_price,
            total=total,
            sort_order=i,
            item_type=act_item.item_type,
            service_id=act_item.service_id,
            part_id=act_item.part_id,
        ))
        subtotal += total
    # Цены в актах уже включают НДС — счёт выставляется без дополнительного начисления
    invoice.subtotal = subtotal
    invoice.vat_amount = Decimal("0.00")
    invoice.total_amount = subtotal


@router.patch("/{ticket_id}/work-act", response_model=WorkActResponse)
def update_work_act(
    ticket_id: int,
    data: WorkActUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("engineer", "svc_mgr", "admin")),
):
    _require_ticket(db, ticket_id)
    act = (
        db.query(WorkAct)
        .options(joinedload(WorkAct.items))
        .filter(WorkAct.ticket_id == ticket_id)
        .first()
    )
    if not act:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Акт выполненных работ не найден"},
        )

    # Guard 1: акт подписан → запрещено всем
    if act.signed_by is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Акт подписан и не может быть изменён"},
        )

    # Guard 2: счёт существует → только admin (BR-F-126)
    user_roles = set(_get_user_roles(current_user))
    all_invoices = (
        db.query(Invoice)
        .filter(Invoice.ticket_id == ticket_id)
        .filter(Invoice.status != "cancelled")
        .order_by(Invoice.created_at.desc())
        .all()
    )
    paid_invoice = next((inv for inv in all_invoices if inv.status == "paid"), None)
    latest_unpaid_invoice = next((inv for inv in all_invoices if inv.status != "paid"), None)

    if all_invoices and "admin" not in user_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "ACT_LOCKED_INVOICE_EXISTS",
                    "message": "Редактирование акта заблокировано: счёт уже создан. Обратитесь к администратору"},
        )

    # Применяем изменения
    if data.work_description is not None:
        act.work_description = data.work_description
    if data.total_time_minutes is not None:
        act.total_time_minutes = data.total_time_minutes
    if data.parts_used is not None:
        act.parts_used = data.parts_used

    new_act_items: list = []   # заполняется ниже при изменении позиций
    if data.items is not None:
        db.query(WorkActItem).filter(WorkActItem.work_act_id == act.id).delete()
        for i, item_data in enumerate(data.items):
            total = (item_data.quantity * item_data.unit_price).quantize(Decimal("0.01"))
            item = WorkActItem(
                work_act_id=act.id,
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
            db.add(item)
            new_act_items.append(item)
        db.flush()

    # Синхронизация счётов (только если изменились позиции)
    if data.items is not None:
        act_total = _calc_act_total(new_act_items)

        # BR-F-127: если есть оплаченный счёт и сумма изменилась → 409
        if paid_invoice is not None and act_total != paid_invoice.subtotal:
            if not data.force_save:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": "INVOICE_PAID_MISMATCH",
                        "message": "Сумма акта изменилась, но счёт уже оплачен. Подтвердите сохранение.",
                        "act_total": str(act_total),
                        "invoice_total": str(paid_invoice.total_amount),
                    },
                )
            # force_save=True: сохраняем акт, оплаченный счёт не трогаем

        # Синхронизируем последний неоплаченный счёт (всегда, независимо от наличия оплаченного)
        if latest_unpaid_invoice is not None:
            _sync_invoice_from_act(latest_unpaid_invoice, new_act_items, db)

    db.commit()
    db.refresh(act)
    return act


@router.post("/{ticket_id}/work-act/sign", response_model=WorkActResponse)
def sign_work_act_by_ticket(
    ticket_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("client_user")),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    """BR-F-116: подписание акта по ticket_id (без явного act_id)."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.is_deleted.is_(False)).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Заявка не найдена"},
        )
    if client_scope is not None and ticket.client_id != client_scope:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Нет доступа к этой заявке"},
        )
    act = db.query(WorkAct).filter(WorkAct.ticket_id == ticket_id).first()
    if not act:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Акт не найден"},
        )
    if act.signed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "BR_VIOLATION", "message": "Акт уже подписан"},
        )
    act.signed_by = current_user.id
    act.signed_at = datetime.utcnow()
    if ticket.status == "in_progress":
        ticket.status = "on_review"
    db.commit()
    db.refresh(act)
    return act


@router.post("/{ticket_id}/work-act/{act_id}/sign", response_model=WorkActResponse)
def sign_work_act(
    ticket_id: int,
    act_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("client_user")),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    # row-level: client_user may only sign acts for their own org's tickets (BR-F-116)
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.is_deleted.is_(False)).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Заявка не найдена"},
        )
    if client_scope is not None and ticket.client_id != client_scope:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Нет доступа к этой заявке"},
        )
    act = db.query(WorkAct).filter(WorkAct.id == act_id, WorkAct.ticket_id == ticket_id).first()
    if not act:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Акт не найден"},
        )
    if act.signed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "BR_VIOLATION", "message": "Акт уже подписан"},
        )
    act.signed_by = current_user.id
    act.signed_at = datetime.utcnow()

    # Transition ticket to on_review
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if ticket and ticket.status == "in_progress":
        ticket.status = "on_review"

    db.commit()
    db.refresh(act)
    return act


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _require_ticket(db: Session, ticket_id: int,
                    client_scope: Optional[int] = None) -> Ticket:
    q = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.is_deleted.is_(False))
    if client_scope is not None:
        q = q.filter(Ticket.client_id == client_scope)
    ticket = q.first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Заявка не найдена"},
        )
    return ticket
