"""Queue data access.

The live-queue ordering rule lives here in one place: acuity first, arrival
second, id as a deterministic tie-break.
"""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, joinedload

from app.models.queue import ACTIVE_STATUSES, Queue, QueueStatus
from app.models.symptom_report import SymptomReport
from app.models.triage_result import TriageResult
from app.repositories.base import BaseRepository

_QUEUE_ORDER = (Queue.priority.asc(), Queue.created_at.asc(), Queue.id.asc())


class QueueRepository(BaseRepository[Queue]):
    def __init__(self) -> None:
        super().__init__(Queue)

    def _with_patient_chain(self, statement: Select[tuple[Queue]]) -> Select[tuple[Queue]]:
        """Eager-load triage result -> symptom report -> patient.

        Rendering the queue touches all three for every row; under lazy loading
        that is three extra queries per row.
        """
        return statement.options(
            joinedload(Queue.triage_result)
            .joinedload(TriageResult.symptom_report)
            .joinedload(SymptomReport.patient)
        )

    def get_with_relations(self, db: Session, queue_id: int) -> Queue | None:
        """Return one queue entry with its patient chain loaded, or None."""
        return (
            db.scalars(self._with_patient_chain(select(Queue)).where(Queue.id == queue_id))
            .unique()
            .one_or_none()
        )

    def list_active(
        self, db: Session, *, skip: int = 0, limit: int | None = None
    ) -> Sequence[Queue]:
        """Active entries in clinical order."""
        statement = (
            self._with_patient_chain(select(Queue))
            .where(Queue.status.in_(ACTIVE_STATUSES))
            .order_by(*_QUEUE_ORDER)
        )
        if limit is not None:
            statement = statement.offset(skip).limit(limit)
        return db.scalars(statement).unique().all()

    def active_for_patient(self, db: Session, patient_id: int) -> Sequence[Queue]:
        """Active queue entries belonging to one patient, in clinical order."""
        return (
            db.scalars(
                self._with_patient_chain(select(Queue))
                .join(Queue.triage_result)
                .join(TriageResult.symptom_report)
                .where(
                    SymptomReport.patient_id == patient_id,
                    Queue.status.in_(ACTIVE_STATUSES),
                )
                .order_by(*_QUEUE_ORDER)
            )
            .unique()
            .all()
        )

    def count_active(self, db: Session) -> int:
        """Count entries still occupying a place in the waiting room."""
        return int(
            db.scalar(
                select(func.count()).select_from(Queue).where(Queue.status.in_(ACTIVE_STATUSES))
            )
            or 0
        )

    def count_ahead_of_priority(self, db: Session, priority: int) -> int:
        """Active patients a newly arriving patient at `priority` waits behind."""
        return int(
            db.scalar(
                select(func.count())
                .select_from(Queue)
                .where(Queue.status.in_(ACTIVE_STATUSES), Queue.priority <= priority)
            )
            or 0
        )

    def count_ahead_of_entry(self, db: Session, entry: Queue) -> int:
        """Active patients ordered strictly before `entry`."""
        return int(
            db.scalar(
                select(func.count())
                .select_from(Queue)
                .where(
                    Queue.status.in_(ACTIVE_STATUSES),
                    Queue.id != entry.id,
                    (Queue.priority < entry.priority)
                    | (
                        (Queue.priority == entry.priority)
                        & (Queue.created_at < entry.created_at)
                    ),
                )
            )
            or 0
        )

    def status_counts(self, db: Session) -> dict[str, int]:
        """Return every queue status count in one pass over the table."""
        row = db.execute(
            select(
                func.count().filter(Queue.status == QueueStatus.WAITING).label("waiting"),
                func.count()
                .filter(Queue.status == QueueStatus.IN_PROGRESS)
                .label("in_progress"),
                func.count().filter(Queue.status == QueueStatus.DONE).label("done"),
                func.count().filter(Queue.status == QueueStatus.CANCELLED).label("cancelled"),
            ).select_from(Queue)
        ).one()
        return {
            "waiting": row.waiting,
            "in_progress": row.in_progress,
            "done": row.done,
            "cancelled": row.cancelled,
        }

    def performance(self, db: Session, *, since: datetime) -> dict[str, float | int]:
        """Throughput counters plus quoted-versus-measured wait times."""
        row = db.execute(
            select(
                func.count().filter(Queue.status == QueueStatus.WAITING).label("waiting"),
                func.count()
                .filter(Queue.status == QueueStatus.IN_PROGRESS)
                .label("in_progress"),
                func.count()
                .filter(Queue.status == QueueStatus.DONE, Queue.completed_at >= since)
                .label("completed_today"),
                func.avg(Queue.estimated_wait).label("avg_quoted"),
                func.avg(func.extract("epoch", Queue.completed_at - Queue.created_at) / 60.0)
                .filter(Queue.completed_at.is_not(None))
                .label("avg_actual"),
            ).select_from(Queue)
        ).one()
        return {
            "waiting": row.waiting,
            "in_progress": row.in_progress,
            "completed_today": row.completed_today,
            "avg_quoted": round(float(row.avg_quoted or 0.0), 1),
            "avg_actual": round(float(row.avg_actual or 0.0), 1),
        }

    def average_actual_wait_minutes(self, db: Session) -> float:
        """Mean measured minutes from joining the queue to completion."""
        value = db.scalar(
            select(
                func.avg(func.extract("epoch", Queue.completed_at - Queue.created_at) / 60.0)
            ).where(Queue.completed_at.is_not(None))
        )
        return round(float(value or 0.0), 1)


queue_repository = QueueRepository()
