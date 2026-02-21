from sqlalchemy import Column, Integer, String, DateTime, Text, Date, ForeignKey, Enum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Vendor(Base):
    __tablename__ = "vendors"

    id            = Column(Integer, primary_key=True, index=True)
    name          = Column(String(255), nullable=False)
    country       = Column(String(64))
    contact_name  = Column(String(128))
    contact_email = Column(String(128))
    contact_phone = Column(String(32))
    website       = Column(String(255))
    notes         = Column(Text)
    created_at    = Column(DateTime, server_default=func.now())
    updated_at    = Column(DateTime, server_default=func.now(), onupdate=func.now())

    orders = relationship("PurchaseOrder", back_populates="vendor")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id            = Column(Integer, primary_key=True, index=True)
    number        = Column(String(32), unique=True, nullable=False)
    vendor_id     = Column(Integer, ForeignKey("vendors.id"), nullable=False)
    status        = Column(Enum("draft","sent","confirmed","received","cancelled"), nullable=False, default="draft")
    order_date    = Column(Date, nullable=False)
    expected_date = Column(Date)
    received_date = Column(Date)
    total_amount  = Column(Numeric(14, 2))
    currency      = Column(String(3), nullable=False, default="RUB")
    notes         = Column(Text)
    created_by    = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at    = Column(DateTime, server_default=func.now())
    updated_at    = Column(DateTime, server_default=func.now(), onupdate=func.now())

    vendor  = relationship("Vendor", back_populates="orders")
    creator = relationship("User")
    items   = relationship("PurchaseOrderItem", back_populates="order", cascade="all, delete-orphan")

class PurchaseOrderItem(Base):
    __tablename__ = "purchase_order_items"

    id          = Column(Integer, primary_key=True, index=True)
    order_id    = Column(Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False)
    part_id     = Column(Integer, ForeignKey("spare_parts.id"),        nullable=True)
    catalog_id  = Column(Integer, ForeignKey("equipment_catalog.id"),  nullable=True)
    description = Column(String(512), nullable=False)
    quantity    = Column(Integer, nullable=False)
    unit_price  = Column(Numeric(12, 2))
    total       = Column(Numeric(14, 2))

    order   = relationship("PurchaseOrder", back_populates="items")
    part    = relationship("SparePart")
    catalog = relationship("EquipmentCatalog")
