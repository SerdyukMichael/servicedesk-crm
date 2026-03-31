from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload, contains_eager

from app.core.database import get_db
from app.models import Client, User
from app.api.deps import get_current_user, require_roles
from app.schemas import ClientCreate, ClientUpdate, ClientResponse, PaginatedResponse, ClientContactCreate, ClientContactResponse, EquipmentResponse, TicketResponse
from app.models import ClientContact, Equipment, Ticket

router = APIRouter()

_WRITE_ROLES = ("admin", "sales_mgr", "svc_mgr")
_ADMIN = ("admin",)


@router.get("", response_model=PaginatedResponse[ClientResponse])
def list_clients(
    search: Optional[str] = Query(None),
    contract_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Client).options(joinedload(Client.manager)).filter(Client.is_deleted.is_(False))
    if search:
        q = q.filter(Client.name.ilike(f"%{search}%"))
    if contract_type:
        q = q.filter(Client.contract_type == contract_type)
    total = q.count()
    skip = (page - 1) * size
    items = q.order_by(Client.name).offset(skip).limit(size).all()
    pages = max(1, (total + size - 1) // size)
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.post("", response_model=ClientResponse, status_code=status.HTTP_201_CREATED)
def create_client(
    data: ClientCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE_ROLES)),
):
    d = data.model_dump()
    if d.get("contract_end") is not None:
        d["contract_valid_until"] = d.pop("contract_end")
    else:
        d.pop("contract_end", None)
    client = Client(**d)
    db.add(client)
    db.commit()
    db.refresh(client)
    db.refresh(client, ["manager"])
    return client


@router.get("/{client_id}", response_model=ClientResponse)
def get_client(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    client = (
        db.query(Client)
        .options(joinedload(Client.manager))
        .filter(Client.id == client_id, Client.is_deleted.is_(False))
        .first()
    )
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Клиент не найден"},
        )
    return client


@router.put("/{client_id}", response_model=ClientResponse)
def update_client(
    client_id: int,
    data: ClientUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE_ROLES)),
):
    client = (
        db.query(Client)
        .options(joinedload(Client.manager))
        .filter(Client.id == client_id, Client.is_deleted.is_(False))
        .first()
    )
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Клиент не найден"},
        )
    d = data.model_dump(exclude_none=True)
    if "contract_end" in d:
        d["contract_valid_until"] = d.pop("contract_end")
    for k, v in d.items():
        setattr(client, k, v)
    db.commit()
    db.refresh(client)
    db.refresh(client, ["manager"])
    return client


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_ADMIN)),
):
    client = db.query(Client).filter(Client.id == client_id, Client.is_deleted.is_(False)).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Клиент не найден"},
        )
    client.is_deleted = True
    db.commit()


@router.get("/{client_id}/contacts", response_model=list[ClientContactResponse])
def list_contacts(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id, Client.is_deleted.is_(False)).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "NOT_FOUND", "message": "Клиент не найден"})
    return db.query(ClientContact).filter(ClientContact.client_id == client_id, ClientContact.is_active.is_(True)).all()


@router.post("/{client_id}/contacts", response_model=ClientContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(
    client_id: int,
    data: ClientContactCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE_ROLES)),
):
    client = db.query(Client).filter(Client.id == client_id, Client.is_deleted.is_(False)).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "NOT_FOUND", "message": "Клиент не найден"})
    contact = ClientContact(client_id=client_id, **data.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@router.delete("/{client_id}/contacts/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contact(
    client_id: int,
    contact_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_WRITE_ROLES)),
):
    contact = db.query(ClientContact).filter(ClientContact.id == contact_id, ClientContact.client_id == client_id).first()
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "NOT_FOUND", "message": "Контакт не найден"})
    contact.is_active = False
    db.commit()


@router.get("/{client_id}/equipment", response_model=list[EquipmentResponse])
def list_client_equipment(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id, Client.is_deleted.is_(False)).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "NOT_FOUND", "message": "Клиент не найден"})
    return (
        db.query(Equipment)
        .options(joinedload(Equipment.model))
        .filter(Equipment.client_id == client_id, Equipment.is_deleted.is_(False))
        .all()
    )


@router.get("/{client_id}/tickets", response_model=list[TicketResponse])
def list_client_tickets(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    client = db.query(Client).filter(Client.id == client_id, Client.is_deleted.is_(False)).first()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail={"error": "NOT_FOUND", "message": "Клиент не найден"})
    return (
        db.query(Ticket)
        .options(joinedload(Ticket.client))
        .filter(Ticket.client_id == client_id, Ticket.is_deleted.is_(False))
        .order_by(Ticket.created_at.desc())
        .all()
    )
