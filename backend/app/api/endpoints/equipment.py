from typing import List, Optional
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.core.database import get_db
from app.models import EquipmentCatalog, ClientEquipment
from app.api.deps import get_current_user, require_admin

router = APIRouter()


# ─── Schemas ────────────────────────────────────────────────────────────────

class CatalogCreate(BaseModel):
    name: str
    model: Optional[str] = None
    category: str = "other"
    vendor_id: Optional[int] = None
    purchase_price: Optional[float] = None
    sale_price: Optional[float] = None
    description: Optional[str] = None


class CatalogOut(BaseModel):
    id: int
    name: str
    model: Optional[str]
    category: str
    vendor_id: Optional[int]
    purchase_price: Optional[float]
    sale_price: Optional[float]
    description: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class UnitCreate(BaseModel):
    client_id: int
    catalog_id: int
    serial_number: str
    install_date: Optional[date] = None
    address: Optional[str] = None
    status: str = "active"
    warranty_until: Optional[date] = None
    notes: Optional[str] = None


class UnitUpdate(BaseModel):
    install_date: Optional[date] = None
    address: Optional[str] = None
    status: Optional[str] = None
    warranty_until: Optional[date] = None
    notes: Optional[str] = None


class UnitOut(BaseModel):
    id: int
    client_id: int
    catalog_id: int
    serial_number: str
    install_date: Optional[date]
    address: Optional[str]
    status: str
    warranty_until: Optional[date]
    notes: Optional[str]

    class Config:
        from_attributes = True


# ─── Catalog Endpoints ──────────────────────────────────────────────────────

@router.get("/catalog", response_model=List[CatalogOut])
def list_catalog(
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(EquipmentCatalog).filter(EquipmentCatalog.is_active == True)
    if category:
        q = q.filter(EquipmentCatalog.category == category)
    if search:
        q = q.filter(EquipmentCatalog.name.ilike(f"%{search}%"))
    return q.order_by(EquipmentCatalog.name).all()


@router.post("/catalog", response_model=CatalogOut)
def create_catalog_item(
    data: CatalogCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    obj = EquipmentCatalog(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/catalog/{catalog_id}", response_model=CatalogOut)
def get_catalog_item(
    catalog_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = db.query(EquipmentCatalog).filter(EquipmentCatalog.id == catalog_id).first()
    if not obj:
        raise HTTPException(404, "Позиция каталога не найдена")
    return obj


@router.put("/catalog/{catalog_id}", response_model=CatalogOut)
def update_catalog_item(
    catalog_id: int,
    data: CatalogCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    obj = db.query(EquipmentCatalog).filter(EquipmentCatalog.id == catalog_id).first()
    if not obj:
        raise HTTPException(404, "Позиция каталога не найдена")
    for k, v in data.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/catalog/{catalog_id}")
def delete_catalog_item(
    catalog_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    obj = db.query(EquipmentCatalog).filter(EquipmentCatalog.id == catalog_id).first()
    if not obj:
        raise HTTPException(404, "Позиция каталога не найдена")
    obj.is_active = False
    db.commit()
    return {"ok": True}


# ─── Client Equipment Units ─────────────────────────────────────────────────

@router.get("/units", response_model=List[UnitOut])
def list_units(
    client_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    q = db.query(ClientEquipment)
    if client_id:
        q = q.filter(ClientEquipment.client_id == client_id)
    if status:
        q = q.filter(ClientEquipment.status == status)
    return q.order_by(ClientEquipment.id.desc()).all()


@router.post("/units", response_model=UnitOut)
def create_unit(
    data: UnitCreate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    existing = db.query(ClientEquipment).filter(
        ClientEquipment.serial_number == data.serial_number
    ).first()
    if existing:
        raise HTTPException(400, "Оборудование с таким серийным номером уже существует")
    obj = ClientEquipment(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/units/{unit_id}", response_model=UnitOut)
def get_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = db.query(ClientEquipment).filter(ClientEquipment.id == unit_id).first()
    if not obj:
        raise HTTPException(404, "Оборудование не найдено")
    return obj


@router.put("/units/{unit_id}", response_model=UnitOut)
def update_unit(
    unit_id: int,
    data: UnitUpdate,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = db.query(ClientEquipment).filter(ClientEquipment.id == unit_id).first()
    if not obj:
        raise HTTPException(404, "Оборудование не найдено")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/units/{unit_id}/requests")
def get_unit_requests(
    unit_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    obj = db.query(ClientEquipment).filter(ClientEquipment.id == unit_id).first()
    if not obj:
        raise HTTPException(404, "Оборудование не найдено")
    return [
        {
            "id": r.id,
            "number": r.number,
            "type": r.type,
            "priority": r.priority,
            "status": r.status,
            "description": r.description,
            "created_at": r.created_at,
            "closed_at": r.closed_at,
        }
        for r in obj.requests
    ]
