from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import List
import json

from app.core.database import get_db
from app.core.security import decode_token
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


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
