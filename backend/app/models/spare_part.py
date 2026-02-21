from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Numeric, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class SparePart(Base):
    __tablename__ = "spare_parts"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(255), nullable=False)
    part_number  = Column(String(64))
    catalog_id   = Column(Integer, ForeignKey("equipment_catalog.id"), nullable=True)
    quantity     = Column(Integer, nullable=False, default=0)
    unit         = Column(String(16), nullable=False, default="шт")
    cost_price   = Column(Numeric(10, 2))
    sale_price   = Column(Numeric(10, 2))
    min_quantity = Column(Integer, nullable=False, default=0)
    created_at   = Column(DateTime, server_default=func.now())
    updated_at   = Column(DateTime, server_default=func.now(), onupdate=func.now())

    catalog    = relationship("EquipmentCatalog")
    movements  = relationship("StockMovement", back_populates="part")

class StockMovement(Base):
    __tablename__ = "stock_movements"

    id         = Column(Integer, primary_key=True, index=True)
    part_id    = Column(Integer, ForeignKey("spare_parts.id"),       nullable=False)
    type       = Column(Enum("in","out"), nullable=False)
    quantity   = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2))
    request_id = Column(Integer, ForeignKey("service_requests.id"),  nullable=True)
    notes      = Column(String(255))
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"),             nullable=False)

    part       = relationship("SparePart", back_populates="movements")
    request    = relationship("ServiceRequest", back_populates="movements")
    creator    = relationship("User")
