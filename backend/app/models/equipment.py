from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey, Enum, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class EquipmentCatalog(Base):
    __tablename__ = "equipment_catalog"

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String(255), nullable=False)
    model          = Column(String(128))
    category       = Column(Enum("atm","card_printer","other"), nullable=False, default="other")
    vendor_id      = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    purchase_price = Column(Numeric(12, 2))
    sale_price     = Column(Numeric(12, 2))
    description    = Column(Text)
    created_at     = Column(DateTime, server_default=func.now())

    vendor   = relationship("Vendor")
    units    = relationship("ClientEquipment", back_populates="catalog")

class ClientEquipment(Base):
    __tablename__ = "client_equipment"

    id             = Column(Integer, primary_key=True, index=True)
    client_id      = Column(Integer, ForeignKey("clients.id"), nullable=False)
    catalog_id     = Column(Integer, ForeignKey("equipment_catalog.id"), nullable=False)
    serial_number  = Column(String(64), unique=True, nullable=False)
    install_date   = Column(Date)
    address        = Column(Text)
    status         = Column(Enum("active","in_repair","decommissioned"), nullable=False, default="active")
    warranty_until = Column(Date)
    notes          = Column(Text)
    created_at     = Column(DateTime, server_default=func.now())
    updated_at     = Column(DateTime, server_default=func.now(), onupdate=func.now())

    client         = relationship("Client", back_populates="equipment")
    catalog        = relationship("EquipmentCatalog", back_populates="units")
    service_requests = relationship("ServiceRequest", back_populates="equipment")
