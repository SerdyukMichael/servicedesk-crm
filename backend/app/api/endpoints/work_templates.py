from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import WorkTemplate, WorkTemplateStep, User
from app.api.deps import get_current_user, require_roles
from app.schemas import (
    WorkTemplateCreate, WorkTemplateUpdate, WorkTemplateResponse, PaginatedResponse,
)

router = APIRouter()

_MANAGE_ROLES = ("admin", "svc_mgr")
_ADMIN = ("admin",)


@router.get("", response_model=PaginatedResponse[WorkTemplateResponse])
def list_work_templates(
    equipment_model_id: Optional[int] = Query(None),
    equipment_model: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(WorkTemplate).filter(WorkTemplate.is_active.is_(True))
    if equipment_model_id is not None:
        q = q.filter(WorkTemplate.equipment_model_id == equipment_model_id)
    if equipment_model:
        from app.models import EquipmentModel
        q = q.join(EquipmentModel, WorkTemplate.equipment_model_id == EquipmentModel.id)
        q = q.filter(EquipmentModel.name.ilike(f"%{equipment_model}%"))
    total = q.count()
    skip = (page - 1) * size
    items = q.order_by(WorkTemplate.name).offset(skip).limit(size).all()
    pages = max(1, (total + size - 1) // size)
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.post("", response_model=WorkTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_work_template(
    data: WorkTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    if not data.steps:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "VALIDATION_ERROR", "message": "Шаблон должен содержать хотя бы один шаг"},
        )
    template = WorkTemplate(
        name=data.name,
        equipment_model_id=data.equipment_model_id,
        description=data.description,
        is_active=data.is_active,
        created_by=current_user.id,
    )
    db.add(template)
    db.flush()
    for step_data in data.steps:
        step = WorkTemplateStep(template_id=template.id, **step_data.model_dump())
        db.add(step)
    db.commit()
    db.refresh(template)
    return template


@router.get("/{template_id}", response_model=WorkTemplateResponse)
def get_work_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    template = db.query(WorkTemplate).filter(
        WorkTemplate.id == template_id,
        WorkTemplate.is_active.is_(True),
    ).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Шаблон работ не найден"},
        )
    return template


@router.put("/{template_id}", response_model=WorkTemplateResponse)
def update_work_template(
    template_id: int,
    data: WorkTemplateUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_MANAGE_ROLES)),
):
    template = db.query(WorkTemplate).filter(WorkTemplate.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Шаблон работ не найден"},
        )
    update_data = data.model_dump(exclude_none=True)
    steps_data = update_data.pop("steps", None)
    for k, v in update_data.items():
        setattr(template, k, v)

    if steps_data is not None:
        if not steps_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": "VALIDATION_ERROR", "message": "Шаблон должен содержать хотя бы один шаг"},
            )
        # Replace all steps
        for old_step in template.steps:
            db.delete(old_step)
        db.flush()
        for step_data in steps_data:
            step = WorkTemplateStep(template_id=template.id, **step_data)
            db.add(step)

    db.commit()
    db.refresh(template)
    return template


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_work_template(
    template_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_ADMIN)),
):
    template = db.query(WorkTemplate).filter(WorkTemplate.id == template_id).first()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Шаблон работ не найден"},
        )
    template.is_active = False
    db.commit()
