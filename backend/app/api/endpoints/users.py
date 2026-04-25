from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import hash_password
from app.models import User
from app.api.deps import get_current_user, require_roles, get_client_scope
from app.schemas import UserCreate, UserUpdate, UserResponse, PaginatedResponse
from app.services.audit import log_action

router = APIRouter()

_READ_ROLES = ("admin", "svc_mgr", "director", "client_user")
_ADMIN = ("admin",)


@router.get("", response_model=PaginatedResponse[UserResponse])
def list_users(
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_READ_ROLES)),
    client_scope: Optional[int] = Depends(get_client_scope),
):
    q = db.query(User).filter(User.is_deleted.is_(False))
    # client_user sees only other users of the same organisation
    if client_scope is not None:
        q = q.filter(User.client_id == client_scope)
    if is_active is not None:
        q = q.filter(User.is_active.is_(is_active))
    if role:
        q = q.filter(User.roles.contains(role))
    total = q.count()
    skip = (page - 1) * size
    items = q.order_by(User.id).offset(skip).limit(size).all()
    pages = max(1, (total + size - 1) // size)
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ADMIN)),
):
    if db.query(User).filter(User.email == data.email, User.is_deleted.is_(False)).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"error": "CONFLICT", "message": "Email уже используется"},
        )
    user = User(
        email=data.email,
        full_name=data.full_name,
        password_hash=hash_password(data.password),
        roles=data.roles,
        phone=data.phone,
        telegram_chat_id=data.telegram_chat_id,
        is_active=data.is_active,
    )
    db.add(user)
    db.flush()
    log_action(db, user_id=current_user.id, action="CREATE", entity_type="user", entity_id=user.id,
               new={"email": user.email, "full_name": user.full_name, "roles": user.roles})
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(*_READ_ROLES)),
):
    user = db.query(User).filter(User.id == user_id, User.is_deleted.is_(False)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Пользователь не найден"},
        )
    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ADMIN)),
):
    user = db.query(User).filter(User.id == user_id, User.is_deleted.is_(False)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Пользователь не найден"},
        )
    update_data = data.model_dump(exclude_none=True)
    changed_fields = [k for k in update_data if k != "password"]
    old_vals = {k: getattr(user, k) for k in changed_fields}
    if "password" in update_data:
        user.password_hash = hash_password(update_data.pop("password"))
        old_vals["password"] = "***"
        update_data["password"] = "***"
    for k, v in update_data.items():
        if k != "password":
            setattr(user, k, v)
    log_action(db, user_id=current_user.id, action="UPDATE", entity_type="user", entity_id=user.id,
               old=old_vals, new={k: v for k, v in update_data.items()})
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*_ADMIN)),
):
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "CANNOT_DELETE_SELF", "message": "Нельзя удалить свою учётную запись"},
        )
    user = db.query(User).filter(User.id == user_id, User.is_deleted.is_(False)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "NOT_FOUND", "message": "Пользователь не найден"},
        )
    user.is_deleted = True
    user.is_active = False
    log_action(db, user_id=current_user.id, action="DELETE", entity_type="user", entity_id=user.id,
               old={"email": user.email, "full_name": user.full_name})
    db.commit()
