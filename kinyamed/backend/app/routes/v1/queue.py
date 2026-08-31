"""Queue endpoints. HTTP only — all rules live in `queue_service`."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import CurrentUser, StaffUser, assert_may_act_for_patient
from app.models.queue import Queue, QueueStatus
from app.schemas.common import PaginatedResponse, PaginationParams, pagination
from app.schemas.queue import QueueDoctorAssignment, QueueItemResponse, QueueStatusUpdate
from app.services import queue_service
from app.services.queue_service import QueueItem

router = APIRouter(prefix="/queue", tags=["Queue"])


def _waiting_minutes(entry: Queue) -> int:
    end = entry.completed_at or entry.started_at or datetime.now(timezone.utc)
    return max(int((end - entry.created_at).total_seconds() // 60), 0)


def _to_response(item: QueueItem) -> QueueItemResponse:
    """Render a queue entry, tolerating an incomplete patient chain."""
    entry = item.entry
    report = entry.triage_result.symptom_report if entry.triage_result else None
    patient = report.patient if report else None
    return QueueItemResponse(
        id=entry.id,
        queue_number=entry.queue_number,
        queue_position=item.position,
        patient_id=patient.id if patient else 0,
        patient_name=patient.name if patient else "Unknown",
        patient_phone=patient.phone if patient else "Unknown",
        urgency_level=entry.triage_result.urgency_level,
        symptoms=report.raw_input if report else "",
        language_detected=report.language_detected if report else None,
        status=entry.status,
        estimated_wait=item.estimated_wait,
        quoted_wait_at_intake=entry.estimated_wait,
        waiting_minutes=_waiting_minutes(entry),
        doctor_id=entry.doctor_id,
        created_at=entry.created_at,
        started_at=entry.started_at,
        completed_at=entry.completed_at,
    )


@router.get("", response_model=PaginatedResponse[QueueItemResponse])
def view_queue(
    _staff: StaffUser,
    db: Session = Depends(get_db),
    page: PaginationParams = Depends(pagination),
) -> PaginatedResponse[QueueItemResponse]:
    """The live queue in clinical order. Clinical staff only.

    Every row carries another patient's name, phone and symptoms, so this is
    never exposed to a patient account.

    Positions and wait estimates are recomputed on every read, so they reflect
    the queue as it stands now rather than as it was at intake.
    """
    items, total = queue_service.get_live_queue(db, skip=page.offset, limit=page.limit)
    return PaginatedResponse[QueueItemResponse].build(
        [_to_response(item) for item in items], total=total, params=page
    )


# Declared before /{queue_id} so the literal path is not captured as an id.
@router.get("/me", response_model=list[QueueItemResponse])
def my_queue_entries(
    user: CurrentUser, db: Session = Depends(get_db)
) -> list[QueueItemResponse]:
    """The caller's own live queue entries.

    This is how a patient checks their place in line without being able to see
    anyone else's record.
    """
    if user.patient_id is None:
        return []
    return [
        _to_response(queue_service.describe(db, entry))
        for entry in queue_service.get_active_entries_for_patient(db, user.patient_id)
    ]


@router.get("/{queue_id}", response_model=QueueItemResponse)
def get_queue_entry(
    queue_id: int, user: CurrentUser, db: Session = Depends(get_db)
) -> QueueItemResponse:
    """Fetch one queue entry. Staff may read any; a patient only their own."""
    entry = queue_service.get_entry(db, queue_id)
    patient = entry.triage_result.symptom_report.patient
    assert_may_act_for_patient(user, patient.id)
    return _to_response(queue_service.describe(db, entry))


@router.patch("/{queue_id}/status", response_model=QueueItemResponse)
def update_queue_status(
    queue_id: int,
    data: QueueStatusUpdate,
    _staff: StaffUser,
    db: Session = Depends(get_db),
) -> QueueItemResponse:
    """Advance a queue entry. Clinical staff only; legal transitions only."""
    entry = queue_service.get_entry(db, queue_id)
    queue_service.change_status(db, entry, data.status)
    return _to_response(queue_service.describe(db, entry))


@router.patch("/{queue_id}/assign-doctor", response_model=QueueItemResponse)
def assign_doctor(
    queue_id: int,
    data: QueueDoctorAssignment,
    _staff: StaffUser,
    db: Session = Depends(get_db),
) -> QueueItemResponse:
    """Assign an on-duty clinician and start the consultation. Staff only."""
    entry = queue_service.get_entry(db, queue_id)
    queue_service.assign_doctor(db, entry, data.doctor_id)
    return _to_response(queue_service.describe(db, entry))


@router.delete("/{queue_id}", response_model=QueueItemResponse, status_code=status.HTTP_200_OK)
def remove_from_queue(
    queue_id: int, _staff: StaffUser, db: Session = Depends(get_db)
) -> QueueItemResponse:
    """Remove a patient from the queue by cancelling their entry. Staff only.

    This is a state change, not a deletion: the triage result and any
    consultation notes are clinical history and are kept.
    """
    entry = queue_service.get_entry(db, queue_id)
    queue_service.change_status(db, entry, QueueStatus.CANCELLED)
    return _to_response(queue_service.describe(db, entry))
