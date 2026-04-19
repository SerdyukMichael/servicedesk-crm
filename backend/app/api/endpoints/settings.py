from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.models import SystemSetting, User
from app.schemas import CurrencySettingResponse, CurrencySettingUpdate

router = APIRouter()

_CURRENCY_CODE_KEY = "currency_code"
_CURRENCY_NAME_KEY = "currency_name"


def _get_setting(db: Session, key: str) -> str:
    row = db.get(SystemSetting, key)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Настройка '{key}' не найдена")
    return row.value


@router.get("/currency", response_model=CurrencySettingResponse, summary="Получить системную валюту")
def get_currency(db: Session = Depends(get_db)):
    return CurrencySettingResponse(
        currency_code=_get_setting(db, _CURRENCY_CODE_KEY),
        currency_name=_get_setting(db, _CURRENCY_NAME_KEY),
    )


@router.put("/currency", response_model=CurrencySettingResponse, summary="Изменить системную валюту")
def update_currency(
    data: CurrencySettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    for key, value in [
        (_CURRENCY_CODE_KEY, data.currency_code),
        (_CURRENCY_NAME_KEY, data.currency_name),
    ]:
        row = db.get(SystemSetting, key)
        if row is None:
            row = SystemSetting(key=key, value=value, updated_by=current_user.id)
            db.add(row)
        else:
            row.value = value
            row.updated_by = current_user.id
    db.commit()
    return CurrencySettingResponse(
        currency_code=data.currency_code,
        currency_name=data.currency_name,
    )
