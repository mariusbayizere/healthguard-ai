from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class Patient(Base):
    __tablename__ = "patients"

    id         = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), nullable=False)
    phone      = Column(String(20),  nullable=False)
    age        = Column(Integer)
    gender     = Column(String(10))
    location   = Column(String(100))
    created_at = Column(DateTime, default=datetime.utcnow)

    symptom_reports = relationship("SymptomReport", back_populates="patient")
    sms_logs        = relationship("SMSLog",        back_populates="patient")
