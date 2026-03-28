from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Equipment, EquipmentModel, RepairHistory, User
from app.api.deps import get_current_user, require_roles
from app.schemas import (
    EquipmentCreate, EquipmentUpdate, EquipmentResponse,
    EquipmentModelResponse, RepairHistoryResponse, PaginatedResponse,
)

router = APIRouter()

_WRITE_ROLES = ("admin", "svc_mgr")
_ADMIN = ("admin",)


@router.get("/models", response_model=list[EquipmentModelResponse])
def list_equipment_models(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    return (
        db.query(EquipmentModel)
        .filter(EquipmentModel.is_active.is_(True))
        .order_by(EquipmentModel.name)
        .all()
    )


@router.get("", response_model=PaginatedResponse[EquipmentResponse])
def list_equipment(
    client_id: Optional[int] = Query(None),
    eq_status: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Equipment).filter(Equipment.is_deleted.is_(False))
    if client_id is not None:
        q = q.filter(Equipment.client_id == client_id)
    if eq_status:
        q = q.filter(Equipment.status == eq_status)
    total = q.count()
    skip = (page - 1) * size
    items = q.order_by(Equipment.id).offset(skip).limit(size).all()
    pages = max(1, (total + size - 1) // size)
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.post("", response_model=EquipmentResponse, status_code=status.HTTP_201_CREATED)
def create_equipment(
    data: EquipmentCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE_ROLES)),
):
    if db.query(Equipment).filter(Equipment.serial_number == data.serial_number).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "CONFLICT", "message": "Серийный номер уже существует"},
        )
    eq = Equipment(**data.model_dump())
    db.add(eq)
    db.commit()
    db.refresh(eq)
    return eq


@router.get("/{equipment_id}", response_model=EquipmentResponse)
def get_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    eq = db.query(Equipment).filter(Equipment.id == equipment_id, Equipment.is_deleted.is_(False)).first()
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Оборудование не найдено"},
        )
    return eq


@router.put("/{equipment_id}", response_model=EquipmentResponse)
def update_equipment(
    equipment_id: int,
    data: EquipmentUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE_ROLES)),
):
    eq = db.query(Equipment).filter(Equipment.id == equipment_id, Equipment.is_deleted.is_(False)).first()
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Оборудование не найдено"},
        )
    update_data = data.model_dump(exclude_none=True)
    if "serial_number" in update_data:
        conflict = (
            db.query(Equipment)
            .filter(
                Equipment.serial_number == update_data["serial_number"],
                Equipment.id != equipment_id,
            )
            .first()
        )
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "CONFLICT", "message": "Серийный номер уже существует"},
            )
    for k, v in update_data.items():
        setattr(eq, k, v)
    db.commit()
    db.refresh(eq)
    return eq


@router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_ADMIN)),
):
    eq = db.query(Equipment).filter(Equipment.id == equipment_id, Equipment.is_deleted.is_(False)).first()
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Оборудование не найдено"},
        )
    eq.is_deleted = True
    db.commit()


@router.get("/{equipment_id}/history", response_model=list[RepairHistoryResponse])
def get_equipment_history(
    equipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    eq = db.query(Equipment).filter(Equipment.id == equipment_id, Equipment.is_deleted.is_(False)).first()
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Оборудование не найдено"},
        )
    return (
        db.query(RepairHistory)
        .filter(RepairHistory.equipment_id == equipment_id)
        .order_by(RepairHistory.performed_at.desc())
        .all()
    )
