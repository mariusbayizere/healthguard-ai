from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.patient import Patient
from app.schemas.triage import TriageRequest, TriageResponse
from app.services.triage_service import run_triage

router = APIRouter(prefix="/triage", tags=["Triage"])

@router.post("/", response_model=TriageResponse)
def submit_triage(data: TriageRequest, db: Session = Depends(get_db)):
    patient = db.query(Patient).filter(Patient.id == data.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    result, queue_entry = run_triage(
        db             = db,
        patient_id     = patient.id,
        patient_name   = patient.name,
        symptoms_input = data.symptoms_input
    )

    return TriageResponse(
        patient_id          = patient.id,
        patient_name        = patient.name,
        urgency_level       = result.urgency_level.value,
        possible_conditions = result.possible_conditions,
        confidence_score    = result.confidence_score,
        ai_response_rw      = result.ai_response_rw,
        queue_number        = queue_entry.queue_number,
        estimated_wait      = queue_entry.estimated_wait
    )
