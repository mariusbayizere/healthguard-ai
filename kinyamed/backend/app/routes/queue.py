from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.queue import Queue, QueueStatus
from app.services.queue_service import get_full_queue

router = APIRouter(prefix="/queue", tags=["Queue"])

# GET ALL — full live queue
@router.get("/")
def view_queue(db: Session = Depends(get_db)):
    queue = get_full_queue(db)
    result = []
    for entry in queue:
        triage  = entry.triage_result
        report  = triage.symptom_report if triage else None
        patient = report.patient if report else None
        result.append({
            "id":             entry.id,
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

# GET ONE queue entry
@router.get("/{queue_id}")
def get_queue_entry(queue_id: int, db: Session = Depends(get_db)):
    entry = db.query(Queue).filter(Queue.id == queue_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    triage  = entry.triage_result
    report  = triage.symptom_report if triage else None
    patient = report.patient if report else None
    return {
        "id":             entry.id,
        "queue_number":   entry.queue_number,
        "queue_position": entry.queue_position,
        "patient_name":   patient.name  if patient else "Unknown",
        "urgency_level":  triage.urgency_level.value if triage else "ROUTINE",
        "status":         entry.status.value,
        "estimated_wait": entry.estimated_wait,
        "created_at":     entry.created_at
    }

# UPDATE — change queue status (WAITING → IN_PROGRESS → DONE)
@router.put("/{queue_id}/status")
def update_queue_status(queue_id: int, status: str, db: Session = Depends(get_db)):
    entry = db.query(Queue).filter(Queue.id == queue_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    try:
        entry.status = QueueStatus[status.upper()]
    except KeyError:
        raise HTTPException(status_code=400, detail="Invalid status. Use WAITING, IN_PROGRESS or DONE")
    db.commit()
    db.refresh(entry)
    return {"message": "Queue status updated", "new_status": entry.status.value}

# UPDATE — assign doctor to queue entry
@router.put("/{queue_id}/assign-doctor")
def assign_doctor(queue_id: int, doctor_id: int, db: Session = Depends(get_db)):
    entry = db.query(Queue).filter(Queue.id == queue_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    entry.doctor_id = doctor_id
    entry.status = QueueStatus.IN_PROGRESS
    db.commit()
    db.refresh(entry)
    return {"message": f"Doctor {doctor_id} assigned to queue entry {queue_id}"}

# DELETE — remove from queue
@router.delete("/{queue_id}")
def remove_from_queue(queue_id: int, db: Session = Depends(get_db)):
    entry = db.query(Queue).filter(Queue.id == queue_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    db.delete(entry)
    db.commit()
    return {"message": f"Queue entry {queue_id} removed successfully"}
