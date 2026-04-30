from datetime import datetime
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from fastapi import Request
from app.core.database import get_db
from app.core.security import verify_password, create_access_token, decode_token, hash_password
from app.models import User
from app.api.deps import get_current_user, _get_redis, oauth2_scheme
from pydantic import Field
from app.services.audit import log_action, extract_ip

router = APIRouter()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=128)


class UserInfo(BaseModel):
    id: int
    email: str
    full_name: str
    roles: Any

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user: UserInfo


# ─── Endpoints ───────────────────────────────────────────────────────────────

@router.post("/login")
def login(request: Request, body: LoginRequest, db: Session = Depends(get_db)):
    user = (
        db.query(User)
        .filter(User.email == body.email, User.is_active.is_(True), User.is_deleted.is_(False))
        .first()
    )
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный email или пароль",
        )

    user.last_login_at = datetime.utcnow()
    log_action(db, user_id=user.id, action="LOGIN", entity_type="user", entity_id=user.id, ip=extract_ip(request))
    db.commit()

    token = create_access_token({"sub": str(user.id)})
    return {
        "access_token": token,
        "token_type": "bearer",
        "must_change_password": getattr(user, "must_change_password", False),
        # top-level fields expected by tests and frontend
        "user_id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "roles": user.roles,
        # nested object kept for backwards compat
        "user": {
            "id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "roles": user.roles,
        },
    }


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    token: str = Depends(oauth2_scheme),
    _: User = Depends(get_current_user),
):
    """Отзывает текущий токен — добавляет jti в Redis-блоклист."""
    try:
        payload = decode_token(token)
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            ttl = max(1, int(exp - datetime.utcnow().timestamp()))
            _get_redis().setex(f"revoked_jti:{jti}", ttl, "1")
    except Exception:
        pass


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    body: ChangePasswordRequest,
    token: str = Depends(oauth2_scheme),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Смена пароля. Сбрасывает флаг must_change_password."""
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "WRONG_PASSWORD", "message": "Неверный текущий пароль"},
        )
    current_user.password_hash = hash_password(body.new_password)
    if getattr(current_user, "must_change_password", False):
        current_user.must_change_password = False
    # отзываем текущий токен — пользователь получит новый после повторного логина
    try:
        payload = decode_token(token)
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            ttl = max(1, int(exp - datetime.utcnow().timestamp()))
            _get_redis().setex(f"revoked_jti:{jti}", ttl, "1")
    except Exception:
        pass
    log_action(db, user_id=current_user.id, action="CHANGE_PASSWORD", entity_type="user", entity_id=current_user.id)
    db.commit()


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "roles": current_user.roles,
        "phone": current_user.phone,
        "telegram_chat_id": current_user.telegram_chat_id,
        "is_active": current_user.is_active,
        "last_login_at": current_user.last_login_at,
        "created_at": current_user.created_at,
    }
