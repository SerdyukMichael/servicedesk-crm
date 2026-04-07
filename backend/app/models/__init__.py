"""
SQLAlchemy 2.0 ORM models — 20-table schema for ServiceDesk CRM.
All models are imported here so that Base.metadata is fully populated
when alembic or the app imports `app.models`.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Any

from sqlalchemy import (
    Integer, String, Text, Boolean, DateTime, Date,
    Enum, DECIMAL, ForeignKey, JSON, LargeBinary, func, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# ── Users ─────────────────────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id:               Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    email:            Mapped[str]            = mapped_column(String(128), unique=True, nullable=False, index=True)
    full_name:        Mapped[str]            = mapped_column(String(128), nullable=False)
    password_hash:    Mapped[str]            = mapped_column(String(255), nullable=False)
    roles:            Mapped[Any]            = mapped_column(JSON, nullable=False, default=lambda: ["engineer"])
    phone:            Mapped[Optional[str]]  = mapped_column(String(32))
    telegram_chat_id: Mapped[Optional[str]]  = mapped_column(String(64))
    is_active:        Mapped[bool]           = mapped_column(Boolean, default=True, nullable=False)
    is_deleted:       Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    client_id:        Mapped[Optional[int]]  = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    last_login_at:    Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at:       Mapped[datetime]       = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at:       Mapped[datetime]       = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # relationships
    managed_clients:        Mapped[List["Client"]]          = relationship("Client", foreign_keys="Client.manager_id", back_populates="manager")
    assigned_tickets:       Mapped[List["Ticket"]]          = relationship("Ticket", foreign_keys="Ticket.assigned_to", back_populates="assignee")
    created_tickets:        Mapped[List["Ticket"]]          = relationship("Ticket", foreign_keys="Ticket.created_by", back_populates="creator")
    ticket_comments:        Mapped[List["TicketComment"]]   = relationship("TicketComment", back_populates="user")
    ticket_files:           Mapped[List["TicketFile"]]      = relationship("TicketFile", foreign_keys="TicketFile.uploaded_by", back_populates="uploader")
    work_acts_engineer:     Mapped[List["WorkAct"]]         = relationship("WorkAct", foreign_keys="WorkAct.engineer_id", back_populates="engineer")
    work_acts_signed:       Mapped[List["WorkAct"]]         = relationship("WorkAct", foreign_keys="WorkAct.signed_by", back_populates="signer")
    created_work_templates: Mapped[List["WorkTemplate"]]    = relationship("WorkTemplate", foreign_keys="WorkTemplate.created_by", back_populates="creator")
    created_invoices:       Mapped[List["Invoice"]]         = relationship("Invoice", foreign_keys="Invoice.created_by", back_populates="creator")
    repair_history:         Mapped[List["RepairHistory"]]   = relationship("RepairHistory", back_populates="performer")
    notification_settings:  Mapped[List["NotificationSetting"]] = relationship("NotificationSetting", back_populates="user", cascade="all, delete-orphan")
    notifications:          Mapped[List["Notification"]]   = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    audit_logs:             Mapped[List["AuditLog"]]        = relationship("AuditLog", back_populates="user")


# ── Clients ───────────────────────────────────────────────────────────────────
class Client(Base):
    __tablename__ = "clients"

    id:                   Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:                 Mapped[str]            = mapped_column(String(255), nullable=False, index=True)
    inn:                  Mapped[Optional[str]]  = mapped_column(String(12))
    kpp:                  Mapped[Optional[str]]  = mapped_column(String(9))
    legal_address:        Mapped[Optional[str]]  = mapped_column(Text)
    contract_type:        Mapped[str]            = mapped_column(String(64), default="none", nullable=False)
    contract_number:      Mapped[Optional[str]]  = mapped_column(String(64))
    contract_start:       Mapped[Optional[date]] = mapped_column(Date)
    contract_valid_until: Mapped[Optional[date]] = mapped_column(Date)
    address:              Mapped[Optional[str]]  = mapped_column(Text)
    city:                 Mapped[Optional[str]]  = mapped_column(String(128))
    manager_id:           Mapped[Optional[int]]  = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    is_deleted:           Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    created_at:           Mapped[datetime]       = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at:           Mapped[datetime]       = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    manager:   Mapped[Optional["User"]]          = relationship("User", foreign_keys=[manager_id], back_populates="managed_clients")
    contacts:  Mapped[List["ClientContact"]]     = relationship("ClientContact", back_populates="client", cascade="all, delete-orphan")
    equipment: Mapped[List["Equipment"]]         = relationship("Equipment", back_populates="client")
    tickets:   Mapped[List["Ticket"]]            = relationship("Ticket", back_populates="client")
    invoices:  Mapped[List["Invoice"]]           = relationship("Invoice", back_populates="client")


# ── Client Contacts ───────────────────────────────────────────────────────────
class ClientContact(Base):
    __tablename__ = "client_contacts"

    id:            Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id:     Mapped[int]           = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    name:          Mapped[str]           = mapped_column(String(128), nullable=False)
    phone:         Mapped[Optional[str]] = mapped_column(String(32))
    email:         Mapped[Optional[str]] = mapped_column(String(128))
    position:      Mapped[Optional[str]] = mapped_column(String(128))
    is_primary:    Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    is_active:     Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)
    portal_access: Mapped[bool]          = mapped_column(Boolean, default=False, nullable=False)
    portal_role:   Mapped[Optional[str]] = mapped_column(
        Enum("client_user", "client_admin", name="contact_portal_role_enum"),
        nullable=True,
    )
    portal_user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_by:    Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at:    Mapped[datetime]      = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at:    Mapped[datetime]      = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    client:      Mapped["Client"]        = relationship("Client", back_populates="contacts")
    portal_user: Mapped[Optional["User"]] = relationship("User", foreign_keys=[portal_user_id])
    creator:     Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by])


# ── Equipment Models ──────────────────────────────────────────────────────────
class EquipmentModel(Base):
    __tablename__ = "equipment_models"

    id:           Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:         Mapped[str]           = mapped_column(String(255), nullable=False)
    manufacturer: Mapped[Optional[str]] = mapped_column(String(128))
    category:     Mapped[str]           = mapped_column(
        Enum("atm", "card_printer", "pos_terminal", "other", name="equipment_category_enum"),
        default="other", nullable=False
    )
    description:              Mapped[Optional[str]] = mapped_column(Text)
    warranty_months_default:  Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active:                Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)

    equipment:       Mapped[List["Equipment"]]     = relationship("Equipment", back_populates="model")
    work_templates:  Mapped[List["WorkTemplate"]]  = relationship("WorkTemplate", back_populates="equipment_model")


# ── Equipment ─────────────────────────────────────────────────────────────────
class Equipment(Base):
    __tablename__ = "equipment"

    id:               Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id:        Mapped[int]            = mapped_column(ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    model_id:         Mapped[int]            = mapped_column(ForeignKey("equipment_models.id", ondelete="RESTRICT"), nullable=False)
    serial_number:    Mapped[str]            = mapped_column(String(128), unique=True, nullable=False)
    location:         Mapped[Optional[str]]  = mapped_column(Text)
    status:           Mapped[str]            = mapped_column(
        Enum("active", "in_repair", "decommissioned", "written_off", "transferred",
             name="equipment_status_enum"),
        default="active", nullable=False
    )
    installed_at:     Mapped[Optional[date]] = mapped_column(Date)
    warranty_until:   Mapped[Optional[date]] = mapped_column(Date)
    manufacture_date: Mapped[Optional[date]] = mapped_column(Date)
    sale_date:        Mapped[Optional[date]] = mapped_column(Date)
    warranty_start:   Mapped[Optional[date]] = mapped_column(Date)
    firmware_version: Mapped[Optional[str]]  = mapped_column(String(64))
    notes:            Mapped[Optional[str]]  = mapped_column(Text)
    is_deleted:       Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    created_at:       Mapped[datetime]       = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at:       Mapped[datetime]       = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    client:         Mapped["Client"]            = relationship("Client", back_populates="equipment")
    model:          Mapped["EquipmentModel"]    = relationship("EquipmentModel", back_populates="equipment")
    tickets:        Mapped[List["Ticket"]]      = relationship("Ticket", back_populates="equipment")
    repair_history: Mapped[List["RepairHistory"]] = relationship("RepairHistory", back_populates="equipment")


# ── Work Templates ────────────────────────────────────────────────────────────
class WorkTemplate(Base):
    __tablename__ = "work_templates"

    id:                 Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:               Mapped[str]           = mapped_column(String(255), nullable=False)
    equipment_model_id: Mapped[Optional[int]] = mapped_column(ForeignKey("equipment_models.id", ondelete="SET NULL"))
    description:        Mapped[Optional[str]] = mapped_column(Text)
    is_active:          Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)
    created_by:         Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_at:         Mapped[datetime]      = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at:         Mapped[datetime]      = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    equipment_model: Mapped[Optional["EquipmentModel"]] = relationship("EquipmentModel", back_populates="work_templates")
    creator:         Mapped[Optional["User"]]           = relationship("User", foreign_keys=[created_by], back_populates="created_work_templates")
    steps:           Mapped[List["WorkTemplateStep"]]   = relationship("WorkTemplateStep", back_populates="template", cascade="all, delete-orphan", order_by="WorkTemplateStep.step_order")
    tickets:         Mapped[List["Ticket"]]             = relationship("Ticket", back_populates="work_template")


# ── Work Template Steps ───────────────────────────────────────────────────────
class WorkTemplateStep(Base):
    __tablename__ = "work_template_steps"

    id:                 Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    template_id:        Mapped[int]           = mapped_column(ForeignKey("work_templates.id", ondelete="CASCADE"), nullable=False)
    step_order:         Mapped[int]           = mapped_column(Integer, nullable=False)
    description:        Mapped[str]           = mapped_column(Text, nullable=False)
    estimated_minutes:  Mapped[Optional[int]] = mapped_column(Integer)

    template: Mapped["WorkTemplate"] = relationship("WorkTemplate", back_populates="steps")


# ── Tickets ───────────────────────────────────────────────────────────────────
class Ticket(Base):
    __tablename__ = "tickets"

    id:               Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    number:           Mapped[str]            = mapped_column(String(32), unique=True, nullable=False, index=True)
    client_id:        Mapped[int]            = mapped_column(ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    equipment_id:     Mapped[Optional[int]]  = mapped_column(ForeignKey("equipment.id", ondelete="SET NULL"))
    assigned_to:      Mapped[Optional[int]]  = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created_by:       Mapped[int]            = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    title:            Mapped[str]            = mapped_column(String(255), nullable=False)
    description:      Mapped[Optional[str]]  = mapped_column(Text)
    type:             Mapped[str]            = mapped_column(
        Enum("repair", "maintenance", "diagnostics", "installation", name="ticket_type_enum"),
        default="repair", nullable=False
    )
    priority:         Mapped[str]            = mapped_column(
        Enum("low", "medium", "high", "critical", name="ticket_priority_enum"),
        default="medium", nullable=False
    )
    status:           Mapped[str]            = mapped_column(
        Enum("new", "assigned", "in_progress", "waiting_part", "on_review", "completed", "closed", "cancelled",
             name="ticket_status_enum"),
        default="new", nullable=False
    )
    sla_deadline:     Mapped[Optional[datetime]] = mapped_column(DateTime)
    work_template_id: Mapped[Optional[int]]  = mapped_column(ForeignKey("work_templates.id", ondelete="SET NULL"))
    closed_at:        Mapped[Optional[datetime]] = mapped_column(DateTime)
    is_deleted:       Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    created_at:       Mapped[datetime]       = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at:       Mapped[datetime]       = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    client:        Mapped["Client"]              = relationship("Client", back_populates="tickets")
    equipment:     Mapped[Optional["Equipment"]] = relationship("Equipment", back_populates="tickets")
    assignee:      Mapped[Optional["User"]]      = relationship("User", foreign_keys=[assigned_to], back_populates="assigned_tickets")
    creator:       Mapped["User"]                = relationship("User", foreign_keys=[created_by], back_populates="created_tickets")
    work_template: Mapped[Optional["WorkTemplate"]] = relationship("WorkTemplate", back_populates="tickets")
    status_history: Mapped[List["TicketStatusHistory"]] = relationship("TicketStatusHistory", back_populates="ticket", cascade="all, delete-orphan", order_by="TicketStatusHistory.changed_at")
    comments:      Mapped[List["TicketComment"]] = relationship("TicketComment", back_populates="ticket", cascade="all, delete-orphan")
    files:         Mapped[List["TicketFile"]]    = relationship("TicketFile", back_populates="ticket", cascade="all, delete-orphan")
    work_act:      Mapped[Optional["WorkAct"]]   = relationship("WorkAct", back_populates="ticket", uselist=False)
    repair_history: Mapped[List["RepairHistory"]] = relationship("RepairHistory", back_populates="ticket")
    notifications: Mapped[List["Notification"]]  = relationship("Notification", back_populates="ticket")


# ── Ticket Status History ─────────────────────────────────────────────────────
class TicketStatusHistory(Base):
    __tablename__ = "ticket_status_history"

    id:          Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id:   Mapped[int]            = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status: Mapped[Optional[str]]  = mapped_column(String(32))
    to_status:   Mapped[str]            = mapped_column(String(32), nullable=False)
    changed_by:  Mapped[Optional[int]]  = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    comment:     Mapped[Optional[str]]  = mapped_column(Text)
    changed_at:  Mapped[datetime]       = mapped_column(DateTime, default=func.now(), nullable=False)

    ticket:  Mapped["Ticket"]          = relationship("Ticket", back_populates="status_history")
    changer: Mapped[Optional["User"]]  = relationship("User")


# ── Ticket Comments ───────────────────────────────────────────────────────────
class TicketComment(Base):
    __tablename__ = "ticket_comments"

    id:          Mapped[int]  = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id:   Mapped[int]  = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    user_id:     Mapped[int]  = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    text:        Mapped[str]  = mapped_column(Text, nullable=False)
    is_internal: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at:  Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    ticket: Mapped["Ticket"] = relationship("Ticket", back_populates="comments")
    user:   Mapped["User"]   = relationship("User", back_populates="ticket_comments")


# ── Ticket Files ──────────────────────────────────────────────────────────────
class TicketFile(Base):
    __tablename__ = "ticket_files"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id:   Mapped[int]           = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False)
    uploaded_by: Mapped[int]           = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    file_name:   Mapped[str]           = mapped_column(String(255), nullable=False)
    file_type:   Mapped[Optional[str]] = mapped_column(String(128))
    file_size:   Mapped[Optional[int]] = mapped_column(Integer)
    file_data:   Mapped[Optional[bytes]] = mapped_column(LargeBinary(length=4294967295))
    created_at:  Mapped[datetime]      = mapped_column(DateTime, default=func.now(), nullable=False)

    ticket:   Mapped["Ticket"] = relationship("Ticket", back_populates="files")
    uploader: Mapped["User"]   = relationship("User", foreign_keys=[uploaded_by], back_populates="ticket_files")


# ── Work Acts ─────────────────────────────────────────────────────────────────
class WorkAct(Base):
    __tablename__ = "work_acts"

    id:                  Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id:           Mapped[int]            = mapped_column(ForeignKey("tickets.id", ondelete="RESTRICT"), unique=True, nullable=False)
    engineer_id:         Mapped[int]            = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    work_description:    Mapped[Optional[str]]  = mapped_column(Text)
    parts_used:          Mapped[Optional[Any]]  = mapped_column(JSON)
    total_time_minutes:  Mapped[Optional[int]]  = mapped_column(Integer)
    signed_by:           Mapped[Optional[int]]  = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    signed_at:           Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at:          Mapped[datetime]       = mapped_column(DateTime, default=func.now(), nullable=False)

    ticket:   Mapped["Ticket"]          = relationship("Ticket", back_populates="work_act")
    engineer: Mapped["User"]            = relationship("User", foreign_keys=[engineer_id], back_populates="work_acts_engineer")
    signer:   Mapped[Optional["User"]]  = relationship("User", foreign_keys=[signed_by], back_populates="work_acts_signed")
    items:    Mapped[List["WorkActItem"]] = relationship("WorkActItem", back_populates="work_act", cascade="all, delete-orphan", order_by="WorkActItem.sort_order")


# ── Service Catalog ───────────────────────────────────────────────────────────
class ServiceCatalog(Base):
    __tablename__ = "service_catalog"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    code:        Mapped[str]           = mapped_column(String(32), unique=True, nullable=False, index=True)
    name:        Mapped[str]           = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category:    Mapped[str]           = mapped_column(
        Enum("repair", "maintenance", "diagnostics", "visit", "other",
             name="service_category_enum"),
        default="other", nullable=False
    )
    unit:        Mapped[str]           = mapped_column(
        Enum("pcs", "hour", "visit", "kit", name="service_unit_enum"),
        default="pcs", nullable=False
    )
    unit_price:  Mapped[Decimal]       = mapped_column(DECIMAL(12, 2), nullable=False, default=0)
    currency:    Mapped[str]           = mapped_column(String(3), default="RUB", nullable=False)
    is_active:   Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)
    created_at:  Mapped[datetime]      = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at:  Mapped[datetime]      = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    work_act_items: Mapped[List["WorkActItem"]] = relationship("WorkActItem", back_populates="service")


# ── Work Act Items ────────────────────────────────────────────────────────────
class WorkActItem(Base):
    __tablename__ = "work_act_items"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    work_act_id: Mapped[int]           = mapped_column(ForeignKey("work_acts.id", ondelete="CASCADE"), nullable=False)
    item_type:   Mapped[str]           = mapped_column(
        Enum("service", "part", name="work_act_item_type_enum"),
        nullable=False
    )
    service_id:  Mapped[Optional[int]] = mapped_column(ForeignKey("service_catalog.id", ondelete="RESTRICT"), nullable=True)
    part_id:     Mapped[Optional[int]] = mapped_column(ForeignKey("spare_parts.id", ondelete="RESTRICT"), nullable=True)
    name:        Mapped[str]           = mapped_column(String(255), nullable=False)
    quantity:    Mapped[Decimal]       = mapped_column(DECIMAL(10, 3), nullable=False, default=1)
    unit:        Mapped[str]           = mapped_column(String(16), nullable=False, default="шт")
    unit_price:  Mapped[Decimal]       = mapped_column(DECIMAL(12, 2), nullable=False, default=0)
    total:       Mapped[Decimal]       = mapped_column(DECIMAL(14, 2), nullable=False, default=0)
    sort_order:  Mapped[int]           = mapped_column(Integer, default=0, nullable=False)

    work_act: Mapped["WorkAct"]                  = relationship("WorkAct", back_populates="items")
    service:  Mapped[Optional["ServiceCatalog"]] = relationship("ServiceCatalog", back_populates="work_act_items")
    part:     Mapped[Optional["SparePart"]]      = relationship("SparePart")


# ── Vendors ───────────────────────────────────────────────────────────────────
class Vendor(Base):
    __tablename__ = "vendors"

    id:            Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:          Mapped[str]           = mapped_column(String(255), nullable=False)
    inn:           Mapped[Optional[str]] = mapped_column(String(12))
    contact_name:  Mapped[Optional[str]] = mapped_column(String(128))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(32))
    contact_email: Mapped[Optional[str]] = mapped_column(String(128))
    website:       Mapped[Optional[str]] = mapped_column(String(255))
    notes:         Mapped[Optional[str]] = mapped_column(Text)
    is_active:     Mapped[bool]          = mapped_column(Boolean, default=True, nullable=False)

    spare_parts: Mapped[List["SparePart"]] = relationship("SparePart", back_populates="vendor")


# ── Spare Parts ───────────────────────────────────────────────────────────────
class SparePart(Base):
    __tablename__ = "spare_parts"

    id:           Mapped[int]             = mapped_column(Integer, primary_key=True, autoincrement=True)
    sku:          Mapped[str]             = mapped_column(String(64), unique=True, nullable=False, index=True)
    name:         Mapped[str]             = mapped_column(String(255), nullable=False)
    category:     Mapped[Optional[str]]   = mapped_column(String(64))
    unit:         Mapped[str]             = mapped_column(String(16), default="шт", nullable=False)
    quantity:     Mapped[int]             = mapped_column(Integer, default=0, nullable=False)
    min_quantity: Mapped[int]             = mapped_column(Integer, default=0, nullable=False)
    unit_price:   Mapped[Decimal]         = mapped_column(DECIMAL(12, 2), nullable=False, default=0)
    currency:     Mapped[str]             = mapped_column(String(3), default="RUB", nullable=False)
    vendor_id:    Mapped[Optional[int]]   = mapped_column(ForeignKey("vendors.id", ondelete="SET NULL"))
    description:  Mapped[Optional[str]]   = mapped_column(Text)
    is_active:    Mapped[bool]            = mapped_column(Boolean, default=True, nullable=False)

    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor", back_populates="spare_parts")


# ── Invoices ──────────────────────────────────────────────────────────────────
class Invoice(Base):
    __tablename__ = "invoices"

    id:           Mapped[int]             = mapped_column(Integer, primary_key=True, autoincrement=True)
    number:       Mapped[str]             = mapped_column(String(32), unique=True, nullable=False, index=True)
    client_id:    Mapped[int]             = mapped_column(ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False)
    ticket_id:    Mapped[Optional[int]]   = mapped_column(ForeignKey("tickets.id", ondelete="SET NULL"))
    type:         Mapped[str]             = mapped_column(
        Enum("service", "parts", "mixed", name="invoice_type_enum"),
        default="service", nullable=False
    )
    status:       Mapped[str]             = mapped_column(
        Enum("draft", "sent", "paid", "cancelled", "overdue", name="invoice_status_enum"),
        default="draft", nullable=False
    )
    issue_date:   Mapped[date]            = mapped_column(Date, nullable=False)
    due_date:     Mapped[Optional[date]]  = mapped_column(Date)
    subtotal:     Mapped[Decimal]         = mapped_column(DECIMAL(14, 2), default=0, nullable=False)
    vat_rate:     Mapped[Decimal]         = mapped_column(DECIMAL(5, 2), default=20.00, nullable=False)
    vat_amount:   Mapped[Decimal]         = mapped_column(DECIMAL(14, 2), default=0, nullable=False)
    total_amount: Mapped[Decimal]         = mapped_column(DECIMAL(14, 2), default=0, nullable=False)
    notes:        Mapped[Optional[str]]   = mapped_column(Text)
    created_by:   Mapped[int]             = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    paid_at:      Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at:   Mapped[datetime]        = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at:   Mapped[datetime]        = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    client:  Mapped["Client"]            = relationship("Client", back_populates="invoices")
    creator: Mapped["User"]              = relationship("User", foreign_keys=[created_by], back_populates="created_invoices")
    items:   Mapped[List["InvoiceItem"]] = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


# ── Invoice Items ─────────────────────────────────────────────────────────────
class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id:  Mapped[int]           = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    description: Mapped[str]           = mapped_column(String(512), nullable=False)
    quantity:    Mapped[Decimal]       = mapped_column(DECIMAL(10, 3), default=1, nullable=False)
    unit:        Mapped[str]           = mapped_column(String(16), default="шт", nullable=False)
    unit_price:  Mapped[Decimal]       = mapped_column(DECIMAL(12, 2), nullable=False)
    total:       Mapped[Decimal]       = mapped_column(DECIMAL(14, 2), nullable=False)
    sort_order:  Mapped[int]           = mapped_column(Integer, default=0, nullable=False)
    item_type:   Mapped[Optional[str]] = mapped_column(
        Enum("service", "part", "manual", name="invoice_item_type_enum"),
        nullable=True
    )
    service_id:  Mapped[Optional[int]] = mapped_column(ForeignKey("service_catalog.id", ondelete="RESTRICT"), nullable=True)
    part_id:     Mapped[Optional[int]] = mapped_column(ForeignKey("spare_parts.id", ondelete="RESTRICT"), nullable=True)

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="items")


# ── Repair History ────────────────────────────────────────────────────────────
class RepairHistory(Base):
    __tablename__ = "repair_history"

    id:            Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id:     Mapped[Optional[int]]  = mapped_column(ForeignKey("tickets.id", ondelete="SET NULL"))
    equipment_id:  Mapped[int]            = mapped_column(ForeignKey("equipment.id", ondelete="RESTRICT"), nullable=False)
    action_type:   Mapped[str]            = mapped_column(String(64), nullable=False)
    description:   Mapped[Optional[str]]  = mapped_column(Text)
    performed_by:  Mapped[Optional[int]]  = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    performed_at:  Mapped[datetime]       = mapped_column(DateTime, default=func.now(), nullable=False)
    parts_used:    Mapped[Optional[Any]]  = mapped_column(JSON)

    ticket:    Mapped[Optional["Ticket"]]    = relationship("Ticket", back_populates="repair_history")
    equipment: Mapped["Equipment"]           = relationship("Equipment", back_populates="repair_history")
    performer: Mapped[Optional["User"]]      = relationship("User", back_populates="repair_history")


# ── Notification Settings ─────────────────────────────────────────────────────
class NotificationSetting(Base):
    __tablename__ = "notification_settings"

    id:         Mapped[int]  = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:    Mapped[int]  = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str]  = mapped_column(String(64), nullable=False)
    channel:    Mapped[str]  = mapped_column(
        Enum("email", "push", "in_app", name="notif_channel_enum"),
        nullable=False
    )
    enabled:    Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "event_type", "channel", name="uq_notif_setting"),
    )

    user: Mapped["User"] = relationship("User", back_populates="notification_settings")


# ── Notifications ─────────────────────────────────────────────────────────────
class Notification(Base):
    __tablename__ = "notifications"

    id:         Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:    Mapped[int]            = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[str]            = mapped_column(String(64), nullable=False)
    title:      Mapped[str]            = mapped_column(String(255), nullable=False)
    body:       Mapped[Optional[str]]  = mapped_column(Text)
    ticket_id:  Mapped[Optional[int]]  = mapped_column(ForeignKey("tickets.id", ondelete="SET NULL"))
    is_read:    Mapped[bool]           = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime]       = mapped_column(DateTime, default=func.now(), nullable=False)

    user:   Mapped["User"]             = relationship("User", back_populates="notifications")
    ticket: Mapped[Optional["Ticket"]] = relationship("Ticket", back_populates="notifications")


# ── Audit Log ─────────────────────────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_log"

    id:          Mapped[int]            = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id:     Mapped[Optional[int]]  = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    entity_type: Mapped[str]            = mapped_column(String(64), nullable=False)
    entity_id:   Mapped[Optional[int]]  = mapped_column(Integer)
    action:      Mapped[str]            = mapped_column(String(32), nullable=False)
    old_values:  Mapped[Optional[Any]]  = mapped_column(JSON)
    new_values:  Mapped[Optional[Any]]  = mapped_column(JSON)
    ip_address:  Mapped[Optional[str]]  = mapped_column(String(45))
    created_at:  Mapped[datetime]       = mapped_column(DateTime, default=func.now(), nullable=False)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")


__all__ = [
    "User",
    "Client",
    "ClientContact",
    "EquipmentModel",
    "Equipment",
    "WorkTemplate",
    "WorkTemplateStep",
    "Ticket",
    "TicketStatusHistory",
    "TicketComment",
    "TicketFile",
    "WorkAct",
    "ServiceCatalog",
    "WorkActItem",
    "Vendor",
    "SparePart",
    "Invoice",
    "InvoiceItem",
    "RepairHistory",
    "NotificationSetting",
    "Notification",
    "AuditLog",
]
