from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class SymptomReport(Base):
    __tablename__ = "symptom_reports"

    id                 = Column(Integer, primary_key=True, index=True)
    patient_id         = Column(Integer, ForeignKey("patients.id"), nullable=False)
    raw_input          = Column(Text, nullable=False)
    language_detected  = Column(String(20))
    symptoms_extracted = Column(Text)
    created_at         = Column(DateTime, default=datetime.utcnow)

    patient       = relationship("Patient",      back_populates="symptom_reports")
    triage_result = relationship("TriageResult", back_populates="symptom_report", uselist=False)
