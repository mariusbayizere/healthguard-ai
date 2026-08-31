"""Triage endpoints. HTTP only — all rules live in `triage_service`."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentUser, assert_may_act_for_patient
from app.schemas.triage import TriageResponse, TriageRequest
from app.services import patient_service, queue_service, triage_service
from app.services.sms_service import send_sms_in_background

router = APIRouter(prefix="/triage", tags=["Triage"])


@router.post("", response_model=TriageResponse, status_code=status.HTTP_201_CREATED)
def submit_triage(
    data: TriageRequest,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> TriageResponse:
    """Triage a symptom report and place the patient in the queue.

    Staff may submit on behalf of any patient; a patient may submit only for
    themselves.

    The patient's SMS is queued as a background task after the triage has been
    committed, so the response is not held open by the carrier and a delivery
    failure cannot undo the triage.
    """
    assert_may_act_for_patient(user, data.patient_id)
    patient = patient_service.get_patient(db, data.patient_id)
    outcome = triage_service.run_triage(
        db, patient=patient, symptoms_input=data.symptoms_input
    )

    background_tasks.add_task(
        send_sms_in_background, patient.id, patient.phone, outcome.sms_message
    )

    return TriageResponse(
        triage_id=outcome.result.id,
        patient_id=patient.id,
        patient_name=patient.name,
        urgency_level=outcome.result.urgency_level,
        possible_conditions=outcome.result.possible_conditions,
        confidence_score=outcome.result.confidence_score,
        ai_response_rw=outcome.result.ai_response_rw,
        language_detected=outcome.report.language_detected,
        queue_number=outcome.queue_entry.queue_number,
        queue_position=outcome.queue_position,
        estimated_wait=outcome.queue_entry.estimated_wait,
        created_at=outcome.result.created_at,
    )


@router.get("/{triage_id}", response_model=TriageResponse)
def get_triage(
    triage_id: int, user: CurrentUser, db: Session = Depends(get_db)
) -> TriageResponse:
    """Fetch a previous triage with its current queue position.

    Staff may read any triage; a patient only their own.
    """
    result = triage_service.get_triage(db, triage_id)
    patient = result.symptom_report.patient
    assert_may_act_for_patient(user, patient.id)
    entry = result.queue_entry
    return TriageResponse(
        triage_id=result.id,
        patient_id=patient.id,
        patient_name=patient.name,
        urgency_level=result.urgency_level,
        possible_conditions=result.possible_conditions,
        confidence_score=result.confidence_score,
        ai_response_rw=result.ai_response_rw,
        language_detected=result.symptom_report.language_detected,
        queue_number=entry.queue_number if entry else 0,
        queue_position=queue_service.position_of(db, entry) if entry else 0,
        estimated_wait=entry.estimated_wait if entry else None,
        created_at=result.created_at,
    )
