from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.database import get_db
from app.models.triage_result import TriageResult, UrgencyLevel
from app.models.queue import Queue, QueueStatus
from app.models.patient import Patient
from app.models.sms_log import SMSLog, SMSStatus
from app.models.analytics import Analytics
from datetime import datetime

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# GET — overall summary
@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    total    = db.query(TriageResult).count()
    critical = db.query(TriageResult).filter(TriageResult.urgency_level == UrgencyLevel.CRITICAL).count()
    urgent   = db.query(TriageResult).filter(TriageResult.urgency_level == UrgencyLevel.URGENT).count()
    routine  = db.query(TriageResult).filter(TriageResult.urgency_level == UrgencyLevel.ROUTINE).count()
    waiting  = db.query(Queue).filter(Queue.status == QueueStatus.WAITING).count()
    in_prog  = db.query(Queue).filter(Queue.status == QueueStatus.IN_PROGRESS).count()
    done     = db.query(Queue).filter(Queue.status == QueueStatus.DONE).count()
    patients = db.query(Patient).count()
    sms_sent = db.query(SMSLog).filter(SMSLog.status == SMSStatus.SENT).count()

    return {
        "total_patients":      patients,
        "total_triage_done":   total,
        "critical_cases":      critical,
        "urgent_cases":        urgent,
        "routine_cases":       routine,
        "queue_waiting":       waiting,
        "queue_in_progress":   in_prog,
        "queue_done":          done,
        "sms_sent":            sms_sent
    }

# GET — urgency breakdown
@router.get("/urgency-breakdown")
def get_urgency_breakdown(db: Session = Depends(get_db)):
    total = db.query(TriageResult).count()
    if total == 0:
        return {"message": "No triage data yet"}
    critical = db.query(TriageResult).filter(TriageResult.urgency_level == UrgencyLevel.CRITICAL).count()
    urgent   = db.query(TriageResult).filter(TriageResult.urgency_level == UrgencyLevel.URGENT).count()
    routine  = db.query(TriageResult).filter(TriageResult.urgency_level == UrgencyLevel.ROUTINE).count()
    return {
        "critical": {"count": critical, "percentage": round(critical / total * 100, 1)},
        "urgent":   {"count": urgent,   "percentage": round(urgent   / total * 100, 1)},
        "routine":  {"count": routine,  "percentage": round(routine  / total * 100, 1)},
    }

# GET — queue performance
@router.get("/queue-performance")
def get_queue_performance(db: Session = Depends(get_db)):
    avg_wait = db.query(func.avg(Queue.estimated_wait)).scalar()
    return {
        "average_wait_minutes": round(avg_wait, 1) if avg_wait else 0,
        "total_in_queue":       db.query(Queue).count(),
        "completed_today":      db.query(Queue).filter(Queue.status == QueueStatus.DONE).count()
    }

# GET — all saved daily analytics records
@router.get("/daily")
def get_daily_analytics(db: Session = Depends(get_db)):
    return db.query(Analytics).order_by(Analytics.date.desc()).all()

# POST — manually save today's analytics snapshot
@router.post("/daily/snapshot")
def save_daily_snapshot(db: Session = Depends(get_db)):
    total    = db.query(TriageResult).count()
    critical = db.query(TriageResult).filter(TriageResult.urgency_level == UrgencyLevel.CRITICAL).count()
    urgent   = db.query(TriageResult).filter(TriageResult.urgency_level == UrgencyLevel.URGENT).count()
    routine  = db.query(TriageResult).filter(TriageResult.urgency_level == UrgencyLevel.ROUTINE).count()
    avg_wait = db.query(func.avg(Queue.estimated_wait)).scalar()

    snapshot = Analytics(
        date=datetime.utcnow(),
        total_patients=total,
        critical_cases=critical,
        urgent_cases=urgent,
        routine_cases=routine,
        avg_wait_time_mins=round(avg_wait, 1) if avg_wait else 0.0
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return {"message": "Daily snapshot saved", "data": {
        "date": snapshot.date,
        "total_patients": snapshot.total_patients,
        "critical_cases": snapshot.critical_cases,
        "urgent_cases": snapshot.urgent_cases,
        "routine_cases": snapshot.routine_cases,
        "avg_wait_time_mins": snapshot.avg_wait_time_mins
    }}

# DELETE — clear all analytics records
@router.delete("/daily")
def clear_analytics(db: Session = Depends(get_db)):
    db.query(Analytics).delete()
    db.commit()
    return {"message": "All analytics records cleared"}
