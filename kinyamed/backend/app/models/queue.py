from sqlalchemy import Column, Integer, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import enum

class QueueStatus(enum.Enum):
    WAITING     = "WAITING"
    IN_PROGRESS = "IN_PROGRESS"
    DONE        = "DONE"

class Queue(Base):
    __tablename__ = "queue"

    id               = Column(Integer, primary_key=True, index=True)
    triage_result_id = Column(Integer, ForeignKey("triage_results.id"), nullable=False)
    doctor_id        = Column(Integer, ForeignKey("doctors.id"), nullable=True)
    queue_number     = Column(Integer, nullable=False)
    queue_position   = Column(Integer, nullable=False)
    status           = Column(Enum(QueueStatus), default=QueueStatus.WAITING)
    estimated_wait   = Column(Integer)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow)

    triage_result = relationship("TriageResult", back_populates="queue_entry")
    doctor        = relationship("Doctor",       back_populates="queue_entries")
    consultation  = relationship("Consultation", back_populates="queue_entry", uselist=False)
