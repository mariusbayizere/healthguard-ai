from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.queue_service import get_full_queue

router = APIRouter(prefix="/queue", tags=["Queue"])

@router.get("/")
def view_queue(db: Session = Depends(get_db)):
    queue = get_full_queue(db)
    result = []
    for entry in queue:
        triage   = entry.triage_result
        report   = triage.symptom_report if triage else None
        patient  = report.patient if report else None
        result.append({
            "queue_number":   entry.queue_number,
            "queue_position": entry.queue_position,
            "patient_name":   patient.name  if patient else "Unknown",
            "patient_phone":  patient.phone if patient else "Unknown",
            "urgency_level":  triage.urgency_level.value if triage else "ROUTINE",
            "symptoms":       report.raw_input if report else "",
            "status":         entry.status.value,
            "estimated_wait": entry.estimated_wait,
            "created_at":     entry.created_at
        })
    return result
