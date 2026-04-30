import math
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, desc, tuple_
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user, require_roles
from app.models import SystemSetting, User, ExchangeRate
from app.schemas import (
    CurrencySettingResponse, CurrencySettingUpdate,
    ExchangeRateCreate, ExchangeRateResponse, ExchangeRateHistoryItem,
    PaginatedResponse,
)

router = APIRouter()

_CURRENCY_CODE_KEY = "currency_code"
_CURRENCY_NAME_KEY = "currency_name"


def _get_setting(db: Session, key: str) -> str:
    row = db.get(SystemSetting, key)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Настройка '{key}' не найдена")
    return row.value


@router.get("/currency", response_model=CurrencySettingResponse, summary="Получить системную валюту")
def get_currency(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
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


# ── Exchange Rates ─────────────────────────────────────────────────────────────

@router.get(
    "/exchange-rates",
    response_model=list[ExchangeRateResponse],
    summary="Текущие курсы всех валют",
)
def list_exchange_rates(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Актуальный курс — запись с наибольшим set_at; при равенстве — с наибольшим id (BR-R-204, BR-R-206)."""
    # Находим (currency, max set_at) для каждой валюты
    max_date_subq = (
        db.query(
            ExchangeRate.currency,
            func.max(ExchangeRate.set_at).label("max_set_at"),
        )
        .group_by(ExchangeRate.currency)
        .subquery()
    )
    # Среди записей с max set_at берём наибольший id
    max_id_subq = (
        db.query(
            ExchangeRate.currency,
            func.max(ExchangeRate.id).label("max_id"),
        )
        .join(
            max_date_subq,
            (ExchangeRate.currency == max_date_subq.c.currency)
            & (ExchangeRate.set_at == max_date_subq.c.max_set_at),
        )
        .group_by(ExchangeRate.currency)
        .subquery()
    )
    rows = (
        db.query(ExchangeRate)
        .join(max_id_subq, ExchangeRate.id == max_id_subq.c.max_id)
        .order_by(ExchangeRate.currency)
        .all()
    )
    return rows


@router.post(
    "/exchange-rates",
    response_model=ExchangeRateResponse,
    status_code=201,
    summary="Установить курс валюты",
)
def create_exchange_rate(
    data: ExchangeRateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "accountant")),
):
    row = ExchangeRate(
        currency=data.currency,
        rate=data.rate,
        set_by=current_user.id,
        set_at=data.set_at if data.set_at is not None else datetime.now(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get(
    "/exchange-rates/{currency}",
    response_model=PaginatedResponse[ExchangeRateHistoryItem],
    summary="История курсов валюты",
)
def get_exchange_rate_history(
    currency: str,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    currency = currency.upper()
    total = db.query(func.count(ExchangeRate.id)).filter(ExchangeRate.currency == currency).scalar()
    if total == 0:
        raise HTTPException(status_code=404, detail=f"Курсы для валюты {currency} не найдены")

    rows = (
        db.query(ExchangeRate)
        .filter(ExchangeRate.currency == currency)
        .order_by(desc(ExchangeRate.set_at), desc(ExchangeRate.id))
        .offset((page - 1) * size)
        .limit(size)
        .all()
    )

    items = [
        ExchangeRateHistoryItem(
            id=r.id,
            currency=r.currency,
            rate=r.rate,
            set_by=r.set_by,
            set_by_name=r.setter.full_name,
            set_at=r.set_at,
            created_at=r.created_at,
        )
        for r in rows
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=math.ceil(total / size),
    )
