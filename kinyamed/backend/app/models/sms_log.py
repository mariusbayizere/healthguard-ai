from sqlalchemy import Column, Integer, DateTime, Text, Enum, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import enum

class SMSStatus(enum.Enum):
    SENT    = "SENT"
    FAILED  = "FAILED"
    PENDING = "PENDING"

class SMSLog(Base):
    __tablename__ = "sms_logs"

    id         = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    message    = Column(Text, nullable=False)
    status     = Column(Enum(SMSStatus), default=SMSStatus.PENDING)
    sent_at    = Column(DateTime, default=datetime.utcnow)

    patient = relationship("Patient", back_populates="sms_logs")
