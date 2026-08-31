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
from datetime import datetime, timezone

import structlog
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    DoctorNotFoundError,
    DoctorNotOnDutyError,
    InvalidQueueStatusTransitionError,
    QueueEntryNotActiveError,
    QueueEntryNotFoundError,
)
from app.models.queue import ACTIVE_STATUSES, ALLOWED_STATUS_TRANSITIONS, Queue, QueueStatus
from app.models.triage_result import TriageResult, UrgencyLevel
from app.repositories import doctor_repository, queue_repository

logger = structlog.get_logger(__name__)


@dataclass(frozen=True)
class QueueItem:
    """A queue entry together with its freshly computed position and wait."""

    entry: Queue
    position: int
    estimated_wait: int


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _capacity(db: Session) -> int:
    """Clinicians available to see patients, never less than one."""
    return max(doctor_repository.count_on_duty(db), 1)


def _wait_for(priority: int, ahead: int, capacity: int) -> int:
    """Minutes a patient at `priority` waits behind `ahead` patients.

    The work is divided across clinicians on duty: two doctors clear a queue
    twice as fast as one.
    """
    if priority == UrgencyLevel.CRITICAL.priority:
        return 0  # critical cases are seen immediately
    minutes = int(round(ahead / capacity)) * settings.MINUTES_PER_PATIENT
    if priority == UrgencyLevel.URGENT.priority:
        return min(minutes, settings.URGENT_MAX_WAIT_MINUTES)
    return minutes


def estimate_wait(db: Session, *, priority: int, ahead: int | None = None) -> int:
    """Estimate the minutes a patient at `priority` will wait."""
    if ahead is None:
        ahead = queue_repository.count_ahead_of_priority(db, priority)
    return _wait_for(priority, ahead, _capacity(db))


def get_live_queue(
    db: Session, *, skip: int = 0, limit: int | None = None
) -> tuple[list[QueueItem], int]:
    """Return the live queue in clinical order, with positions, waits and total.

    Positions are absolute: paginating from offset 20 still reports position 21
    for the first row on that page.
    """
    entries = queue_repository.list_active(db, skip=skip, limit=limit)
    capacity = _capacity(db)
    items = [
        QueueItem(
            entry=entry,
            position=skip + index + 1,
            estimated_wait=_wait_for(entry.priority, skip + index, capacity),
        )
        for index, entry in enumerate(entries)
    ]
    return items, queue_repository.count_active(db)


def get_active_entries_for_patient(db: Session, patient_id: int) -> list[Queue]:
    """Active queue entries belonging to one patient."""
    return list(queue_repository.active_for_patient(db, patient_id))


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
    return queue_repository.count_ahead_of_entry(db, entry) + 1


def describe(db: Session, entry: Queue) -> QueueItem:
    """Build the position/wait view of a single entry."""
    position = position_of(db, entry)
    wait = _wait_for(entry.priority, max(position - 1, 0), _capacity(db)) if position else 0
    return QueueItem(entry=entry, position=position, estimated_wait=wait)


def enqueue(db: Session, triage_result: TriageResult, *, commit: bool = False) -> Queue:
    """Place a triage result into the queue at its clinical priority.

    Does not commit by default: triage composes this with two other writes into
    a single transaction.
    """
    priority = triage_result.urgency_level.priority
    ahead = queue_repository.count_ahead_of_priority(db, priority)
    entry = queue_repository.create(
        db,
        commit=commit,
        triage_result_id=triage_result.id,
        priority=priority,
        status=QueueStatus.WAITING,
        estimated_wait=_wait_for(priority, ahead, _capacity(db)),
    )
    logger.info(
        "queue_entry_created",
        queue_number=entry.queue_number,
        priority=priority,
        patients_ahead=ahead,
        estimated_wait=entry.estimated_wait,
    )
    return entry


def change_status(
    db: Session, entry: Queue, new_status: QueueStatus, *, commit: bool = True
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

    fields: dict = {"status": new_status}
    if new_status == QueueStatus.IN_PROGRESS and entry.started_at is None:
        fields["started_at"] = _now()
    if new_status in (QueueStatus.DONE, QueueStatus.CANCELLED):
        fields["completed_at"] = _now()
    if new_status == QueueStatus.WAITING:
        fields["started_at"] = None

    previous = entry.status.value
    queue_repository.update(db, entry, commit=commit, **fields)
    logger.info(
        "queue_status_changed",
        queue_id=entry.id,
        from_status=previous,
        to_status=new_status.value,
    )
    return entry


def assign_doctor(db: Session, entry: Queue, doctor_id: int, *, commit: bool = True) -> Queue:
    """Assign an on-duty clinician and start the consultation."""
    doctor = doctor_repository.get_by_id(db, doctor_id)
    if doctor is None:
        raise DoctorNotFoundError(doctor_id)
    if not doctor.is_on_duty:
        raise DoctorNotOnDutyError(doctor_id, doctor.name)
    if entry.status not in ACTIVE_STATUSES:
        raise QueueEntryNotActiveError(entry.id, entry.status.value)

    queue_repository.update(db, entry, commit=False, doctor_id=doctor.id)
    if entry.status == QueueStatus.WAITING:
        change_status(db, entry, QueueStatus.IN_PROGRESS, commit=False)
    if commit:
        db.commit()
    logger.info("queue_doctor_assigned", queue_id=entry.id, doctor_id=doctor.id)
    return entry
