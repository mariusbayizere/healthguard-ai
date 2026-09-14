"""Triage endpoints. HTTP only — all rules live in `triage_service`."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentUser, assert_may_act_for_patient
from app.schemas.triage import TriageRequest, TriageResponse
from app.services import patient_service, queue_service, triage_service
from app.services.patient_message import PATIENT_MESSAGE_LANGUAGE, patient_receipt
from app.services.sms_service import send_sms_in_background
from app.services.triage_service import SymptomClassifier

router = APIRouter(prefix="/triage", tags=["Triage"])


def get_triage_classifier() -> SymptomClassifier | None:
    """The loaded model, or None. `run_triage` fails closed on None.

    A dependency so tests of queue mechanics can supply a scripted classifier;
    the absent-model path is tested through this real implementation.
    """
    return triage_service.get_classifier()


@router.post("", response_model=TriageResponse, status_code=status.HTTP_201_CREATED)
def submit_triage(
    data: TriageRequest,
    background_tasks: BackgroundTasks,
    user: CurrentUser,
    db: Session = Depends(get_db),
    classifier: SymptomClassifier | None = Depends(get_triage_classifier),
) -> TriageResponse:
    """Triage a symptom report and place the patient in the queue.

    Returns 503 with Retry-After, and writes nothing, when the trained model
    cannot classify. Authorisation and the patient lookup run first, so a
    caller who may not submit learns nothing about model state.

    Staff may submit on behalf of any patient; a patient may submit only for
    themselves.

    The patient's SMS is queued as a background task after the triage has been
    committed, so the response is not held open by the carrier and a delivery
    failure cannot undo the triage.
    """
    assert_may_act_for_patient(user, data.patient_id)
    patient = patient_service.get_patient(db, data.patient_id)
    outcome = triage_service.run_triage(
        db, patient=patient, symptoms_input=data.symptoms_input, classifier=classifier
    )

    review = triage_service.review_status(outcome.result.confidence_score)

    background_tasks.add_task(
        send_sms_in_background, patient.id, patient.phone, outcome.sms_message
    )

    return TriageResponse(
        triage_id=outcome.result.id,
        patient_id=patient.id,
        patient_name=patient.name,
        urgency_level=outcome.result.urgency_level,
        confidence_score=outcome.result.confidence_score,
        requires_human_review=review.requires_human_review,
        review_reason=review.reason,
        patient_response=outcome.sms_message,
        patient_message_language=PATIENT_MESSAGE_LANGUAGE,
        language_detected=outcome.report.language_detected,
        queue_id=outcome.queue_entry.id,
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
    position = queue_service.position_of(db, entry) if entry else 0
    review = triage_service.review_status(result.confidence_score)
    return TriageResponse(
        triage_id=result.id,
        patient_id=patient.id,
        patient_name=patient.name,
        urgency_level=result.urgency_level,
        confidence_score=result.confidence_score,
        requires_human_review=review.requires_human_review,
        review_reason=review.reason,
        patient_response=patient_receipt(
            queue_number=entry.queue_number if entry else 0, queue_position=position
        ),
        patient_message_language=PATIENT_MESSAGE_LANGUAGE,
        language_detected=result.symptom_report.language_detected,
        queue_id=entry.id if entry else 0,
        queue_number=entry.queue_number if entry else 0,
        queue_position=position,
        estimated_wait=entry.estimated_wait if entry else None,
        created_at=result.created_at,
    )
