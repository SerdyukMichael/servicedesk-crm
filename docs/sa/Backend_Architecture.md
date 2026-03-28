# Backend Architecture — ServiceDesk CRM

**Версия:** 2.0 | **Дата:** 28.03.2026 | **Автор:** Solution Architect

> Документ описывает внутреннюю архитектуру backend-сервиса: слои, паттерны, middleware.
> Стек: Python 3.11 + FastAPI 0.111 + SQLAlchemy 2.0 + Alembic.
> **Примечание:** Celery/Redis и сервисный слой (`services/`) запланированы в будущих фазах, но ещё не реализованы в текущей кодовой базе.

---

## 1. Структура каталогов

```
backend/
├── app/
│   ├── main.py                   # FastAPI app (redirect_slashes=False), CORS, роуты
│   ├── api/
│   │   ├── router.py             # /api/v1 агрегатор всех роутов
│   │   ├── deps.py               # get_db, get_current_user, require_roles, _get_user_roles
│   │   └── endpoints/
│   │       ├── auth.py           # POST /auth/login
│   │       ├── users.py          # CRUD пользователей
│   │       ├── clients.py        # CRUD клиентов + контактов
│   │       ├── equipment.py      # CRUD оборудования
│   │       ├── tickets.py        # CRUD заявок + комментарии + акты + файлы
│   │       ├── parts.py          # Склад запчастей
│   │       ├── vendors.py        # Вендоры / поставщики
│   │       ├── invoices.py       # Счета и документы
│   │       ├── work_templates.py # Шаблоны работ
│   │       └── notifications.py  # Уведомления
│   ├── core/
│   │   ├── config.py             # Settings (pydantic-settings)
│   │   ├── database.py           # engine, SessionLocal, Base, get_db
│   │   └── security.py           # JWT (PyJWT), bcrypt
│   ├── models/
│   │   └── __init__.py           # Все SQLAlchemy ORM модели — 18 таблиц в одном файле
│   └── schemas/
│       └── __init__.py           # Все Pydantic v2 схемы в одном файле
│                                 # (PaginatedResponse, UserResponse, TicketResponse, ...)
├── alembic/
│   ├── env.py
│   └── versions/                 # Миграции
├── tests/
└── requirements.txt
```

> **Замечание по архитектуре:** Слой `services/` (бизнес-логика) и `tasks/` (Celery) **запланированы**, но в текущей реализации бизнес-логика размещена непосредственно в endpoint-функциях. Рефакторинг в отдельный сервисный слой — задача будущей фазы.

---

## 2. Архитектурные слои

```
HTTP Request
     │
     ▼
┌─────────────────────────────────────┐
│  Router / Endpoint (api/endpoints/) │  ← валидация Pydantic, RBAC-декоратор
│  FastAPI path function              │    бизнес-логика размещена здесь
└──────────────┬──────────────────────┘
               │  SQLAlchemy запросы
               ▼
┌─────────────────────────────────────┐
│  ORM Model (models/__init__.py)     │  ← SQLAlchemy 2.0 Mapped[]
│  session.query / session.execute    │    все модели в одном файле
└──────────────┬──────────────────────┘
               │
               ▼
          MySQL 8.0 / SQLite (тесты)
```

**Текущее состояние**: бизнес-логика размещена непосредственно в endpoint-функциях. Выделение в отдельный слой `services/` запланировано в будущей фазе.

---

## 3. Конфигурация (core/config.py)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # БД
    DATABASE_URL: str                     # mysql+pymysql://user:pass@mysql:3306/servicedesk

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 часов = рабочая смена

    # Redis / Celery
    REDIS_URL: str = "redis://redis:6379/0"

    # Email
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""

    # Лимиты файлов
    MAX_FILE_SIZE_MB: int = 20

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 4. База данных (core/database.py)

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,        # проверка соединения перед запросом
    pool_size=10,
    max_overflow=20,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass
```

---

## 5. Базовые миксины для моделей

```python
# models/mixins.py
from datetime import datetime
from sqlalchemy import Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

class TimestampMixin:
    """Автоматически заполняемые даты создания и обновления."""
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(),
                                                  onupdate=func.now(), nullable=False)

class SoftDeleteMixin:
    """Мягкое удаление. Физический DELETE запрещён (BR-R-009)."""
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
```

**Все модели** наследуют оба миксина. Исключение: `AuditLog` — только `TimestampMixin` (append-only, без `is_deleted`).

---

## 6. Зависимости FastAPI (api/deps.py)

```python
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
    """Парсит поле roles (JSON-столбец или список) → List[str]."""
    roles = user.roles
    if isinstance(roles, str):
        try:
            roles = json.loads(roles)
        except Exception:
            roles = [roles]
    return roles if isinstance(roles, list) else []


def require_roles(*roles: str):
    """RBAC-фабрика. Пример: Depends(require_roles('admin', 'svc_mgr'))"""
    def _check(current_user: User = Depends(get_current_user)) -> User:
        user_roles = _get_user_roles(current_user)
        if not any(r in user_roles for r in roles):
            raise HTTPException(
                status_code=403,
                detail={"error": "FORBIDDEN", "message": "Недостаточно прав"},
            )
        return current_user
    return _check
```

**Использование в эндпоинте:**
```python
@router.delete("/{id}")
def delete_template(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin", "svc_mgr")),
):
    ...
```

---

## 7. Стандарт ошибок (core/exceptions.py)

Реализует ADR-008.

```python
from fastapi import HTTPException

class AppException(HTTPException):
    def __init__(self, status_code: int, error_code: str, message: str, details: dict = None):
        super().__init__(
            status_code=status_code,
            detail={"error": error_code, "message": message, "details": details or {}}
        )

# 404
class NotFoundError(AppException):
    def __init__(self, entity: str, id):
        super().__init__(404, f"{entity.upper()}_NOT_FOUND", f"{entity} #{id} не найден(а)")

# 409
class ConflictError(AppException):
    def __init__(self, message: str):
        super().__init__(409, "CONFLICT", message)

# 400
class BusinessRuleError(AppException):
    def __init__(self, code: str, message: str):
        super().__init__(400, code, message)

# Конкретные исключения
class TicketNotFoundError(NotFoundError):
    def __init__(self, ticket_id: int):
        super().__init__("Заявка", ticket_id)

class EquipmentNotFoundError(NotFoundError):
    def __init__(self, equipment_id: int):
        super().__init__("Оборудование", equipment_id)

class UserNotFoundError(NotFoundError):
    def __init__(self, user_id: int):
        super().__init__("Пользователь", user_id)

class DuplicateSerialNumberError(ConflictError):
    def __init__(self, serial_number: str):
        super().__init__(f"Оборудование с серийным номером '{serial_number}' уже существует")

class TicketCloseWithoutActError(BusinessRuleError):
    def __init__(self):
        super().__init__("TICKET_CLOSE_WITHOUT_ACT", "Нельзя закрыть заявку без подписанного акта")

class EmptyWorkTemplateError(BusinessRuleError):
    def __init__(self):
        super().__init__("EMPTY_WORK_TEMPLATE", "Добавьте хотя бы одну работу в шаблон")
```

---

## 8. Безопасность (core/security.py)

```python
import jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict) -> str:
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode({**data, "exp": expire}, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except jwt.PyJWTError:
        return None
```

---

## 9. Сервисный слой — все сервисы

### 9.1 AuthService

```python
class AuthService:
    def login(self, db: Session, email: str, password: str) -> dict:
        """
        Возвращает {"access_token": str, "token_type": "bearer"}.
        Raises: HTTPException 401 при неверных данных.
        """

    def logout(self, db: Session, user_id: int) -> None:
        """
        MVP: stateless JWT — logout только на стороне клиента (удалить токен).
        Метод-заглушка для будущей blacklist.
        """
```

### 9.2 UserService

```python
class UserService:
    def get_list(self, db: Session, skip: int, limit: int, role: str | None) -> list[User]:
        """Список активных пользователей (is_deleted=False) с фильтром по роли."""

    def get_by_id(self, db: Session, user_id: int) -> User:
        """Raises: UserNotFoundError"""

    def create(self, db: Session, data: UserCreate) -> User:
        """
        Хеширует пароль. Raises: ConflictError при дублировании email.
        Пишет в audit_log (action='user_created').
        """

    def update(self, db: Session, user_id: int, data: UserUpdate) -> User:
        """Обновляет поля. Пароль — только если передан new_password."""

    def soft_delete(self, db: Session, user_id: int) -> None:
        """Устанавливает is_deleted=True. Нельзя удалить самого себя (BR-R-005)."""

    def get_engineers(self, db: Session) -> list[User]:
        """Список инженеров для назначения на заявку."""
```

### 9.3 TicketService

```python
class TicketService:
    def get_list(self, db: Session, filters: TicketFilters, skip: int, limit: int) -> tuple[list[Ticket], int]:
        """
        Фильтры: status, priority, engineer_id, client_id, date_from, date_to.
        Возвращает (items, total) для пагинации.
        Filters сохраняются в сессии — логика на фронте (React Query params).
        """

    def get_by_id(self, db: Session, ticket_id: int) -> Ticket:
        """Raises: TicketNotFoundError"""

    def create(self, db: Session, data: TicketCreate, created_by: int) -> Ticket:
        """
        Генерирует номер T-YYYYMMDD-XXXX (например T-20260328-0001). Статус 'new'.
        SLA deadline = created_at + SLA_HOURS[priority].
        Если передан work_template_id — применяет шаблон.
        """

    def assign_engineer(self, db: Session, ticket_id: int, engineer_id: int) -> Ticket:
        """Статус → 'in_progress'. Raises: TicketNotFoundError, UserNotFoundError."""

    def update_status(self, db: Session, ticket_id: int, new_status: str, actor: User) -> Ticket:
        """
        Матрица переходов статусов:
          new           → assigned, cancelled
          assigned      → in_progress, cancelled
          in_progress   → waiting_part, on_review, completed
          waiting_part  → in_progress, cancelled
          on_review     → completed, in_progress
          completed     → closed, in_progress
          closed        → (финальный, без переходов)
          cancelled     → (финальный, без переходов)
        Raises: BusinessRuleError при нарушении матрицы.
        """

    def close(self, db: Session, ticket_id: int, actor: User) -> Ticket:
        """
        Проверяет наличие подписанного work_act (status='signed').
        Raises: TicketCloseWithoutActError если акта нет.
        Устанавливает closed_at = now().
        """

    def apply_template(self, db: Session, ticket_id: int, template_id: int) -> Ticket:
        """Применяет шаблон работ к существующей заявке. Перезаписывает work_items."""

    def add_comment(self, db: Session, ticket_id: int, author_id: int, text: str) -> Comment:
        """Добавляет комментарий. Уведомляет всех участников заявки."""

    def get_comments(self, db: Session, ticket_id: int) -> list[Comment]:
        pass
```

### 9.4 SLAService

```python
class SLAService:
    SLA_HOURS = {
        "critical": 4,
        "high": 8,
        "medium": 24,
        "low": 72,
    }

    def check_violations(self, db: Session) -> int:
        """
        Вызывается Celery каждые 5 минут (tasks/sla.py).
        Находит все открытые заявки, где now() > deadline.
        Устанавливает sla_violated=True, создаёт уведомление руководителю.
        Возвращает количество новых нарушений.
        """

    def calculate_deadline(self, ticket: Ticket) -> datetime:
        """Дедлайн = created_at + SLA_HOURS[priority]."""

    def get_sla_stats(self, db: Session, date_from: date, date_to: date) -> dict:
        """
        Статистика для отчёта (UC-910):
          {total, closed_in_sla, sla_compliance_pct, avg_resolution_hours, by_engineer: [...]}
        """
```

### 9.5 EquipmentService

```python
class EquipmentService:
    def get_list(self, db: Session, client_id: int | None, model_id: int | None,
                 warranty_status: str | None, skip: int, limit: int) -> tuple[list[Equipment], int]:
        pass

    def get_by_id(self, db: Session, equipment_id: int) -> Equipment:
        """Raises: EquipmentNotFoundError"""

    def create(self, db: Session, data: EquipmentCreate) -> Equipment:
        """Raises: DuplicateSerialNumberError если serial_number уже существует."""

    def update(self, db: Session, equipment_id: int, data: EquipmentUpdate) -> Equipment:
        pass

    def soft_delete(self, db: Session, equipment_id: int) -> None:
        pass

    def recalc_warranty_status(self, db: Session) -> int:
        """
        Вызывается Celery ежедневно в 03:00 (tasks/warranty.py).
        Сравнивает warranty_expiry с today():
          - warranty_expiry > today + 30 дней → 'valid'
          - today < warranty_expiry ≤ today + 30 дней → 'expiring_soon'
          - warranty_expiry ≤ today → 'expired'
        Возвращает количество обновлённых записей.
        """

    def get_history(self, db: Session, equipment_id: int) -> list[EquipmentHistory]:
        """История ремонтов и ТО по единице оборудования (UC-1002)."""

    def get_maintenance_schedule(self, db: Session, equipment_id: int) -> list[MaintenanceSchedule]:
        pass
```

### 9.6 MaintenanceService

```python
class MaintenanceService:
    def create_scheduled_tickets(self, db: Session) -> int:
        """
        Вызывается Celery ежедневно в 08:00 (tasks/maintenance.py).
        Находит maintenance_schedules, где next_date = today + 7 дней.
        Создаёт заявки типа 'maintenance' через TicketService.create().
        Обновляет next_date согласно interval_days.
        Возвращает количество созданных заявок.
        """

    def create_schedule(self, db: Session, equipment_id: int, interval_days: int) -> MaintenanceSchedule:
        pass

    def update_schedule(self, db: Session, schedule_id: int, data: MaintenanceScheduleUpdate) -> MaintenanceSchedule:
        pass
```

### 9.7 FileService

Реализует ADR-001 (BLOB в MySQL).

```python
class FileService:
    MAX_SIZE_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024  # 20 МБ

    ALLOWED_MIME_TYPES = {
        "equipment_document": ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "application/zip"],
        "ticket_attachment": ["image/jpeg", "image/png", "application/pdf",
                               "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                               "application/zip"],
        "work_act_photo": ["image/jpeg", "image/png"],
    }

    def upload(self, db: Session, file: UploadFile, entity_type: str, entity_id: int, uploaded_by: int) -> int:
        """
        1. Проверяет размер (≤ MAX_SIZE_BYTES). Raises: BusinessRuleError FILE_TOO_LARGE.
        2. Проверяет MIME-тип. Raises: BusinessRuleError UNSUPPORTED_FILE_TYPE.
        3. Читает file.read() → bytes.
        4. Сохраняет в equipment_documents или ticket_attachments.
        5. Возвращает file_id.
        """

    def get_stream(self, db: Session, file_id: int, entity_type: str) -> tuple[bytes, str, str]:
        """
        Возвращает (file_data, mime_type, file_name).
        Raises: NotFoundError если файл не найден.
        Используется в GET /files/{entity_type}/{id} → StreamingResponse.
        """

    def delete(self, db: Session, file_id: int, entity_type: str) -> None:
        """Физическое удаление BLOB (файлы не soft-delete, экономия места)."""
```

**Эндпоинт стриминга:**
```python
# api/endpoints/files.py
from fastapi.responses import StreamingResponse
import io

@router.get("/equipment-documents/{doc_id}")
def download_equipment_doc(doc_id: int, db: Session = Depends(get_db),
                            _: User = Depends(get_current_user)):
    data, mime_type, file_name = FileService().get_stream(db, doc_id, "equipment_document")
    return StreamingResponse(
        io.BytesIO(data),
        media_type=mime_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'}
    )
```

### 9.8 NotificationService

Реализует ADR-003.

```python
class NotificationService:
    def notify(self, db: Session, user_id: int, event_type: str, message: str, entity_id: int | None = None) -> None:
        """
        1. Проверяет notification_settings для user_id + event_type.
        2. Если in_app включён (всегда) — создаёт запись в notifications.
        3. Если email включён — ставит задачу tasks.notifications.send_email.delay(...).
        4. Если telegram включён и user.telegram_chat_id заполнен — ставит tasks.notifications.send_telegram.delay(...).
        """

    def get_unread_count(self, db: Session, user_id: int) -> int:
        """GET /notifications/unread → {"count": N}. Polling каждые 30 сек."""

    def get_list(self, db: Session, user_id: int, skip: int, limit: int) -> tuple[list[Notification], int]:
        pass

    def mark_read(self, db: Session, notification_id: int, user_id: int) -> None:
        """Raises: NotFoundError если уведомление не найдено или принадлежит другому пользователю."""

    def mark_all_read(self, db: Session, user_id: int) -> int:
        """Отмечает все непрочитанные. Возвращает количество обновлённых."""

    def get_settings(self, db: Session, user_id: int) -> list[NotificationSetting]:
        pass

    def update_settings(self, db: Session, user_id: int, updates: list[NotificationSettingUpdate]) -> list[NotificationSetting]:
        """
        Нельзя отключить in_app (CHECK constraint на уровне БД + валидация здесь).
        Raises: BusinessRuleError CANNOT_DISABLE_INAPP.
        """

    def reset_settings(self, db: Session, user_id: int) -> None:
        """UC-1401 АП-1: сброс к defaults (все каналы включены для всех событий)."""

    def _send_email(self, to_email: str, subject: str, body: str) -> None:
        """Использует smtplib.SMTP. Вызывается из Celery-задачи (не напрямую)."""

    def _send_telegram(self, chat_id: str, text: str) -> None:
        """httpx.post() к Telegram Bot API. Вызывается из Celery-задачи."""
```

### 9.9 ReportService

```python
class ReportService:
    def generate_ticket_report(self, db: Session, date_from: date, date_to: date,
                               engineer_id: int | None) -> dict:
        """
        UC-910. Возвращает структуру:
        {
          "period": {"from": ..., "to": ...},
          "total_tickets": N,
          "by_status": {"new": N, "in_progress": N, ...},
          "by_priority": {"critical": N, ...},
          "sla_compliance": {"compliant": N, "violated": N, "pct": 95.2},
          "avg_resolution_hours": 6.4,
          "engineers": [{"id": 1, "name": "...", "tickets": N, "sla_pct": 94.0}, ...],
          "top_equipment_models": [...],
        }
        """

    def export_pdf(self, report_data: dict) -> bytes:
        """Генерирует PDF через reportlab. Возвращает bytes."""

    def export_xlsx(self, report_data: dict) -> bytes:
        """Генерирует XLSX через openpyxl. Возвращает bytes."""

    def generate_equipment_report(self, db: Session, client_id: int | None, model_id: int | None) -> dict:
        """UC-1006. Парк оборудования с фильтрацией."""
```

### 9.10 AuditService

```python
class AuditService:
    def log(self, db: Session, user_id: int | None, action: str,
            entity_type: str, entity_id: int | None, details: dict | None = None) -> None:
        """
        Записывает в audit_log. Вызывается из всех сервисов при изменениях.
        user_id=None допустим для системных действий (Celery tasks).
        details — JSON-поле с diff'ом изменений или дополнительным контекстом.
        """

    def get_log(self, db: Session, entity_type: str | None, entity_id: int | None,
                user_id: int | None, skip: int, limit: int) -> tuple[list[AuditLog], int]:
        """GET /audit — доступен только admin и director."""
```

---

## 10. Celery (запланировано, не реализовано)

> **Статус:** Celery и Redis ещё не реализованы в текущей кодовой базе. Раздел описывает целевую архитектуру для будущей реализации.

```python
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "servicedesk",
    broker=settings.REDIS_URL,                    # redis://redis:6379/0
    backend=settings.REDIS_URL.replace("/0", "/1"),  # redis://redis:6379/1
    include=[
        "app.tasks.sla",
        "app.tasks.maintenance",
        "app.tasks.warranty",
        "app.tasks.notifications",
    ]
)

celery_app.conf.beat_schedule = {
    "check-sla-violations": {
        "task": "app.tasks.sla.check_sla_violations",
        "schedule": 300,           # каждые 5 минут
    },
    "create-maintenance-tickets": {
        "task": "app.tasks.maintenance.create_scheduled_tickets",
        "schedule": crontab(hour=8, minute=0),    # ежедневно 08:00
    },
    "recalc-warranty-status": {
        "task": "app.tasks.warranty.recalc_warranty_status",
        "schedule": crontab(hour=3, minute=0),    # ежедневно 03:00
    },
}

celery_app.conf.timezone = "Europe/Moscow"
celery_app.conf.task_serializer = "json"
celery_app.conf.result_expires = 3600   # хранить результаты 1 час
```

**Celery задачи (tasks/sla.py — пример):**
```python
from app.celery_app import celery_app
from app.core.database import SessionLocal
from app.services.sla_service import SLAService

@celery_app.task(name="app.tasks.sla.check_sla_violations", bind=True, max_retries=3)
def check_sla_violations(self):
    db = SessionLocal()
    try:
        count = SLAService().check_violations(db)
        db.commit()
        return {"violations_found": count}
    except Exception as exc:
        db.rollback()
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()
```

---

## 11. main.py — приложение

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import api_router

app = FastAPI(
    title="ServiceDesk CRM API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    redirect_slashes=False,   # предотвращает 307 redirect, теряющий Authorization header
)

# CORS — перед продом заменить * на конкретные домены
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok"}
```

---

## 12. Паттерн добавления нового модуля

При добавлении нового модуля (например, Module 11 — Рекламации вендорам) выполнить в порядке:

1. **Миграция**: `alembic revision --autogenerate -m "add vendor_claims"` → добавить таблицу
2. **Модель**: `models/vendor_claim.py` → наследовать `TimestampMixin + SoftDeleteMixin`
3. **Схемы**: `schemas/vendor_claim.py` → `VendorClaimBase / Create / Update / Response`
4. **Сервис**: `services/vendor_claim_service.py` → методы CRUD + бизнес-правила
5. **Эндпоинт**: `api/endpoints/vendor_claims.py` → router с тегом, `Depends(require_roles(...))`
6. **Регистрация**: `api/router.py` → `api_router.include_router(vendor_claims.router, prefix="/vendor-claims", tags=["Рекламации"])`
7. **Тесты**: `tests/integration/test_vendor_claims.py`

---

## 13. Пагинация — стандартный ответ

```python
# schemas/__init__.py
from pydantic import BaseModel
from typing import Generic, TypeVar, List

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int
```

**Стандартный эндпоинт с пагинацией:**
```python
@router.get("", response_model=PaginatedResponse[TicketResponse])
def list_tickets(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=200),
    status: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Ticket).filter(Ticket.is_deleted.is_(False))
    # ... фильтры ...
    total = q.count()
    skip = (page - 1) * size
    items = q.order_by(Ticket.created_at.desc()).offset(skip).limit(size).all()
    pages = max(1, (total + size - 1) // size)
    return PaginatedResponse(items=items, total=total, page=page, size=size, pages=pages)
```

---

## 14. Матрица ролей → эндпоинты (сводка)

| Эндпоинт | Роли |
|---|---|
| `POST /auth/login` | все |
| `GET /users` | admin, svc_mgr, director |
| `POST /users` | admin |
| `DELETE /users/{id}` | admin |
| `GET /tickets` | все аутентифицированные |
| `POST /tickets` | admin, svc_mgr |
| `PATCH /tickets/{id}/assign` | admin, svc_mgr |
| `PATCH /tickets/{id}/status` | engineer, svc_mgr, admin |
| `DELETE /tickets/{id}` | admin |
| `POST /tickets/{id}/attachments` | engineer, svc_mgr, admin |
| `GET /equipment` | все |
| `POST /equipment` | admin, svc_mgr |
| `DELETE /equipment/{id}` | admin |
| `POST /equipment/{id}/documents` | engineer, svc_mgr, admin |
| `GET /work-templates` | all authenticated |
| `POST /work-templates` | admin, svc_mgr |
| `PUT /work-templates/{id}` | admin, svc_mgr |
| `DELETE /work-templates/{id}` | admin, svc_mgr |
| `GET /reports/tickets` | director, svc_mgr |
| `GET /reports/equipment` | director, svc_mgr, admin |
| `GET /notifications` | все |
| `GET /audit` | admin, director |

Полная матрица: `docs/RBAC_Matrix.md`.

---

## 15. Переменные окружения (.env)

```env
# БД
DATABASE_URL=mysql+pymysql://sduser:sdpass@mysql:3306/servicedesk
MYSQL_ROOT_PASSWORD=rootpass
MYSQL_DATABASE=servicedesk
MYSQL_USER=sduser
MYSQL_PASSWORD=sdpass

# JWT
SECRET_KEY=<генерировать: python -c "import secrets; print(secrets.token_hex(32))">
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480

# Redis
REDIS_URL=redis://redis:6379/0

# Email
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=

# Telegram
TELEGRAM_BOT_TOKEN=

# Лимиты
MAX_FILE_SIZE_MB=20
```
