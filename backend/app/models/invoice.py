from sqlalchemy import Column, Integer, String, DateTime, Date, Text, ForeignKey, Enum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Invoice(Base):
    __tablename__ = "invoices"

    id           = Column(Integer, primary_key=True, index=True)
    number       = Column(String(32), unique=True, nullable=False)
    client_id    = Column(Integer, ForeignKey("clients.id"),          nullable=False)
    request_id   = Column(Integer, ForeignKey("service_requests.id"), nullable=True)
    type         = Column(Enum("service","sale","parts"), nullable=False, default="service")
    status       = Column(Enum("draft","sent","paid","cancelled"),    nullable=False, default="draft")
    issue_date   = Column(Date, nullable=False)
    due_date     = Column(Date)
    total_amount = Column(Numeric(14, 2), nullable=False, default=0)
    vat_rate     = Column(Numeric(5, 2),  nullable=False, default=20.00)
    vat_amount   = Column(Numeric(14, 2), nullable=False, default=0)
    notes        = Column(Text)
    created_by   = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at   = Column(DateTime, server_default=func.now())
    updated_at   = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client  = relationship("Client", back_populates="invoices")
    request = relationship("ServiceRequest")
    creator = relationship("User")
    items   = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")

class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id          = Column(Integer, primary_key=True, index=True)
    invoice_id  = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False)
    description = Column(String(512), nullable=False)
    quantity    = Column(Numeric(10, 3), nullable=False, default=1)
    unit        = Column(String(16), nullable=False, default="шт")
    unit_price  = Column(Numeric(12, 2), nullable=False)
    total       = Column(Numeric(14, 2), nullable=False)

    invoice = relationship("Invoice", back_populates="items")
