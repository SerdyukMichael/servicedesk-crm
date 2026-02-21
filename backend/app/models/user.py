from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(64),  unique=True, nullable=False)
    email         = Column(String(128), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name     = Column(String(128), nullable=False)
    role          = Column(Enum("admin","manager","engineer"), nullable=False, default="engineer")
    is_active     = Column(Boolean, default=True)
    created_at    = Column(DateTime, server_default=func.now())
    updated_at    = Column(DateTime, server_default=func.now(), onupdate=func.now())

    clients       = relationship("Client", back_populates="manager", foreign_keys="Client.manager_id")
