from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.core.database import Base

class Interaction(Base):
    __tablename__ = "interactions"

    id          = Column(Integer, primary_key=True, index=True)
    client_id   = Column(Integer, ForeignKey("clients.id",  ondelete="CASCADE"), nullable=False)
    user_id     = Column(Integer, ForeignKey("users.id",    ondelete="RESTRICT"), nullable=False)
    type        = Column(Enum("call","email","meeting","other"), nullable=False, default="other")
    date        = Column(DateTime, nullable=False)
    subject     = Column(String(255), nullable=False)
    description = Column(Text)
    created_at  = Column(DateTime, server_default=func.now())

    client = relationship("Client", back_populates="interactions")
    user   = relationship("User")
