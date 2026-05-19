from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class Consultation(Base):
    __tablename__ = "consultations"

    id             = Column(Integer, primary_key=True, index=True)
    queue_entry_id = Column(Integer, ForeignKey("queue.id"),    nullable=False)
    doctor_id      = Column(Integer, ForeignKey("doctors.id"),  nullable=False)
    notes          = Column(Text)
    diagnosis      = Column(Text)
    outcome        = Column(String(100))
    created_at     = Column(DateTime, default=datetime.utcnow)

    queue_entry = relationship("Queue",  back_populates="consultation")
    doctor      = relationship("Doctor", back_populates="consultations")
