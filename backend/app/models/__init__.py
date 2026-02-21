from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from sqlalchemy import (
    Integer, String, Text, Boolean, DateTime, Date,
    Enum, DECIMAL, ForeignKey, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


# ── Users ────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id:            Mapped[int]      = mapped_column(Integer, primary_key=True, autoincrement=True)
    username:      Mapped[str]      = mapped_column(String(64), unique=True, nullable=False)
    email:         Mapped[str]      = mapped_column(String(128), unique=True, nullable=False)
    password_hash: Mapped[str]      = mapped_column(String(255), nullable=False)
    full_name:     Mapped[str]      = mapped_column(String(128), nullable=False)
    role:          Mapped[str]      = mapped_column(Enum("admin","manager","engineer"), default="manager")
    is_active:     Mapped[bool]     = mapped_column(Boolean, default=True)
    created_at:    Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at:    Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    clients:       Mapped[List["Client"]]         = relationship("Client", back_populates="manager")
    interactions:  Mapped[List["Interaction"]]     = relationship("Interaction", back_populates="user")
    requests_created: Mapped[List["ServiceRequest"]] = relationship("ServiceRequest", foreign_keys="ServiceRequest.created_by", back_populates="creator")
    requests_assigned: Mapped[List["ServiceRequest"]] = relationship("ServiceRequest", foreign_keys="ServiceRequest.engineer_id", back_populates="engineer")


# ── Vendors ──────────────────────────────────────────────────
class Vendor(Base):
    __tablename__ = "vendors"

    id:            Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:          Mapped[str]           = mapped_column(String(255), nullable=False)
    country:       Mapped[Optional[str]] = mapped_column(String(64))
    inn:           Mapped[Optional[str]] = mapped_column(String(12))
    contact_name:  Mapped[Optional[str]] = mapped_column(String(128))
    contact_email: Mapped[Optional[str]] = mapped_column(String(128))
    contact_phone: Mapped[Optional[str]] = mapped_column(String(32))
    website:       Mapped[Optional[str]] = mapped_column(String(255))
    notes:         Mapped[Optional[str]] = mapped_column(Text)
    created_at:    Mapped[datetime]      = mapped_column(DateTime, default=func.now())

    equipment_catalog: Mapped[List["EquipmentCatalog"]] = relationship("EquipmentCatalog", back_populates="vendor")
    spare_parts:       Mapped[List["SparePart"]]        = relationship("SparePart", back_populates="vendor")
    purchase_orders:   Mapped[List["PurchaseOrder"]]    = relationship("PurchaseOrder", back_populates="vendor")


# ── Equipment Catalog ────────────────────────────────────────
class EquipmentCatalog(Base):
    __tablename__ = "equipment_catalog"

    id:             Mapped[int]                = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:           Mapped[str]                = mapped_column(String(255), nullable=False)
    model:          Mapped[Optional[str]]      = mapped_column(String(128))
    category:       Mapped[str]                = mapped_column(Enum("atm","card_printer","other"), default="other")
    vendor_id:      Mapped[Optional[int]]      = mapped_column(ForeignKey("vendors.id", ondelete="SET NULL"))
    purchase_price: Mapped[Optional[Decimal]]  = mapped_column(DECIMAL(12,2))
    sale_price:     Mapped[Optional[Decimal]]  = mapped_column(DECIMAL(12,2))
    description:    Mapped[Optional[str]]      = mapped_column(Text)
    is_active:      Mapped[bool]               = mapped_column(Boolean, default=True)
    created_at:     Mapped[datetime]           = mapped_column(DateTime, default=func.now())

    vendor:           Mapped[Optional["Vendor"]]       = relationship("Vendor", back_populates="equipment_catalog")
    client_equipment: Mapped[List["ClientEquipment"]]  = relationship("ClientEquipment", back_populates="catalog")
    spare_parts:      Mapped[List["SparePart"]]        = relationship("SparePart", back_populates="catalog")


# ── Clients ──────────────────────────────────────────────────
class Client(Base):
    __tablename__ = "clients"

    id:             Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_name:   Mapped[str]           = mapped_column(String(255), nullable=False, index=True)
    inn:            Mapped[Optional[str]] = mapped_column(String(12), unique=True)
    kpp:            Mapped[Optional[str]] = mapped_column(String(9))
    ogrn:           Mapped[Optional[str]] = mapped_column(String(15))
    legal_address:  Mapped[Optional[str]] = mapped_column(Text)
    actual_address: Mapped[Optional[str]] = mapped_column(Text)
    contact_name:   Mapped[Optional[str]] = mapped_column(String(128))
    contact_phone:  Mapped[Optional[str]] = mapped_column(String(32))
    contact_email:  Mapped[Optional[str]] = mapped_column(String(128))
    manager_id:     Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    status:         Mapped[str]           = mapped_column(Enum("active","inactive"), default="active")
    notes:          Mapped[Optional[str]] = mapped_column(Text)
    created_at:     Mapped[datetime]      = mapped_column(DateTime, default=func.now())
    updated_at:     Mapped[datetime]      = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    manager:        Mapped[Optional["User"]]           = relationship("User", back_populates="clients")
    interactions:   Mapped[List["Interaction"]]        = relationship("Interaction", back_populates="client", cascade="all, delete-orphan")
    equipment:      Mapped[List["ClientEquipment"]]    = relationship("ClientEquipment", back_populates="client")
    invoices:       Mapped[List["Invoice"]]            = relationship("Invoice", back_populates="client")
    service_requests: Mapped[List["ServiceRequest"]]   = relationship("ServiceRequest", back_populates="client")


# ── Interactions ─────────────────────────────────────────────
class Interaction(Base):
    __tablename__ = "interactions"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id:   Mapped[int]           = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"))
    user_id:     Mapped[int]           = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    type:        Mapped[str]           = mapped_column(Enum("call","email","meeting","other"), default="call")
    date:        Mapped[datetime]      = mapped_column(DateTime, nullable=False)
    subject:     Mapped[Optional[str]] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text)
    created_at:  Mapped[datetime]      = mapped_column(DateTime, default=func.now())

    client: Mapped["Client"] = relationship("Client", back_populates="interactions")
    user:   Mapped["User"]   = relationship("User",   back_populates="interactions")


# ── Client Equipment ─────────────────────────────────────────
class ClientEquipment(Base):
    __tablename__ = "client_equipment"

    id:             Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    client_id:      Mapped[int]           = mapped_column(ForeignKey("clients.id",           ondelete="RESTRICT"))
    catalog_id:     Mapped[int]           = mapped_column(ForeignKey("equipment_catalog.id", ondelete="RESTRICT"))
    serial_number:  Mapped[str]           = mapped_column(String(64), unique=True, nullable=False)
    install_date:   Mapped[Optional[datetime]] = mapped_column(Date)
    address:        Mapped[Optional[str]] = mapped_column(Text)
    status:         Mapped[str]           = mapped_column(Enum("active","in_repair","decommissioned"), default="active")
    warranty_until: Mapped[Optional[datetime]] = mapped_column(Date)
    notes:          Mapped[Optional[str]] = mapped_column(Text)
    created_at:     Mapped[datetime]      = mapped_column(DateTime, default=func.now())
    updated_at:     Mapped[datetime]      = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    client:   Mapped["Client"]           = relationship("Client",           back_populates="equipment")
    catalog:  Mapped["EquipmentCatalog"] = relationship("EquipmentCatalog", back_populates="client_equipment")
    requests: Mapped[List["ServiceRequest"]] = relationship("ServiceRequest", back_populates="equipment")


# ── Service Requests ─────────────────────────────────────────
class ServiceRequest(Base):
    __tablename__ = "service_requests"

    id:           Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    number:       Mapped[str]           = mapped_column(String(32), unique=True, nullable=False)
    client_id:    Mapped[int]           = mapped_column(ForeignKey("clients.id",          ondelete="RESTRICT"))
    equipment_id: Mapped[int]           = mapped_column(ForeignKey("client_equipment.id", ondelete="RESTRICT"))
    engineer_id:  Mapped[Optional[int]] = mapped_column(ForeignKey("users.id",            ondelete="SET NULL"))
    created_by:   Mapped[int]           = mapped_column(ForeignKey("users.id",            ondelete="RESTRICT"))
    type:         Mapped[str]           = mapped_column(Enum("repair","maintenance","installation","other"), default="repair")
    priority:     Mapped[str]           = mapped_column(Enum("low","normal","high","critical"), default="normal")
    status:       Mapped[str]           = mapped_column(Enum("new","assigned","in_progress","done","closed","cancelled"), default="new")
    description:  Mapped[str]           = mapped_column(Text, nullable=False)
    resolution:   Mapped[Optional[str]] = mapped_column(Text)
    created_at:   Mapped[datetime]      = mapped_column(DateTime, default=func.now())
    assigned_at:  Mapped[Optional[datetime]] = mapped_column(DateTime)
    started_at:   Mapped[Optional[datetime]] = mapped_column(DateTime)
    closed_at:    Mapped[Optional[datetime]] = mapped_column(DateTime)
    updated_at:   Mapped[datetime]      = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    client:    Mapped["Client"]          = relationship("Client",          back_populates="service_requests")
    equipment: Mapped["ClientEquipment"] = relationship("ClientEquipment", back_populates="requests")
    engineer:  Mapped[Optional["User"]]  = relationship("User", foreign_keys=[engineer_id], back_populates="requests_assigned")
    creator:   Mapped["User"]            = relationship("User", foreign_keys=[created_by],  back_populates="requests_created")
    parts_used: Mapped[List["PartsUsage"]] = relationship("PartsUsage", back_populates="request", cascade="all, delete-orphan")


# ── Spare Parts ──────────────────────────────────────────────
class SparePart(Base):
    __tablename__ = "spare_parts"

    id:           Mapped[int]                = mapped_column(Integer, primary_key=True, autoincrement=True)
    name:         Mapped[str]                = mapped_column(String(255), nullable=False)
    part_number:  Mapped[Optional[str]]      = mapped_column(String(64), index=True)
    catalog_id:   Mapped[Optional[int]]      = mapped_column(ForeignKey("equipment_catalog.id", ondelete="SET NULL"))
    vendor_id:    Mapped[Optional[int]]      = mapped_column(ForeignKey("vendors.id",           ondelete="SET NULL"))
    quantity:     Mapped[int]                = mapped_column(Integer, default=0)
    unit:         Mapped[str]                = mapped_column(String(16), default="шт")
    cost_price:   Mapped[Optional[Decimal]]  = mapped_column(DECIMAL(10,2))
    sale_price:   Mapped[Optional[Decimal]]  = mapped_column(DECIMAL(10,2))
    min_quantity: Mapped[int]                = mapped_column(Integer, default=0)
    location:     Mapped[Optional[str]]      = mapped_column(String(128))
    notes:        Mapped[Optional[str]]      = mapped_column(Text)
    created_at:   Mapped[datetime]           = mapped_column(DateTime, default=func.now())
    updated_at:   Mapped[datetime]           = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    catalog: Mapped[Optional["EquipmentCatalog"]] = relationship("EquipmentCatalog", back_populates="spare_parts")
    vendor:  Mapped[Optional["Vendor"]]           = relationship("Vendor",            back_populates="spare_parts")
    usages:  Mapped[List["PartsUsage"]]           = relationship("PartsUsage",         back_populates="part")


# ── Parts Usage ──────────────────────────────────────────────
class PartsUsage(Base):
    __tablename__ = "parts_usage"

    id:         Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[int]           = mapped_column(ForeignKey("service_requests.id", ondelete="CASCADE"))
    part_id:    Mapped[int]           = mapped_column(ForeignKey("spare_parts.id",      ondelete="RESTRICT"))
    quantity:   Mapped[int]           = mapped_column(Integer, nullable=False)
    unit_price: Mapped[Decimal]       = mapped_column(DECIMAL(10,2), nullable=False)
    used_by:    Mapped[int]           = mapped_column(ForeignKey("users.id",            ondelete="RESTRICT"))
    used_at:    Mapped[datetime]      = mapped_column(DateTime, default=func.now())
    notes:      Mapped[Optional[str]] = mapped_column(String(255))

    request: Mapped["ServiceRequest"] = relationship("ServiceRequest", back_populates="parts_used")
    part:    Mapped["SparePart"]      = relationship("SparePart",       back_populates="usages")


# ── Invoices ─────────────────────────────────────────────────
class Invoice(Base):
    __tablename__ = "invoices"

    id:           Mapped[int]                = mapped_column(Integer, primary_key=True, autoincrement=True)
    number:       Mapped[str]                = mapped_column(String(32), unique=True, nullable=False)
    client_id:    Mapped[int]                = mapped_column(ForeignKey("clients.id", ondelete="RESTRICT"))
    type:         Mapped[str]                = mapped_column(Enum("service","sale","parts","mixed"), default="service")
    status:       Mapped[str]                = mapped_column(Enum("draft","sent","paid","cancelled"), default="draft")
    issue_date:   Mapped[datetime]           = mapped_column(Date, nullable=False)
    due_date:     Mapped[Optional[datetime]] = mapped_column(Date)
    subtotal:     Mapped[Decimal]            = mapped_column(DECIMAL(14,2), default=0)
    vat_rate:     Mapped[Decimal]            = mapped_column(DECIMAL(5,2),  default=20)
    vat_amount:   Mapped[Decimal]            = mapped_column(DECIMAL(14,2), default=0)
    total_amount: Mapped[Decimal]            = mapped_column(DECIMAL(14,2), default=0)
    notes:        Mapped[Optional[str]]      = mapped_column(Text)
    created_by:   Mapped[int]                = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    paid_at:      Mapped[Optional[datetime]] = mapped_column(DateTime)
    created_at:   Mapped[datetime]           = mapped_column(DateTime, default=func.now())
    updated_at:   Mapped[datetime]           = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    client: Mapped["Client"]           = relationship("Client", back_populates="invoices")
    items:  Mapped[List["InvoiceItem"]] = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


# ── Invoice Items ────────────────────────────────────────────
class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id:          Mapped[int]     = mapped_column(Integer, primary_key=True, autoincrement=True)
    invoice_id:  Mapped[int]     = mapped_column(ForeignKey("invoices.id", ondelete="CASCADE"))
    description: Mapped[str]     = mapped_column(String(512), nullable=False)
    quantity:    Mapped[Decimal] = mapped_column(DECIMAL(10,3), default=1)
    unit:        Mapped[str]     = mapped_column(String(16), default="шт")
    unit_price:  Mapped[Decimal] = mapped_column(DECIMAL(12,2), nullable=False)
    total:       Mapped[Decimal] = mapped_column(DECIMAL(14,2), nullable=False)
    sort_order:  Mapped[int]     = mapped_column(Integer, default=0)

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="items")


# ── Purchase Orders ──────────────────────────────────────────
class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id:            Mapped[int]                = mapped_column(Integer, primary_key=True, autoincrement=True)
    number:        Mapped[str]                = mapped_column(String(32), unique=True, nullable=False)
    vendor_id:     Mapped[int]                = mapped_column(ForeignKey("vendors.id", ondelete="RESTRICT"))
    status:        Mapped[str]                = mapped_column(Enum("draft","sent","confirmed","received","cancelled"), default="draft")
    order_date:    Mapped[datetime]           = mapped_column(Date, nullable=False)
    expected_date: Mapped[Optional[datetime]] = mapped_column(Date)
    received_date: Mapped[Optional[datetime]] = mapped_column(Date)
    total_amount:  Mapped[Optional[Decimal]]  = mapped_column(DECIMAL(14,2))
    currency:      Mapped[str]                = mapped_column(String(3), default="RUB")
    notes:         Mapped[Optional[str]]      = mapped_column(Text)
    created_by:    Mapped[int]                = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    created_at:    Mapped[datetime]           = mapped_column(DateTime, default=func.now())
    updated_at:    Mapped[datetime]           = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    vendor: Mapped["Vendor"]                    = relationship("Vendor", back_populates="purchase_orders")
    items:  Mapped[List["PurchaseOrderItem"]]   = relationship("PurchaseOrderItem", back_populates="order", cascade="all, delete-orphan")


# ── Purchase Order Items ─────────────────────────────────────
class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id:          Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id:    Mapped[int]           = mapped_column(ForeignKey("purchase_orders.id",   ondelete="CASCADE"))
    item_type:   Mapped[str]           = mapped_column(Enum("equipment","part"),           default="part")
    catalog_id:  Mapped[Optional[int]] = mapped_column(ForeignKey("equipment_catalog.id", ondelete="SET NULL"))
    part_id:     Mapped[Optional[int]] = mapped_column(ForeignKey("spare_parts.id",       ondelete="SET NULL"))
    description: Mapped[str]           = mapped_column(String(512), nullable=False)
    quantity:    Mapped[int]           = mapped_column(Integer, nullable=False)
    unit_price:  Mapped[Decimal]       = mapped_column(DECIMAL(12,2), nullable=False)
    total:       Mapped[Decimal]       = mapped_column(DECIMAL(14,2), nullable=False)

    order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="items")
