import secrets
import string
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.core.security import hash_password
from app.models import AuditLog, Client, ClientContact, Equipment, Ticket, User
from app.api.deps import get_current_user, require_roles, get_client_scope
from app.schemas import (
    ClientContactCreate,
    ClientContactPortalAccess,
    ClientContactPortalGrantResponse,
    ClientContactResponse,
    ClientContactUpdate,
    ClientCreate,
    ClientResponse,
    ClientUpdate,
    EquipmentResponse,
    PaginatedResponse,
    TicketResponse,
)

router = APIRouter()

_WRITE_ROLES = ("admin", "sales_mgr", "svc_mgr")
_CONTACT_WRITE_ROLES = ("admin", "sales_mgr", "svc_mgr")
_DEACTIVATE_ROLES = ("admin", "sales_mgr")
_PORTAL_ROLES = ("admin", "sales_mgr")
_ADMIN = ("admin",)


# ── helpers ───────────────────────────────────────────────────────────────────

def _write_audit(
    db: Session,
    user: User,
    entity_type: str,
    entity_id: int,
    action: str,
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
) -> None:
    db.add(
        AuditLog(
            user_id=user.id,
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_values=old_values,
            new_values=new_values,
        )
    )


def _get_active_client(db: Session, client_id: int) -> Client:
    client = (
        db.query(Client)
        .filter(Client.id == client_id, Client.is_deleted.is_(False))
        .first()
    )
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Клиент не найден"},
        )
    return client


def _get_contact(db: Session, client_id: int, contact_id: int) -> ClientContact:
    contact = (
        db.query(ClientContact)
        .filter(
            ClientContact.id == contact_id,
            ClientContact.client_id == client_id,
        )
        .first()
    )
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Контакт не найден"},
        )
    return contact


def _check_email_unique(
    db: Session,
    client_id: int,
    email: Optional[str],
    exclude_id: Optional[int] = None,
) -> None:
    """Raise 409 if email already used by another active contact of this client."""
    if not email:
        return
    q = db.query(ClientContact).filter(
        ClientContact.client_id == client_id,
        ClientContact.email == email,
        ClientContact.is_active.is_(True),
    )
    if exclude_id is not None:
        q = q.filter(ClientContact.id != exclude_id)
    existing = q.first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error": "EMAIL_DUPLICATE",
                "message": f"Email {email} уже назначен контакту {existing.name} этой организации",
            },
        )


def _clear_primary(db: Session, client_id: int, exclude_id: Optional[int] = None) -> None:
    """Set is_primary=False for all contacts of this client except exclude_id."""
    q = db.query(ClientContact).filter(
        ClientContact.client_id == client_id,
        ClientContact.is_primary.is_(True),
    )
    if exclude_id is not None:
        q = q.filter(ClientContact.id != exclude_id)
    q.update({"is_primary": False}, synchronize_session=False)


# ── Clients CRUD ──────────────────────────────────────────────────────────────

@router.get("", response_model=PaginatedResponse[ClientResponse])
def list_clients(
    search: Optional[str] = Query(None),
    contract_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    q = db.query(Client).options(joinedload(Client.manager)).filter(Client.is_deleted.is_(False))
    # client_user sees only their own organisation
    if client_scope is not None:
        q = q.filter(Client.id == client_scope)
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
    client_scope: Optional[int] = Depends(get_client_scope),
):
    if client_scope is not None and client_id != client_scope:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Клиент не найден"},
        )
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


# ── Contacts ──────────────────────────────────────────────────────────────────

@router.get("/{client_id}/contacts", response_model=list[ClientContactResponse])
def list_contacts(
    client_id: int,
    include_inactive: bool = Query(False),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    if client_scope is not None and client_id != client_scope:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Клиент не найден"},
        )
    _get_active_client(db, client_id)
    q = db.query(ClientContact).filter(ClientContact.client_id == client_id)
    if not include_inactive:
        q = q.filter(ClientContact.is_active.is_(True))
    return q.order_by(ClientContact.is_primary.desc(), ClientContact.name).all()


@router.post(
    "/{client_id}/contacts",
    response_model=ClientContactResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_contact(
    client_id: int,
    data: ClientContactCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_CONTACT_WRITE_ROLES)),
):
    _get_active_client(db, client_id)
    _check_email_unique(db, client_id, data.email)

    if data.is_primary:
        _clear_primary(db, client_id)

    contact = ClientContact(
        client_id=client_id,
        created_by=current_user.id,
        **data.model_dump(),
    )
    db.add(contact)
    db.flush()

    _write_audit(
        db, current_user,
        entity_type="client_contact",
        entity_id=contact.id,
        action="create",
        new_values=data.model_dump(),
    )
    db.commit()
    db.refresh(contact)
    return contact


@router.put("/{client_id}/contacts/{contact_id}", response_model=ClientContactResponse)
def update_contact(
    client_id: int,
    contact_id: int,
    data: ClientContactUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_CONTACT_WRITE_ROLES)),
):
    _get_active_client(db, client_id)
    contact = _get_contact(db, client_id, contact_id)

    d = data.model_dump(exclude_none=True)
    if "email" in d:
        _check_email_unique(db, client_id, d["email"], exclude_id=contact_id)

    old_values = {
        "name": contact.name,
        "position": contact.position,
        "phone": contact.phone,
        "email": contact.email,
        "is_primary": contact.is_primary,
        "is_active": contact.is_active,
    }

    # Если устанавливаем этот контакт основным — снимаем флаг у остальных
    if d.get("is_primary") is True:
        _clear_primary(db, client_id, exclude_id=contact_id)

    for k, v in d.items():
        setattr(contact, k, v)

    _write_audit(
        db, current_user,
        entity_type="client_contact",
        entity_id=contact_id,
        action="update",
        old_values=old_values,
        new_values=d,
    )
    db.commit()
    db.refresh(contact)
    return contact


@router.delete(
    "/{client_id}/contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def deactivate_contact(
    client_id: int,
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_DEACTIVATE_ROLES)),
):
    _get_active_client(db, client_id)
    contact = _get_contact(db, client_id, contact_id)

    old_values = {"is_active": contact.is_active, "portal_access": contact.portal_access}
    contact.is_active = False
    contact.portal_access = False  # ИП-3: деактивация блокирует доступ к порталу

    _write_audit(
        db, current_user,
        entity_type="client_contact",
        entity_id=contact_id,
        action="deactivate",
        old_values=old_values,
        new_values={"is_active": False, "portal_access": False},
    )
    db.commit()


def _gen_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$"
    return "".join(secrets.choice(alphabet) for _ in range(length))


@router.post(
    "/{client_id}/contacts/{contact_id}/portal-access",
    response_model=ClientContactPortalGrantResponse,
)
def grant_portal_access(
    client_id: int,
    contact_id: int,
    data: ClientContactPortalAccess,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_PORTAL_ROLES)),
):
    _get_active_client(db, client_id)
    contact = _get_contact(db, client_id, contact_id)

    # ИП-3: нельзя выдать доступ деактивированному
    if not contact.is_active:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "CONTACT_INACTIVE",
                "message": "Нельзя выдать доступ — контакт деактивирован. Сначала активируйте его",
            },
        )

    # ИП-4: email обязателен
    effective_email = data.email or contact.email
    if not effective_email:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "EMAIL_REQUIRED",
                "message": "Для выдачи доступа к порталу укажите email контакта",
            },
        )

    if data.email and data.email != contact.email:
        contact.email = data.email

    # Создать или активировать учётную запись в users
    temp_password: Optional[str] = None
    portal_user = db.query(User).filter(User.email == effective_email).first()

    if portal_user is None:
        # Создаём новую учётную запись
        temp_password = _gen_temp_password()
        portal_user = User(
            email=effective_email,
            full_name=contact.name,
            password_hash=hash_password(temp_password),
            roles=["client_user"],
            client_id=client_id,
            is_active=True,
            is_deleted=False,
        )
        db.add(portal_user)
        db.flush()
    else:
        # Активируем / обновляем существующую
        portal_user.is_active = True
        portal_user.is_deleted = False
        portal_user.client_id = client_id
        existing_roles = portal_user.roles if isinstance(portal_user.roles, list) else ["client_user"]
        if "client_user" not in existing_roles:
            existing_roles = ["client_user"] + existing_roles
        portal_user.roles = existing_roles

    contact.portal_access = True
    contact.portal_role = data.portal_role
    contact.portal_user_id = portal_user.id

    _write_audit(
        db, current_user,
        entity_type="client_contact",
        entity_id=contact_id,
        action="portal_access_grant",
        new_values={
            "portal_access": True,
            "portal_role": data.portal_role,
            "email": effective_email,
            "portal_user_id": portal_user.id,
        },
    )
    db.commit()
    db.refresh(contact)

    result = ClientContactPortalGrantResponse.model_validate(contact)
    result.temporary_password = temp_password
    return result


@router.delete(
    "/{client_id}/contacts/{contact_id}/portal-access",
    response_model=ClientContactResponse,
)
def revoke_portal_access(
    client_id: int,
    contact_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_PORTAL_ROLES)),
):
    _get_active_client(db, client_id)
    contact = _get_contact(db, client_id, contact_id)

    # Деактивировать связанного пользователя
    if contact.portal_user_id:
        portal_user = db.query(User).filter(User.id == contact.portal_user_id).first()
        if portal_user:
            portal_user.is_active = False

    contact.portal_access = False
    contact.portal_role = None

    _write_audit(
        db, current_user,
        entity_type="client_contact",
        entity_id=contact_id,
        action="portal_access_revoke",
        old_values={"portal_access": True},
        new_values={"portal_access": False, "portal_role": None},
    )
    db.commit()
    db.refresh(contact)
    return contact


# ── Equipment & Tickets (read-only sub-resources) ─────────────────────────────

@router.get("/{client_id}/equipment", response_model=list[EquipmentResponse])
def list_client_equipment(
    client_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    if client_scope is not None and client_id != client_scope:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Клиент не найден"},
        )
    _get_active_client(db, client_id)
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
    client_scope: Optional[int] = Depends(get_client_scope),
):
    if client_scope is not None and client_id != client_scope:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Клиент не найден"},
        )
    _get_active_client(db, client_id)
    return (
        db.query(Ticket)
        .options(joinedload(Ticket.client))
        .filter(Ticket.client_id == client_id, Ticket.is_deleted.is_(False))
        .order_by(Ticket.created_at.desc())
        .all()
    )
