from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List, Optional
import json
import redis as _redis_lib

from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

_redis_client: Optional[_redis_lib.Redis] = None


def _get_redis() -> _redis_lib.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = _redis_lib.from_url(settings.redis_url, decode_responses=True)
    return _redis_client


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": "UNAUTHORIZED", "message": "Не авторизован"},
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        # проверяем блоклист отозванных токенов
        jti = payload.get("jti")
        if jti:
            try:
                if _get_redis().get(f"revoked_jti:{jti}"):
                    raise credentials_exception
            except _redis_lib.RedisError:
                pass  # Redis недоступен — не блокируем, продолжаем
    except HTTPException:
        raise
    except Exception:
        raise credentials_exception

    user = (
        db.query(User)
        .filter(User.id == int(user_id), User.is_active.is_(True), User.is_deleted.is_(False))
        .first()
    )
    if user is None:
        raise credentials_exception
    return user


def _get_user_roles(user: User) -> List[str]:
    roles = user.roles
    if isinstance(roles, str):
        try:
            roles = json.loads(roles)
        except Exception:
            roles = [roles]
    return roles if isinstance(roles, list) else []


def require_roles(*roles: str):
    """Factory: returns a dependency that checks the user has one of the given roles."""

    def _check(current_user: User = Depends(get_current_user)) -> User:
        user_roles = _get_user_roles(current_user)
        if not any(r in user_roles for r in roles):
            raise HTTPException(
                status_code=403,
                detail={"error": "FORBIDDEN", "message": "Недостаточно прав"},
            )
        return current_user

    return _check


def get_client_scope(current_user: User = Depends(get_current_user)) -> Optional[int]:
    """Return client_id if the current user is a client_user, else None.

    Endpoints use this to enforce row-level filtering: when not None, only
    records belonging to that client_id are visible.
    """
    user_roles = _get_user_roles(current_user)
    if "client_user" in user_roles:
        return current_user.client_id
    return None
