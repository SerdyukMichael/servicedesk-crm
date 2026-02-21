from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class ServiceRequest(Base):
    __tablename__ = "service_requests"

    id           = Column(Integer, primary_key=True, index=True)
    number       = Column(String(32), unique=True, nullable=False)
    client_id    = Column(Integer, ForeignKey("clients.id"),          nullable=False)
    equipment_id = Column(Integer, ForeignKey("client_equipment.id"), nullable=True)
    engineer_id  = Column(Integer, ForeignKey("users.id"),            nullable=True)
    created_by   = Column(Integer, ForeignKey("users.id"),            nullable=False)
    type         = Column(Enum("repair","maintenance","installation"), nullable=False, default="repair")
    priority     = Column(Enum("low","normal","high","critical"),     nullable=False, default="normal")
    status       = Column(Enum("new","assigned","in_progress","done","closed"), nullable=False, default="new")
    description  = Column(Text, nullable=False)
    resolution   = Column(Text)
    created_at   = Column(DateTime, server_default=func.now())
    updated_at   = Column(DateTime, server_default=func.now(), onupdate=func.now())
    closed_at    = Column(DateTime)

    client     = relationship("Client")
    equipment  = relationship("ClientEquipment", back_populates="service_requests")
    engineer   = relationship("User", foreign_keys=[engineer_id])
    creator    = relationship("User", foreign_keys=[created_by])
    movements  = relationship("StockMovement", back_populates="request")
