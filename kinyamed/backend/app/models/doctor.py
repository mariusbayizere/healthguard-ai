from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class Doctor(Base):
    __tablename__ = "doctors"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), nullable=False)
    email      = Column(String(100), unique=True, nullable=False)
    specialty  = Column(String(100))
    is_on_duty = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    queue_entries = relationship("Queue",        back_populates="doctor")
    consultations = relationship("Consultation", back_populates="doctor")
