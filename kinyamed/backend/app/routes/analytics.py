from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.triage_result import TriageResult, UrgencyLevel
from app.models.queue import Queue, QueueStatus

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    total    = db.query(TriageResult).count()
    critical = db.query(TriageResult).filter(TriageResult.urgency_level == UrgencyLevel.CRITICAL).count()
    urgent   = db.query(TriageResult).filter(TriageResult.urgency_level == UrgencyLevel.URGENT).count()
    routine  = db.query(TriageResult).filter(TriageResult.urgency_level == UrgencyLevel.ROUTINE).count()
    waiting  = db.query(Queue).filter(Queue.status == QueueStatus.WAITING).count()

    return {
        "total_patients":  total,
        "critical_cases":  critical,
        "urgent_cases":    urgent,
        "routine_cases":   routine,
        "currently_waiting": waiting
    }
