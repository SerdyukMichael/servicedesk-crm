"""
Pydantic v2 schemas for ServiceDesk CRM — all modules.
"""

from __future__ import annotations

from datetime import datetime, date
from decimal import Decimal
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, EmailStr, ConfigDict, Field, field_validator, model_validator

T = TypeVar("T")


# ── Generic helpers ───────────────────────────────────────────────────────────

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int


class ErrorResponse(BaseModel):
    error: str
    message: str


# ── Users ─────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    roles: List[str] = ["engineer"]
    phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    is_active: bool = True


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    roles: Optional[List[str]] = None
    phone: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str
    roles: List[str]
    phone: Optional[str]
    telegram_chat_id: Optional[str]
    is_active: bool
    is_deleted: bool
    last_login_at: Optional[datetime]
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _set_last_login(self) -> "UserResponse":
        if self.last_login is None:
            self.last_login = self.last_login_at
        return self

    @field_validator("roles", mode="before")
    @classmethod
    def parse_roles(cls, v: Any) -> List[str]:
        import json as _json
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = _json.loads(v)
                return parsed if isinstance(parsed, list) else [v]
            except Exception:
                return [v] if v else []
        return []


# ── Client Contacts ───────────────────────────────────────────────────────────

class ClientContactCreate(BaseModel):
    name: str
    position: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_primary: bool = False
    is_active: bool = True


class ClientContactUpdate(BaseModel):
    name: Optional[str] = None
    position: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None


class ClientContactPortalAccess(BaseModel):
    email: Optional[str] = None          # переопределить email для портала
    portal_role: str = "client_user"     # client_user | client_admin


class ClientContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    client_id: int
    name: str
    position: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    is_primary: bool
    is_active: bool
    portal_access: bool
    portal_role: Optional[str]
    portal_user_id: Optional[int]
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime


class ClientContactPortalGrantResponse(ClientContactResponse):
    """Extended response after portal access grant — includes one-time password."""
    temporary_password: Optional[str] = None


# ── Clients ───────────────────────────────────────────────────────────────────

class ClientCreate(BaseModel):
    name: str
    inn: str
    city: str
    contract_type: str
    contract_number: str
    kpp: Optional[str] = None
    legal_address: Optional[str] = None
    contract_start: Optional[date] = None
    contract_end: Optional[date] = None        # maps to contract_valid_until
    contract_valid_until: Optional[date] = None
    address: Optional[str] = None
    manager_id: Optional[int] = None

    @field_validator("inn", "city", "contract_type", "contract_number", mode="before")
    @classmethod
    def required_not_empty(cls, v: str) -> str:
        if not v or not str(v).strip():
            raise ValueError("Поле обязательно для заполнения")
        return v


class ClientUpdate(BaseModel):
    name: Optional[str] = None
    inn: Optional[str] = None
    kpp: Optional[str] = None
    legal_address: Optional[str] = None
    contract_type: Optional[str] = None
    contract_number: Optional[str] = None
    contract_start: Optional[date] = None
    contract_end: Optional[date] = None        # maps to contract_valid_until
    contract_valid_until: Optional[date] = None
    address: Optional[str] = None
    city: Optional[str] = None
    manager_id: Optional[int] = None


class ClientResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    inn: Optional[str]
    kpp: Optional[str]
    legal_address: Optional[str]
    contract_type: str = "none"
    contract_number: Optional[str]
    contract_start: Optional[date]
    contract_valid_until: Optional[date]
    contract_end: Optional[date] = None
    address: Optional[str]
    city: Optional[str]
    manager_id: Optional[int]
    manager: Optional["UserResponse"] = None
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    @field_validator("contract_type", mode="before")
    @classmethod
    def default_contract_type(cls, v: object) -> str:
        if not v or (isinstance(v, str) and not v.strip()):
            return "none"
        return str(v)

    @model_validator(mode="after")
    def _aliases(self) -> "ClientResponse":
        if self.contract_end is None:
            self.contract_end = self.contract_valid_until
        return self


# ── Equipment Models ──────────────────────────────────────────────────────────

class EquipmentModelCreate(BaseModel):
    name: str
    manufacturer: Optional[str] = None
    category: str = "other"
    description: Optional[str] = None
    warranty_months_default: Optional[int] = None


class EquipmentModelUpdate(BaseModel):
    name: Optional[str] = None
    manufacturer: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    warranty_months_default: Optional[int] = None


class EquipmentModelResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    manufacturer: Optional[str]
    category: str
    description: Optional[str]
    warranty_months_default: Optional[int]
    is_active: bool


# ── Equipment ─────────────────────────────────────────────────────────────────

class EquipmentCreate(BaseModel):
    client_id: int
    model_id: int
    serial_number: str
    location: Optional[str] = None
    status: str = "active"
    installed_at: Optional[date] = None
    warranty_until: Optional[date] = None
    manufacture_date: Optional[date] = None
    sale_date: Optional[date] = None
    warranty_start: Optional[date] = None
    firmware_version: Optional[str] = None
    notes: Optional[str] = None


class EquipmentUpdate(BaseModel):
    client_id: Optional[int] = None
    model_id: Optional[int] = None
    serial_number: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    installed_at: Optional[date] = None
    warranty_until: Optional[date] = None
    manufacture_date: Optional[date] = None
    sale_date: Optional[date] = None
    warranty_start: Optional[date] = None
    firmware_version: Optional[str] = None
    notes: Optional[str] = None


def _compute_warranty_status(warranty_until: Optional[date]) -> str:
    if not warranty_until:
        return "unknown"
    from datetime import timedelta
    today = date.today()
    if today > warranty_until:
        return "expired"
    if today >= warranty_until - timedelta(days=30):
        return "expiring"
    return "on_warranty"


class EquipmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    client_id: int
    client: Optional[ClientResponse] = None
    model_id: int
    model: Optional[EquipmentModelResponse] = None
    serial_number: str
    location: Optional[str] = None
    address: Optional[str] = None
    status: str
    installed_at: Optional[date] = None
    installation_date: Optional[date] = None
    warranty_until: Optional[date] = None
    warranty_end: Optional[date] = None
    manufacture_date: Optional[date] = None
    sale_date: Optional[date] = None
    warranty_start: Optional[date] = None
    firmware_version: Optional[str] = None
    warranty_status: str = "unknown"
    notes: Optional[str]
    is_deleted: bool
    created_at: datetime
    updated_at: datetime

    @model_validator(mode='after')
    def _aliases(self) -> 'EquipmentResponse':
        if self.installation_date is None:
            self.installation_date = self.installed_at
        if self.warranty_end is None:
            self.warranty_end = self.warranty_until
        if self.address is None:
            self.address = self.location
        self.warranty_status = _compute_warranty_status(self.warranty_until)
        return self


# ── Equipment Lookup ─────────────────────────────────────────────────────────

class EquipmentLookupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    equipment_id: int
    serial_number: str
    model_name: str
    client_id: int
    client_name: str
    is_under_warranty: bool
    warranty_until: Optional[date]


# ── Work Templates ────────────────────────────────────────────────────────────

class WorkTemplateStepCreate(BaseModel):
    step_order: int
    description: str
    estimated_minutes: Optional[int] = None


class WorkTemplateStepResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_id: int
    step_order: int
    description: str
    estimated_minutes: Optional[int]


class WorkTemplateCreate(BaseModel):
    name: str
    equipment_model_id: Optional[int] = None
    description: Optional[str] = None
    is_active: bool = True
    steps: List[WorkTemplateStepCreate]


class WorkTemplateUpdate(BaseModel):
    name: Optional[str] = None
    equipment_model_id: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    steps: Optional[List[WorkTemplateStepCreate]] = None


class WorkTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    equipment_model_id: Optional[int]
    description: Optional[str]
    is_active: bool
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime
    steps: List[WorkTemplateStepResponse]


# ── Tickets ───────────────────────────────────────────────────────────────────

class TicketCreate(BaseModel):
    client_id: int
    equipment_id: Optional[int] = None
    title: str
    description: Optional[str] = None
    type: str = Field("repair", pattern="^(repair|maintenance|diagnostics|installation)$")
    priority: str = Field("medium", pattern="^(low|medium|high|critical)$")
    work_template_id: Optional[int] = None


class TicketUpdate(BaseModel):
    client_id: Optional[int] = None
    equipment_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    priority: Optional[str] = None
    work_template_id: Optional[int] = None


class TicketAssign(BaseModel):
    engineer_id: int


class TicketStatusChange(BaseModel):
    status: str
    comment: Optional[str] = None


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    client_id: int
    client: Optional[ClientResponse] = None
    equipment_id: Optional[int]
    equipment: Optional[EquipmentResponse] = None
    assigned_to: Optional[int]
    engineer: Optional[UserResponse] = Field(None, validation_alias='assignee')
    created_by: Optional[UserResponse] = Field(None, validation_alias='creator')
    title: str
    description: Optional[str]
    type: str
    priority: str
    status: str
    sla_deadline: Optional[datetime]
    assigned_at: Optional[datetime]
    sla_reaction_deadline: Optional[datetime]
    sla_resolution_deadline: Optional[datetime]
    sla_reaction_violated: bool
    sla_resolution_violated: bool
    work_template_id: Optional[int]
    closed_at: Optional[datetime]
    is_deleted: bool
    created_at: datetime
    updated_at: datetime


# ── Ticket Status History ─────────────────────────────────────────────────────

class TicketStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    from_status: Optional[str]
    to_status: str
    changed_by: Optional[int]
    changer: Optional["UserResponse"] = None
    comment: Optional[str]
    changed_at: datetime


# ── Comments ──────────────────────────────────────────────────────────────────

class CommentCreate(BaseModel):
    text: str = Field(..., min_length=1)
    is_internal: bool = False


class CommentAuthorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str


class CommentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    user_id: int
    text: str
    is_internal: bool
    author: Optional[CommentAuthorResponse] = Field(None, validation_alias="user")
    created_at: datetime


# ── Work Acts ─────────────────────────────────────────────────────────────────

class WorkActItemCreate(BaseModel):
    item_type: str  # "service" | "part"
    service_id: Optional[int] = None
    part_id: Optional[int] = None
    warehouse_id: Optional[int] = None  # склад-источник (только для part)
    name: str
    quantity: Decimal = Decimal("1")
    unit: str = "шт"
    unit_price: Decimal = Decimal("0")
    sort_order: int = 0


class WorkActItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    work_act_id: int
    item_type: str
    service_id: Optional[int]
    part_id: Optional[int]
    warehouse_id: Optional[int]
    name: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    total: Decimal
    sort_order: int


class WorkActCreate(BaseModel):
    work_description: Optional[str] = None
    parts_used: Optional[Any] = None       # оставить для совместимости
    total_time_minutes: Optional[int] = None
    items: List[WorkActItemCreate] = []    # новые структурированные позиции


class WorkActUpdate(BaseModel):
    work_description: Optional[str] = None
    parts_used: Optional[Any] = None
    total_time_minutes: Optional[int] = None
    items: Optional[List[WorkActItemCreate]] = None  # None = не менять, [] = удалить все
    force_save: bool = False  # True = сохранить акт даже если счёт оплачен и суммы расходятся


class WorkActResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    ticket_id: int
    engineer_id: int
    work_description: Optional[str]
    parts_used: Optional[Any]
    total_time_minutes: Optional[int]
    signed_by: Optional[int]
    signed_at: Optional[datetime]
    created_at: datetime
    items: List[WorkActItemResponse] = []


# ── Spare Parts ───────────────────────────────────────────────────────────────

class SparePartCreate(BaseModel):
    sku: str
    name: str
    category: Optional[str] = None
    unit: str = "шт"
    quantity: int = 0
    min_quantity: int = 0
    unit_price: Decimal = Decimal("0.00")
    currency: str = "RUB"
    vendor_id: Optional[int] = None
    description: Optional[str] = None
    is_active: bool = True


class SparePartUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    quantity: Optional[int] = None
    min_quantity: Optional[int] = None
    unit_price: Optional[Decimal] = None
    currency: Optional[str] = None
    vendor_id: Optional[int] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class SparePartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    name: str
    category: Optional[str]
    unit: str
    quantity: int
    min_quantity: int
    unit_price: float
    price: Optional[float] = None   # alias для фронтенда (number в JSON)
    currency: str
    vendor_id: Optional[int]
    description: Optional[str]
    is_active: bool

    @model_validator(mode='after')
    def _set_price(self) -> 'SparePartResponse':
        if self.price is None:
            self.price = self.unit_price
        return self


class StockAdjust(BaseModel):
    delta: int
    reason: str


class SparePartPriceUpdate(BaseModel):
    new_price: Decimal
    currency: str = "RUB"
    reason: str

    @field_validator("new_price")
    @classmethod
    def validate_price(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Цена не может быть отрицательной")
        return v

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if len(v.strip()) < 5:
            raise ValueError("Причина должна содержать минимум 5 символов")
        return v


class PriceHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entity_type: str
    entity_id: int
    old_price: Decimal
    new_price: Decimal
    currency: str
    reason: str
    changed_by: int
    changed_at: datetime


# ── Vendors ───────────────────────────────────────────────────────────────────

class VendorCreate(BaseModel):
    name: str
    inn: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool = True


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    inn: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class VendorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    inn: Optional[str]
    contact_name: Optional[str]
    contact_phone: Optional[str]
    contact_email: Optional[str]
    website: Optional[str]
    notes: Optional[str]
    is_active: bool


# ── Invoices ──────────────────────────────────────────────────────────────────

class InvoiceItemCreate(BaseModel):
    description: str
    quantity: Decimal = Decimal("1")
    unit: str = "шт"
    unit_price: Decimal
    sort_order: int = 0
    item_type: Optional[str] = None   # "service" | "part" | "manual"
    service_id: Optional[int] = None
    part_id: Optional[int] = None


class InvoiceItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    description: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    total: Decimal
    sort_order: int
    item_type: Optional[str] = None
    service_id: Optional[int] = None
    part_id: Optional[int] = None


class InvoiceCreate(BaseModel):
    client_id: int
    ticket_id: Optional[int] = None
    type: str = "service"
    issue_date: date
    due_date: Optional[date] = None
    vat_rate: Decimal = Decimal("22.00")
    notes: Optional[str] = None
    items: List[InvoiceItemCreate]


class InvoiceUpdate(BaseModel):
    client_id: Optional[int] = None
    ticket_id: Optional[int] = None
    type: Optional[str] = None
    status: Optional[str] = None
    issue_date: Optional[date] = None
    due_date: Optional[date] = None
    vat_rate: Optional[Decimal] = None
    notes: Optional[str] = None
    items: Optional[List[InvoiceItemCreate]] = None


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    client_id: int
    ticket_id: Optional[int]
    type: str
    status: str
    issue_date: date
    due_date: Optional[date]
    subtotal: Decimal
    vat_rate: Decimal
    vat_amount: Decimal
    total_amount: Decimal
    notes: Optional[str]
    created_by: int
    paid_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    items: List[InvoiceItemResponse]
    is_paid: bool = False

    @model_validator(mode="after")
    def compute_is_paid(self) -> "InvoiceResponse":
        self.is_paid = self.status == "paid"
        return self


# ── Notifications ─────────────────────────────────────────────────────────────

class NotificationSettingUpdate(BaseModel):
    event_type: str
    channel: str
    enabled: bool


class NotificationSettingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    event_type: str
    channel: str
    enabled: bool


class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    event_type: str
    title: str
    body: Optional[str]
    ticket_id: Optional[int]
    is_read: bool
    created_at: datetime


# ── Service Catalog ───────────────────────────────────────────────────────────

class ServiceCatalogCreate(BaseModel):
    code: str
    name: str
    description: Optional[str] = None
    category: str = "other"
    unit: str = "pcs"
    unit_price: Decimal = Decimal("0")
    currency: str = "RUB"
    is_active: bool = True


class ServiceCatalogUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    currency: Optional[str] = None
    is_active: Optional[bool] = None


class ServiceCatalogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    description: Optional[str]
    category: str
    unit: str
    unit_price: Decimal
    currency: str
    is_active: bool
    created_at: datetime
    updated_at: datetime





# ===== SystemSettings =====

class CurrencySettingResponse(BaseModel):
    currency_code: str
    currency_name: str


class CurrencySettingUpdate(BaseModel):
    currency_code: str
    currency_name: str

    @field_validator("currency_code")
    @classmethod
    def validate_code(cls, v: str) -> str:
        v = v.strip().upper()
        if len(v) != 3 or not v.isalpha():
            raise ValueError("Код валюты должен содержать ровно 3 латинских символа (например: RUB, KZT, PLN)")
        return v

    @field_validator("currency_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Введите наименование валюты")
        return v.strip()


# ===== Exchange Rates =====

class ExchangeRateCreate(BaseModel):
    currency: str
    rate: Decimal
    set_at: Optional[datetime] = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        if not v.isupper() or not v.isalpha() or len(v) != 3:
            raise ValueError("Код валюты должен содержать ровно 3 заглавных латинских символа (например: USD, EUR)")
        return v

    @field_validator("rate")
    @classmethod
    def validate_rate(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Курс должен быть положительным числом")
        return v


class ExchangeRateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    currency: str
    rate: Decimal
    set_by: int
    set_at: datetime


class ExchangeRateHistoryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    currency: str
    rate: Decimal
    set_by: int
    set_by_name: str
    set_at: datetime
    created_at: datetime


# ── Audit Log ─────────────────────────────────────────────────────────────────

class AuditUserBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    full_name: str


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: Optional[int]
    user: Optional[AuditUserBrief]
    action: str
    entity_type: str
    entity_id: Optional[int]
    old_values: Optional[dict]
    new_values: Optional[dict]
    ip_address: Optional[str]
    created_at: datetime


# ── Reports ───────────────────────────────────────────────────────────────────

class TicketReportResponse(BaseModel):
    total: int
    by_status: dict[str, int]
    by_type: dict[str, int]
    by_priority: dict[str, int]
    by_engineer: dict[str, int]
    sla_reaction_compliance_pct: Optional[float] = None
    sla_resolution_compliance_pct: Optional[float] = None
    sla_compliance_pct: Optional[float] = None
    avg_resolution_hours: Optional[float] = None
    period_from: date
    period_to: date


# ── Maintenance Schedule ──────────────────────────────────────────────────────

class MaintenanceScheduleCreate(BaseModel):
    frequency: str = Field(..., pattern="^(monthly|quarterly|semiannual|annual)$")
    first_date: date


class MaintenanceScheduleUpdate(BaseModel):
    frequency: Optional[str] = Field(None, pattern="^(monthly|quarterly|semiannual|annual)$")
    first_date: Optional[date] = None
    next_date: Optional[date] = None
    is_active: Optional[bool] = None


class MaintenanceScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: int
    frequency: str
    first_date: date
    next_date: date
    last_ticket_id: Optional[int]
    is_active: bool
    created_by: Optional[int]
    created_at: datetime
    updated_at: datetime


# ── Warehouse ─────────────────────────────────────────────────────────────────

class WarehouseCreate(BaseModel):
    name: str
    type: str = "company"
    client_id: Optional[int] = None
    is_active: bool = True


class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    client_id: Optional[int] = None
    is_active: Optional[bool] = None


class WarehouseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    client_id: Optional[int]
    is_active: bool


class WarehouseStockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    warehouse_id: int
    warehouse_name: str = ""
    warehouse_type: str = ""
    part_id: int
    part_sku: str = ""
    part_name: str = ""
    part_unit: str = ""
    part_category: Optional[str] = None
    part_min_quantity: int = 0
    quantity: int
    unit_price_snapshot: Optional[Decimal]

    @model_validator(mode="after")
    def _fill_from_relations(self) -> "WarehouseStockResponse":
        from app.models import WarehouseStock  # noqa: F401 — type-only use
        obj = self
        # filled from ORM relationships via model_validate
        return obj


# ── Stock Receipt ─────────────────────────────────────────────────────────────

class StockReceiptItemCreate(BaseModel):
    part_id: int
    quantity: int = Field(..., ge=1)
    unit_price: Decimal = Decimal("0")


class StockReceiptItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    part_id: int
    part_name: str = ""
    part_sku: str = ""
    quantity: int
    unit_price: Decimal


class StockReceiptCreate(BaseModel):
    warehouse_id: int
    receipt_date: date
    vendor_id: Optional[int] = None
    supplier_doc_number: Optional[str] = None
    notes: Optional[str] = None
    items: List[StockReceiptItemCreate] = []


class StockReceiptUpdate(BaseModel):
    warehouse_id: Optional[int] = None
    receipt_date: Optional[date] = None
    vendor_id: Optional[int] = None
    supplier_doc_number: Optional[str] = None
    notes: Optional[str] = None
    items: Optional[List[StockReceiptItemCreate]] = None


class StockReceiptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    receipt_number: str
    warehouse_id: int
    warehouse_name: str = ""
    receipt_date: date
    vendor_id: Optional[int]
    supplier_doc_number: Optional[str]
    notes: Optional[str]
    status: str
    created_by: int
    created_at: datetime
    items: List[StockReceiptItemResponse] = []


# ── Parts Transfer ────────────────────────────────────────────────────────────

class PartsTransferItemCreate(BaseModel):
    part_id: int
    quantity: int = Field(..., ge=1)


class PartsTransferItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    part_id: int
    part_name: str = ""
    part_sku: str = ""
    quantity: int
    unit_price_snapshot: Optional[Decimal]
    available_qty: int = 0


class PartsTransferCreate(BaseModel):
    from_warehouse_id: int
    to_warehouse_id: int
    transfer_date: date
    notes: Optional[str] = None
    items: List[PartsTransferItemCreate] = []


class PartsTransferUpdate(BaseModel):
    from_warehouse_id: Optional[int] = None
    to_warehouse_id: Optional[int] = None
    transfer_date: Optional[date] = None
    notes: Optional[str] = None
    items: Optional[List[PartsTransferItemCreate]] = None


class PartsTransferResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transfer_number: str
    from_warehouse_id: int
    from_warehouse_name: str = ""
    to_warehouse_id: int
    to_warehouse_name: str = ""
    transfer_date: date
    notes: Optional[str]
    status: str
    created_by: int
    posted_by: Optional[int]
    posted_at: Optional[datetime]
    created_at: datetime
    items: List[PartsTransferItemResponse] = []
