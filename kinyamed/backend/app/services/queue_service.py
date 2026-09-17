"""Queue business rules.

The queue is ordered by clinical priority first and arrival time second. A
patient's position is *derived* from that ordering every time it is read, so
adding, completing, cancelling or removing an entry can never leave stored
positions inconsistent with the real order.

All queries are delegated to the repository layer; this module holds only the
rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.orm import Session

from app.core.audit_context import AuditContext
from app.core.config import settings
from app.core.exceptions import (
    DoctorNotFoundError,
    DoctorNotOnDutyError,
    InvalidQueueStatusTransitionError,
    QueueEntryNotActiveError,
    QueueEntryNotFoundError,
)
from app.models.queue import (
    ACTIVE_STATUSES,
    ALLOWED_STATUS_TRANSITIONS,
    Queue,
    QueueStatus,
)
from app.models.queue_band import QueueBand, band_for
from app.models.triage_result import TriageResult
from app.repositories import doctor_repository, queue_repository
from app.services.audit import record, snapshot
from app.services.review import needs_review

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class QueueItem:
    """A queue entry together with its freshly computed position and wait."""

    entry: Queue
    position: int
    estimated_wait: int
    band: QueueBand


def _now() -> datetime:
    return datetime.now(UTC)


def _capacity(db: Session) -> int:
    """Clinicians available to see patients, never less than one."""
    return max(doctor_repository.count_on_duty(db), 1)


def _threshold() -> float:
    return settings.MODEL_CONFIDENCE_THRESHOLD


def band_of(triage_result: TriageResult) -> QueueBand:
    """The band a triage result sorts in, under the current review threshold."""
    return band_for(
        triage_result.urgency_level,
        requires_review=needs_review(triage_result.confidence_score, _threshold()),
    )


def _wait_for_band(band: QueueBand, ahead: int, capacity: int) -> int:
    """Minutes a patient in `band` waits behind `ahead` patients.

    The work is divided across clinicians on duty: two doctors clear a queue
    twice as fast as one. NEEDS REVIEW is seen before URGENT, so its quote is
    capped the same way.
    """
    if band is QueueBand.CRITICAL:
        return 0  # critical cases are seen immediately
    minutes = round(ahead / capacity) * settings.MINUTES_PER_PATIENT
    if band in (QueueBand.NEEDS_REVIEW, QueueBand.URGENT):
        return min(minutes, settings.URGENT_MAX_WAIT_MINUTES)
    return minutes


def get_live_queue(
    db: Session, *, skip: int = 0, limit: int | None = None
) -> tuple[list[QueueItem], int]:
    """Return the live queue in clinical order, with positions, waits and total.

    Positions are absolute: paginating from offset 20 still reports position 21
    for the first row on that page.
    """
    entries = queue_repository.list_active(
        db, threshold=_threshold(), skip=skip, limit=limit
    )
    capacity = _capacity(db)
    items = []
    for index, entry in enumerate(entries):
        band = band_of(entry.triage_result)
        items.append(
            QueueItem(
                entry=entry,
                position=skip + index + 1,
                estimated_wait=_wait_for_band(band, skip + index, capacity),
                band=band,
            )
        )
    return items, queue_repository.count_active(db)


def get_active_entries_for_patient(db: Session, patient_id: int) -> list[Queue]:
    """Active queue entries belonging to one patient."""
    return list(
        queue_repository.active_for_patient(db, patient_id, threshold=_threshold())
    )


def get_entry(db: Session, queue_id: int) -> Queue:
    """Load one queue entry with its patient chain, or raise."""
    entry = queue_repository.get_with_relations(db, queue_id)
    if entry is None:
        raise QueueEntryNotFoundError(queue_id)
    return entry


def position_of(db: Session, entry: Queue) -> int:
    """The 1-based position of an active entry; 0 once it has left the queue."""
    if entry.status not in ACTIVE_STATUSES:
        return 0
    return (
        queue_repository.count_ahead_of_entry(
            db, entry, band_of(entry.triage_result), threshold=_threshold()
        )
        + 1
    )


def describe(db: Session, entry: Queue) -> QueueItem:
    """Build the position/wait view of a single entry."""
    position = position_of(db, entry)
    band = band_of(entry.triage_result)
    wait = _wait_for_band(band, max(position - 1, 0), _capacity(db)) if position else 0
    return QueueItem(entry=entry, position=position, estimated_wait=wait, band=band)


def enqueue(db: Session, triage_result: TriageResult, *, commit: bool = False) -> Queue:
    """Place a triage result into the queue at its clinical priority and band.

    Does not commit by default: triage composes this with two other writes into
    a single transaction.
    """
    priority = triage_result.urgency_level.priority
    band = band_of(triage_result)
    ahead = queue_repository.count_ahead_of_band(db, band, threshold=_threshold())
    entry = queue_repository.create(
        db,
        commit=commit,
        triage_result_id=triage_result.id,
        priority=priority,
        status=QueueStatus.WAITING,
        estimated_wait=_wait_for_band(band, ahead, _capacity(db)),
    )
    logger.info(
        "queue_entry_created",
        queue_number=entry.queue_number,
        priority=priority,
        band=band.name,
        patients_ahead=ahead,
        estimated_wait=entry.estimated_wait,
    )
    return entry


def change_status(
    db: Session,
    entry: Queue,
    new_status: QueueStatus,
    *,
    commit: bool = True,
    audit: AuditContext | None = None,
) -> Queue:
    """Move an entry to `new_status`, rejecting transitions that make no sense."""
    if new_status == entry.status:
        return entry

    allowed = ALLOWED_STATUS_TRANSITIONS[entry.status]
    if new_status not in allowed:
        raise InvalidQueueStatusTransitionError(
            current=entry.status.value,
            requested=new_status.value,
            allowed=sorted(status.value for status in allowed),
        )

    fields: dict[str, Any] = {"status": new_status}
    if new_status == QueueStatus.IN_PROGRESS and entry.started_at is None:
        fields["started_at"] = _now()
    if new_status in (QueueStatus.DONE, QueueStatus.CANCELLED):
        fields["completed_at"] = _now()
    if new_status == QueueStatus.WAITING:
        fields["started_at"] = None

    previous = entry.status.value
    before = snapshot(entry)
    queue_repository.update(db, entry, commit=False, **fields)
    # `audit` is None when another operation calls this as one of its steps
    # (assigning a doctor also starts the consultation). That operation writes
    # the single row for what it did; two rows would describe one act twice.
    if audit is not None:
        record(
            db,
            action="CHANGE_QUEUE_STATUS",
            table_name="queue",
            record_id=entry.id,
            before=before,
            after=snapshot(entry),
            actor=audit.actor,
            ip_address=audit.ip_address,
            user_agent=audit.user_agent,
        )
    if commit:
        db.commit()
    logger.info(
        "queue_status_changed",
        queue_id=entry.id,
        from_status=previous,
        to_status=new_status.value,
    )
    return entry


def assign_doctor(
    db: Session,
    entry: Queue,
    doctor_id: int,
    *,
    commit: bool = True,
    audit: AuditContext | None = None,
) -> Queue:
    """Assign an on-duty clinician and start the consultation."""
    doctor = doctor_repository.get_by_id(db, doctor_id)
    if doctor is None:
        raise DoctorNotFoundError(doctor_id)
    if not doctor.is_on_duty:
        raise DoctorNotOnDutyError(doctor_id, doctor.name)
    if entry.status not in ACTIVE_STATUSES:
        raise QueueEntryNotActiveError(entry.id, entry.status.value)

    before = snapshot(entry)
    queue_repository.update(db, entry, commit=False, doctor_id=doctor.id)
    if entry.status == QueueStatus.WAITING:
        change_status(db, entry, QueueStatus.IN_PROGRESS, commit=False)
    if audit is not None:
        record(
            db,
            action="ASSIGN_DOCTOR",
            table_name="queue",
            record_id=entry.id,
            before=before,
            after=snapshot(entry),
            actor=audit.actor,
            ip_address=audit.ip_address,
            user_agent=audit.user_agent,
        )
    if commit:
        db.commit()
    logger.info("queue_doctor_assigned", queue_id=entry.id, doctor_id=doctor.id)
    return entry
