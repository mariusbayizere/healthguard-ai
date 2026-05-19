from sqlalchemy import Column, Integer, DateTime, Text, Enum, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime
import enum

class UrgencyLevel(enum.Enum):
    CRITICAL = "CRITICAL"
    URGENT   = "URGENT"
    ROUTINE  = "ROUTINE"

class TriageResult(Base):
    __tablename__ = "triage_results"

    id                  = Column(Integer, primary_key=True, index=True)
    symptom_report_id   = Column(Integer, ForeignKey("symptom_reports.id"), nullable=False)
    urgency_level       = Column(Enum(UrgencyLevel), nullable=False)
    possible_conditions = Column(Text)
    confidence_score    = Column(Float)
    ai_response_rw      = Column(Text)
    created_at          = Column(DateTime, default=datetime.utcnow)

    symptom_report = relationship("SymptomReport", back_populates="triage_result")
    queue_entry    = relationship("Queue",         back_populates="triage_result", uselist=False)
