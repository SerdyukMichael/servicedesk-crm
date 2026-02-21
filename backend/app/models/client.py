from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Client(Base):
    __tablename__ = "clients"

    id             = Column(Integer, primary_key=True, index=True)
    company_name   = Column(String(255), nullable=False)
    inn            = Column(String(12),  unique=True)
    kpp            = Column(String(9))
    legal_address  = Column(Text)
    actual_address = Column(Text)
    contact_name   = Column(String(128))
    contact_phone  = Column(String(32))
    contact_email  = Column(String(128))
    manager_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    notes          = Column(Text)
    is_active      = Column(Boolean, default=True)
    created_at     = Column(DateTime, server_default=func.now())
    updated_at     = Column(DateTime, server_default=func.now(), onupdate=func.now())

    manager        = relationship("User", back_populates="clients", foreign_keys=[manager_id])
    interactions   = relationship("Interaction", back_populates="client")
    equipment      = relationship("ClientEquipment", back_populates="client")
    invoices       = relationship("Invoice", back_populates="client")
