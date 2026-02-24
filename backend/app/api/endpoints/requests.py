from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.models import ServiceRequest, ClientEquipment
from app.api.deps import get_current_user, require_manager

router = APIRouter()


# ─── Helpers ────────────────────────────────────────────────────────────────

def _next_number(db: Session) -> str:
    year = datetime.now().year
    count = db.query(ServiceRequest).filter(
        ServiceRequest.number.like(f"ZVK-{year}-%")
    ).count()
    return f"ZVK-{year}-{count + 1:05d}"


VALID_TRANSITIONS = {
    "new":         ["assigned", "in_progress", "cancelled"],
    "assigned":    ["in_progress", "cancelled"],
    "in_progress": ["done", "cancelled"],
    "done":        ["closed"],
    "closed":      [],
    "cancelled":   [],
}


# ─── Schemas ────────────────────────────────────────────────────────────────

class RequestCreate(BaseModel):
    client_id: int
    equipment_id: int
    type: str = "repair"
    priority: str = "normal"
    description: str


class RequestUpdate(BaseModel):
    type: Optional[str] = None
    priority: Optional[str] = None
    description: Optional[str] = None
    resolution: Optional[str] = None
    engineer_id: Optional[int] = None


class StatusUpdate(BaseModel):
    status: str
    resolution: Optional[str] = None


class AssignRequest(BaseModel):
    engineer_id: int


class RequestOut(BaseModel):
    id: int
    number: str
    client_id: int
    equipment_id: int
    engineer_id: Optional[int]
    created_by: int
    type: str
    priority: str
    status: str
    description: str
    resolution: Optional[str]
    created_at: Optional[datetime]
    assigned_at: Optional[datetime]
    started_at: Optional[datetime]
    closed_at: Optional[datetime]

    class Config:
        from_attributes = True


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/", response_model=List[RequestOut])
def list_requests(
    status: Optional[str] = Query(None),
    client_id: Optional[int] = Query(None),
    engineer_id: Optional[int] = Query(None),
    priority: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(ServiceRequest)
    if status:
        q = q.filter(ServiceRequest.status == status)
    if client_id:
        q = q.filter(ServiceRequest.client_id == client_id)
    if engineer_id:
        q = q.filter(ServiceRequest.engineer_id == engineer_id)
    if priority:
        q = q.filter(ServiceRequest.priority == priority)
    if type:
        q = q.filter(ServiceRequest.type == type)
    return q.order_by(ServiceRequest.created_at.desc()).all()


@router.post("/", response_model=RequestOut)
def create_request(
    data: RequestCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    eq = db.query(ClientEquipment).filter(ClientEquipment.id == data.equipment_id).first()
    if not eq:
        raise HTTPException(404, "Оборудование не найдено")
    obj = ServiceRequest(
        **data.model_dump(),
        number=_next_number(db),
        created_by=current_user.id,
    )
    eq.status = "in_repair"
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{request_id}", response_model=RequestOut)
def get_request(
    request_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
    if not obj:
        raise HTTPException(404, "Заявка не найдена")
    return obj


@router.put("/{request_id}", response_model=RequestOut)
def update_request(
    request_id: int,
    data: RequestUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
    if not obj:
        raise HTTPException(404, "Заявка не найдена")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{request_id}/status", response_model=RequestOut)
def update_status(
    request_id: int,
    data: StatusUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
    if not obj:
        raise HTTPException(404, "Заявка не найдена")
    allowed = VALID_TRANSITIONS.get(obj.status, [])
    if data.status not in allowed:
        raise HTTPException(
            400, f"Переход из статуса '{obj.status}' в '{data.status}' недопустим"
        )

    now = datetime.utcnow()
    obj.status = data.status
    if data.status == "assigned":
        obj.assigned_at = now
    elif data.status == "in_progress":
        obj.started_at = now
    elif data.status in ("done", "closed", "cancelled"):
        obj.closed_at = now

    if data.resolution:
        obj.resolution = data.resolution

    # Restore equipment status once work is finished
    if data.status in ("done", "closed", "cancelled"):
        eq = db.query(ClientEquipment).filter(
            ClientEquipment.id == obj.equipment_id
        ).first()
        if eq:
            eq.status = "active"

    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{request_id}/assign", response_model=RequestOut)
def assign_engineer(
    request_id: int,
    data: AssignRequest,
    db: Session = Depends(get_db),
    _=Depends(require_manager),
):
    obj = db.query(ServiceRequest).filter(ServiceRequest.id == request_id).first()
    if not obj:
        raise HTTPException(404, "Заявка не найдена")
    obj.engineer_id = data.engineer_id
    if obj.status == "new":
        obj.status = "assigned"
        obj.assigned_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/{request_id}/parts")
def get_request_parts(
    request_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    from app.models import PartsUsage
    usages = db.query(PartsUsage).filter(PartsUsage.request_id == request_id).all()
    return [
        {
            "id": u.id,
            "part_id": u.part_id,
            "part_name": u.part.name if u.part else None,
            "quantity": u.quantity,
            "unit_price": float(u.unit_price),
            "total": float(u.quantity * u.unit_price),
            "used_by": u.used_by,
            "used_at": u.used_at,
            "notes": u.notes,
        }
        for u in usages
    ]
