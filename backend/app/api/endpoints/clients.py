from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from app.core.database import get_db
from app.models.client import Client
from app.models.interaction import Interaction
from app.api.deps import get_current_user

router = APIRouter()

class ClientCreate(BaseModel):
    company_name: str
    inn: Optional[str] = None
    kpp: Optional[str] = None
    legal_address: Optional[str] = None
    actual_address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    manager_id: Optional[int] = None
    notes: Optional[str] = None

class ClientOut(BaseModel):
    id: int; company_name: str; inn: Optional[str]; contact_name: Optional[str]
    contact_phone: Optional[str]; contact_email: Optional[str]; is_active: bool
    class Config: from_attributes = True

class InteractionCreate(BaseModel):
    type: str
    date: datetime
    subject: str
    description: Optional[str] = None

class InteractionOut(BaseModel):
    id: int; type: str; date: datetime; subject: str; description: Optional[str]
    class Config: from_attributes = True

@router.get("/", response_model=List[ClientOut])
def list_clients(search: Optional[str] = Query(None), db: Session = Depends(get_db), _=Depends(get_current_user)):
    q = db.query(Client).filter(Client.is_active == True)
    if search:
        q = q.filter(Client.company_name.ilike(f"%{search}%"))
    return q.order_by(Client.company_name).all()

@router.post("/", response_model=ClientOut)
def create_client(data: ClientCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    client = Client(**data.model_dump())
    db.add(client); db.commit(); db.refresh(client)
    return client

@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = db.query(Client).filter(Client.id == client_id).first()
    if not c: raise HTTPException(404, "Клиент не найден")
    return c

@router.put("/{client_id}", response_model=ClientOut)
def update_client(client_id: int, data: ClientCreate, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = db.query(Client).filter(Client.id == client_id).first()
    if not c: raise HTTPException(404, "Клиент не найден")
    for k, v in data.model_dump().items(): setattr(c, k, v)
    db.commit(); db.refresh(c)
    return c

@router.delete("/{client_id}")
def delete_client(client_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    c = db.query(Client).filter(Client.id == client_id).first()
    if not c: raise HTTPException(404, "Клиент не найден")
    c.is_active = False; db.commit()
    return {"ok": True}

@router.get("/{client_id}/interactions", response_model=List[InteractionOut])
def get_interactions(client_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(Interaction).filter(Interaction.client_id == client_id).order_by(Interaction.date.desc()).all()

@router.post("/{client_id}/interactions", response_model=InteractionOut)
def add_interaction(client_id: int, data: InteractionCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    obj = Interaction(client_id=client_id, user_id=current_user.id, **data.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj
