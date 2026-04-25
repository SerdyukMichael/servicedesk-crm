import csv
import json
from datetime import datetime
from io import StringIO
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_db, require_roles
from app.models import AuditLog, User
from app.schemas import AuditLogResponse, PaginatedResponse

router = APIRouter()
_ROLES = ("admin", "director")


def _build_query(
    db: Session,
    user_id: Optional[int],
    action: Optional[str],
    entity_type: Optional[str],
    date_from: Optional[datetime],
    date_to: Optional[datetime],
    ip_address: Optional[str],
):
    q = db.query(AuditLog).options(joinedload(AuditLog.user))
    if user_id is not None:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if date_from:
        q = q.filter(AuditLog.created_at >= date_from)
    if date_to:
        q = q.filter(AuditLog.created_at <= date_to)
    if ip_address:
        q = q.filter(AuditLog.ip_address == ip_address)
    return q.order_by(AuditLog.created_at.desc())


@router.get("", response_model=PaginatedResponse[AuditLogResponse])
def list_audit_log(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    ip_address: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_ROLES)),
):
    q = _build_query(db, user_id, action, entity_type, date_from, date_to, ip_address)
    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    pages = max(1, (total + size - 1) // size)
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.get("/export")
def export_audit_log_csv(
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    ip_address: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_ROLES)),
):
    q = _build_query(db, user_id, action, entity_type, date_from, date_to, ip_address)

    def generate():
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "id", "created_at", "user_id", "user_email", "user_name",
            "action", "entity_type", "entity_id", "ip_address",
            "old_values", "new_values",
        ])
        yield buf.getvalue()
        buf.seek(0)
        buf.truncate(0)

        for row in q.yield_per(500):
            writer.writerow([
                row.id,
                row.created_at.isoformat() if row.created_at else "",
                row.user_id or "",
                row.user.email if row.user else "",
                row.user.full_name if row.user else "",
                row.action,
                row.entity_type,
                row.entity_id or "",
                row.ip_address or "",
                json.dumps(row.old_values, ensure_ascii=False) if row.old_values else "",
                json.dumps(row.new_values, ensure_ascii=False) if row.new_values else "",
            ])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate(0)

    return StreamingResponse(
        generate(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
    )
