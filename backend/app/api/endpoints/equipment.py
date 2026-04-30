from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import Equipment, EquipmentModel, MaintenanceSchedule, User, Ticket
from app.api.deps import get_current_user, require_roles, get_client_scope
from app.services.audit import log_action
from app.schemas import (
    EquipmentCreate, EquipmentUpdate, EquipmentResponse,
    EquipmentModelCreate, EquipmentModelUpdate, EquipmentModelResponse,
    MaintenanceScheduleCreate, MaintenanceScheduleUpdate, MaintenanceScheduleResponse,
    PaginatedResponse, EquipmentLookupResponse,
)

router = APIRouter()

_WRITE_ROLES = ("admin", "svc_mgr")
_ADMIN = ("admin",)


@router.get("/models", response_model=list[EquipmentModelResponse])
def list_equipment_models(
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(EquipmentModel)
    if not include_inactive:
        q = q.filter(EquipmentModel.is_active.is_(True))
    return q.order_by(EquipmentModel.name).all()


@router.post("/models", response_model=EquipmentModelResponse, status_code=status.HTTP_201_CREATED)
def create_equipment_model(
    data: EquipmentModelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_WRITE_ROLES)),
):
    existing = db.query(EquipmentModel).filter(EquipmentModel.name == data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "DUPLICATE_NAME", "message": f"Модель «{data.name}» уже существует"},
        )
    m = EquipmentModel(**data.model_dump())
    db.add(m)
    db.flush()
    log_action(db, user_id=current_user.id, action="CREATE", entity_type="equipment_model", entity_id=m.id,
               new={"name": m.name, "manufacturer": m.manufacturer})
    db.commit()
    db.refresh(m)
    return m


@router.put("/models/{model_id}", response_model=EquipmentModelResponse)
def update_equipment_model(
    model_id: int,
    data: EquipmentModelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_WRITE_ROLES)),
):
    m = db.query(EquipmentModel).filter(EquipmentModel.id == model_id).first()
    if not m:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Модель оборудования не найдена"},
        )
    update_data = data.model_dump(exclude_none=True)
    if "name" in update_data:
        conflict = db.query(EquipmentModel).filter(
            EquipmentModel.name == update_data["name"],
            EquipmentModel.id != model_id,
        ).first()
        if conflict:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": "DUPLICATE_NAME", "message": f"Модель «{update_data['name']}» уже существует"},
            )
    old_vals = {k: getattr(m, k) for k in update_data}
    for k, v in update_data.items():
        setattr(m, k, v)
    log_action(db, user_id=current_user.id, action="UPDATE", entity_type="equipment_model", entity_id=m.id,
               old=old_vals, new=update_data)
    db.commit()
    db.refresh(m)
    return m


@router.patch("/models/{model_id}/deactivate", response_model=EquipmentModelResponse)
def deactivate_equipment_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_WRITE_ROLES)),
):
    m = db.query(EquipmentModel).filter(EquipmentModel.id == model_id).first()
    if not m:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Модель оборудования не найдена"},
        )
    m.is_active = False
    log_action(db, user_id=current_user.id, action="UPDATE", entity_type="equipment_model", entity_id=m.id,
               old={"is_active": True}, new={"is_active": False})
    db.commit()
    db.refresh(m)
    return m


@router.patch("/models/{model_id}/activate", response_model=EquipmentModelResponse)
def activate_equipment_model(
    model_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_WRITE_ROLES)),
):
    m = db.query(EquipmentModel).filter(EquipmentModel.id == model_id).first()
    if not m:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Модель оборудования не найдена"},
        )
    m.is_active = True
    log_action(db, user_id=current_user.id, action="UPDATE", entity_type="equipment_model", entity_id=m.id,
               old={"is_active": False}, new={"is_active": True})
    db.commit()
    db.refresh(m)
    return m


@router.get("", response_model=PaginatedResponse[EquipmentResponse])
def list_equipment(
    client_id: Optional[int] = Query(None),
    eq_status: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    q = db.query(Equipment).options(joinedload(Equipment.client), joinedload(Equipment.model)).filter(Equipment.is_deleted.is_(False))
    # client_user sees only their organisation's equipment
    effective_client_id = client_scope if client_scope is not None else client_id
    if effective_client_id is not None:
        q = q.filter(Equipment.client_id == effective_client_id)
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
    current_user: User = Depends(require_roles(*_WRITE_ROLES)),
):
    existing = (
        db.query(Equipment)
        .options(joinedload(Equipment.client), joinedload(Equipment.model))
        .filter(Equipment.serial_number == data.serial_number)
        .first()
    )
    if existing:
        client_name = existing.client.name if existing.client else f"id={existing.client_id}"
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "DUPLICATE_SERIAL",
                "message": (
                    f"Серийный номер {data.serial_number} уже существует: "
                    f"клиент {client_name}"
                ),
            },
        )
    eq = Equipment(**data.model_dump())
    db.add(eq)
    db.flush()
    log_action(db, user_id=current_user.id, action="CREATE", entity_type="equipment", entity_id=eq.id,
               new={"serial_number": eq.serial_number, "client_id": eq.client_id, "model_id": eq.model_id})
    db.commit()
    db.refresh(eq)
    db.refresh(eq, ["client", "model"])
    return eq


@router.get("/lookup", response_model=EquipmentLookupResponse)
def lookup_equipment_by_serial(
    serial: str = Query(..., min_length=3, description="Серийный номер оборудования (минимум 3 символа)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    eq = (
        db.query(Equipment)
        .options(joinedload(Equipment.client), joinedload(Equipment.model))
        .filter(Equipment.serial_number == serial, Equipment.is_deleted.is_(False))
        .first()
    )
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": f"Equipment with serial number '{serial}' not found"},
        )
    if client_scope is not None and eq.client_id != client_scope:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": "FORBIDDEN", "message": "Equipment does not belong to your organization"},
        )
    today = date.today()
    is_warranty = eq.warranty_until is not None and eq.warranty_until >= today
    return EquipmentLookupResponse(
        equipment_id=eq.id,
        serial_number=eq.serial_number,
        model_name=eq.model.name,
        client_id=eq.client_id,
        client_name=eq.client.name,
        is_under_warranty=is_warranty,
        warranty_until=eq.warranty_until,
    )


@router.get("/{equipment_id}", response_model=EquipmentResponse)
def get_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    q = (
        db.query(Equipment)
        .options(joinedload(Equipment.client), joinedload(Equipment.model))
        .filter(Equipment.id == equipment_id, Equipment.is_deleted.is_(False))
    )
    if client_scope is not None:
        q = q.filter(Equipment.client_id == client_scope)
    eq = q.first()
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
    current_user: User = Depends(require_roles(*_WRITE_ROLES)),
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
    old_vals = {k: str(getattr(eq, k, None)) for k in update_data}
    for k, v in update_data.items():
        setattr(eq, k, v)
    log_action(db, user_id=current_user.id, action="UPDATE", entity_type="equipment", entity_id=eq.id,
               old=old_vals, new={k: str(v) for k, v in update_data.items()})
    db.commit()
    db.refresh(eq)
    db.refresh(eq, ["client", "model"])
    return eq


@router.delete("/{equipment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ADMIN)),
):
    eq = db.query(Equipment).filter(Equipment.id == equipment_id, Equipment.is_deleted.is_(False)).first()
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Оборудование не найдено"},
        )
    eq.is_deleted = True
    log_action(db, user_id=current_user.id, action="DELETE", entity_type="equipment", entity_id=eq.id,
               old={"serial_number": eq.serial_number, "client_id": eq.client_id})
    db.commit()




# ── Maintenance Schedule ───────────────────────────────────────────────────────

def _get_equipment_or_404(db: Session, equipment_id: int) -> Equipment:
    eq = db.query(Equipment).filter(
        Equipment.id == equipment_id, Equipment.is_deleted.is_(False)
    ).first()
    if not eq:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Оборудование не найдено"},
        )
    return eq


@router.get("/{equipment_id}/maintenance-schedule", response_model=Optional[MaintenanceScheduleResponse])
def get_maintenance_schedule(
    equipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    _get_equipment_or_404(db, equipment_id)
    schedule = db.query(MaintenanceSchedule).filter(
        MaintenanceSchedule.equipment_id == equipment_id,
        MaintenanceSchedule.is_active.is_(True),
    ).first()
    return schedule


@router.post("/{equipment_id}/maintenance-schedule", response_model=MaintenanceScheduleResponse, status_code=status.HTTP_201_CREATED)
def create_maintenance_schedule(
    equipment_id: int,
    data: MaintenanceScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_WRITE_ROLES)),
):
    _get_equipment_or_404(db, equipment_id)
    existing = db.query(MaintenanceSchedule).filter(
        MaintenanceSchedule.equipment_id == equipment_id,
        MaintenanceSchedule.is_active.is_(True),
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "CONFLICT", "message": "Активный график ТО уже существует"},
        )
    schedule = MaintenanceSchedule(
        equipment_id=equipment_id,
        frequency=data.frequency,
        first_date=data.first_date,
        next_date=data.first_date,
        created_by=current_user.id,
    )
    db.add(schedule)
    db.flush()
    log_action(db, user_id=current_user.id, action="CREATE", entity_type="maintenance_schedule",
               entity_id=schedule.id,
               new={"equipment_id": equipment_id, "frequency": data.frequency, "first_date": str(data.first_date)})
    db.commit()
    db.refresh(schedule)
    return schedule


@router.put("/{equipment_id}/maintenance-schedule", response_model=MaintenanceScheduleResponse)
def update_maintenance_schedule(
    equipment_id: int,
    data: MaintenanceScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_WRITE_ROLES)),
):
    _get_equipment_or_404(db, equipment_id)
    schedule = db.query(MaintenanceSchedule).filter(
        MaintenanceSchedule.equipment_id == equipment_id,
        MaintenanceSchedule.is_active.is_(True),
    ).first()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "График ТО не найден"},
        )
    upd = data.model_dump(exclude_none=True)
    old_vals = {k: str(getattr(schedule, k, None)) for k in upd}
    if data.frequency is not None:
        schedule.frequency = data.frequency
    if data.first_date is not None:
        schedule.first_date = data.first_date
    if data.next_date is not None:
        schedule.next_date = data.next_date
    if data.is_active is not None:
        schedule.is_active = data.is_active
    log_action(db, user_id=current_user.id, action="UPDATE", entity_type="maintenance_schedule",
               entity_id=schedule.id, old=old_vals, new={k: str(v) for k, v in upd.items()})
    db.commit()
    db.refresh(schedule)
    return schedule
