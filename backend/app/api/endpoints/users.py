from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from app.core.database import get_db
from app.core.security import hash_password
from app.models import User
from app.api.deps import get_current_user, require_admin

router = APIRouter()


# ─── Schemas ────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: str
    role: str = "engineer"


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    role: Optional[str] = None


class PasswordChange(BaseModel):
    new_password: str


class UserOut(BaseModel):
    id: int
    username: str
    email: str
    full_name: str
    role: str
    is_active: bool

    class Config:
        from_attributes = True


# ─── Endpoints ──────────────────────────────────────────────────────────────

@router.get("/", response_model=List[UserOut])
def list_users(db: Session = Depends(get_db), _=Depends(get_current_user)):
    return db.query(User).filter(User.is_active == True).all()


@router.post("/", response_model=UserOut)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "Логин уже занят")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email уже используется")
    user = User(
        **data.model_dump(exclude={"password"}),
        password_hash=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/{user_id}", response_model=UserOut)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(user, k, v)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/password")
def change_password(
    user_id: int,
    data: PasswordChange,
    db: Session = Depends(get_db),
    _=Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return {"ok": True}


@router.delete("/{user_id}")
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if user_id == current_user.id:
        raise HTTPException(400, "Нельзя деактивировать собственную учётную запись")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    user.is_active = False
    db.commit()
    return {"ok": True}
