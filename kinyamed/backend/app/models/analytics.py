from sqlalchemy import Column, Integer, String, DateTime, Float
from app.core.database import Base
from datetime import datetime

class Analytics(Base):
    __tablename__ = "analytics"

    id                 = Column(Integer, primary_key=True, index=True)
    date               = Column(DateTime, nullable=False)
    total_patients     = Column(Integer, default=0)
    critical_cases     = Column(Integer, default=0)
    urgent_cases       = Column(Integer, default=0)
    routine_cases      = Column(Integer, default=0)
    avg_wait_time_mins = Column(Float,   default=0.0)
    top_symptom        = Column(String(100))
    created_at         = Column(DateTime, default=datetime.utcnow)
