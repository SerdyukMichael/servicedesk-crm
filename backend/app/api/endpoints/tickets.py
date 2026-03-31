"""
Ticket management endpoint — full CRUD + sub-resources.
"""

from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.core.database import get_db
from app.models import Ticket, TicketComment, TicketFile, WorkAct, User, RepairHistory, Equipment, EquipmentModel, TicketStatusHistory

# Ticket type → repair history work_type
_TICKET_TYPE_TO_WORK_TYPE = {
    "repair":       "unplanned_repair",
    "maintenance":  "planned_maintenance",
    "installation": "installation",
    "diagnostics":  "unplanned_repair",
}
from app.api.deps import get_current_user, require_roles, _get_user_roles
from app.schemas import (
    TicketCreate, TicketUpdate, TicketResponse, TicketAssign,
    TicketStatusChange, CommentCreate, CommentResponse,
    WorkActCreate, WorkActResponse, PaginatedResponse,
    TicketStatusHistoryResponse,
)

router = APIRouter()

_MANAGE_ROLES = ("admin", "svc_mgr")
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
    "closed":       [],
    "cancelled":    [],
}


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
):
    user_roles = _get_user_roles(current_user)
    q = db.query(Ticket).options(joinedload(Ticket.client), joinedload(Ticket.assignee), joinedload(Ticket.creator), joinedload(Ticket.equipment).joinedload(Equipment.model)).filter(Ticket.is_deleted.is_(False))

    # Engineers see only their own tickets
    if not any(r in user_roles for r in ("admin", "svc_mgr", "director")):
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
):
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
):
    ticket = (
        db.query(Ticket)
        .options(joinedload(Ticket.client), joinedload(Ticket.assignee), joinedload(Ticket.creator), joinedload(Ticket.equipment).joinedload(Equipment.model))
        .filter(Ticket.id == ticket_id, Ticket.is_deleted.is_(False))
        .first()
    )
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
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.is_deleted.is_(False)).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Заявка не найдена"},
        )
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
    _: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.is_deleted.is_(False)).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Заявка не найдена"},
        )
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


@router.patch("/{ticket_id}/status", response_model=TicketResponse)
@router.post("/{ticket_id}/status", response_model=TicketResponse)
def change_ticket_status(
    ticket_id: int,
    data: TicketStatusChange,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.is_deleted.is_(False)).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Заявка не найдена"},
        )
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
    prev_status = ticket.status
    ticket.status = data.status
    if data.status in ("closed", "completed"):
        ticket.closed_at = datetime.utcnow()
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
    ticket = db.query(Ticket).options(joinedload(Ticket.client), joinedload(Ticket.assignee), joinedload(Ticket.creator), joinedload(Ticket.equipment).joinedload(Equipment.model)).filter(Ticket.id == ticket_id).first()
    return ticket


# ─── Status History ───────────────────────────────────────────────────────────

@router.get("/{ticket_id}/status-history", response_model=list[TicketStatusHistoryResponse])
def get_status_history(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.is_deleted.is_(False)).first()
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "NOT_FOUND", "message": "Заявка не найдена"})
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
    _: User = Depends(get_current_user),
):
    _require_ticket(db, ticket_id)
    return (
        db.query(TicketComment)
        .filter(TicketComment.ticket_id == ticket_id)
        .order_by(TicketComment.created_at)
        .all()
    )


@router.post("/{ticket_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED)
def add_comment(
    ticket_id: int,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_ticket(db, ticket_id)
    comment = TicketComment(ticket_id=ticket_id, user_id=current_user.id, text=data.text)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


# ─── Attachments ─────────────────────────────────────────────────────────────

@router.post("/{ticket_id}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    ticket_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_ticket(db, ticket_id)
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
    attachment = TicketFile(
        ticket_id=ticket_id,
        uploaded_by=current_user.id,
        file_name=file.filename or "file",
        file_type=file.content_type,
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
):
    _require_ticket(db, ticket_id)
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
    inline_types = ("image/", "text/")
    disposition = "inline" if any(mime.startswith(t) for t in inline_types) else "attachment"
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
):
    """Download endpoint without JWT auth — accessible via direct browser link."""
    f = db.query(TicketFile).filter(TicketFile.id == file_id, TicketFile.ticket_id == ticket_id).first()
    if not f:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Файл не найден"},
        )
    mime = f.file_type or "application/octet-stream"
    # Images and text open inline in the browser tab; other types are downloaded
    inline_types = ("image/", "text/")
    disposition = "inline" if any(mime.startswith(t) for t in inline_types) else "attachment"
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
    db.commit()
    db.refresh(act)
    return act


@router.get("/{ticket_id}/work-act", response_model=WorkActResponse)
def get_work_act(
    ticket_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    act = db.query(WorkAct).filter(WorkAct.ticket_id == ticket_id).first()
    if not act:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Акт выполненных работ не найден"},
        )
    return act


@router.post("/{ticket_id}/work-act/{act_id}/sign", response_model=WorkActResponse)
def sign_work_act(
    ticket_id: int,
    act_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("svc_mgr", "admin")),
):
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

def _require_ticket(db: Session, ticket_id: int) -> Ticket:
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id, Ticket.is_deleted.is_(False)).first()
    if not ticket:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Заявка не найдена"},
        )
    return ticket
