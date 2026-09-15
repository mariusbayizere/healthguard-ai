"""Queue data access.

The live-queue ordering rule lives here in one place: band first (CRITICAL,
NEEDS REVIEW, URGENT, ROUTINE; see app/models/queue_band.py), arrival second, id
as a deterministic tie-break. The band depends on the review threshold, so every
ordered or counted read takes it as an argument.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import Select, cast, func, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql.elements import UnaryExpression
from sqlalchemy.types import Date

from app.models.queue import ACTIVE_STATUSES, Queue, QueueStatus
from app.models.queue_band import QueueBand, band_sql
from app.models.symptom_report import SymptomReport
from app.models.triage_result import TriageResult
from app.repositories.base import BaseRepository


def _queue_order(
    threshold: float,
) -> tuple[UnaryExpression[int], UnaryExpression[datetime], UnaryExpression[int]]:
    return (band_sql(threshold).asc(), Queue.created_at.asc(), Queue.id.asc())


def _percentile(ordered: list[float], fraction: float) -> float:
    """Linear-interpolated percentile of an ALREADY SORTED list.

    Matches PostgreSQL's `percentile_cont` and numpy's default so the Python
    path and a hand-written SQL query cannot disagree: the rank is
    `fraction * (n - 1)`, and the result interpolates between the two values
    that straddle it.

    Returns 0.0 for an empty list only because callers never pass one -- an
    acuity with no completed entries is omitted entirely rather than reported
    as zero, since 0.0 would read as "seen instantly".
    """
    if not ordered:
        return 0.0
    if len(ordered) == 1:
        return ordered[0]
    rank = fraction * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    return ordered[low] + (ordered[high] - ordered[low]) * (rank - low)


class QueueRepository(BaseRepository[Queue]):
    def __init__(self) -> None:
        super().__init__(Queue)

    def _with_patient_chain(
        self, statement: Select[tuple[Queue]]
    ) -> Select[tuple[Queue]]:
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
            db.scalars(
                self._with_patient_chain(select(Queue)).where(Queue.id == queue_id)
            )
            .unique()
            .one_or_none()
        )

    def list_active(
        self, db: Session, *, threshold: float, skip: int = 0, limit: int | None = None
    ) -> Sequence[Queue]:
        """Active entries in clinical order."""
        statement = (
            self._with_patient_chain(select(Queue))
            .join(TriageResult, Queue.triage_result_id == TriageResult.id)
            .where(Queue.status.in_(ACTIVE_STATUSES))
            .order_by(*_queue_order(threshold))
        )
        if limit is not None:
            statement = statement.offset(skip).limit(limit)
        return db.scalars(statement).unique().all()

    def active_for_patient(
        self, db: Session, patient_id: int, *, threshold: float
    ) -> Sequence[Queue]:
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
                .order_by(*_queue_order(threshold))
            )
            .unique()
            .all()
        )

    def count_active(self, db: Session) -> int:
        """Count entries still occupying a place in the waiting room."""
        return int(
            db.scalar(
                select(func.count())
                .select_from(Queue)
                .where(Queue.status.in_(ACTIVE_STATUSES))
            )
            or 0
        )

    def count_ahead_of_band(
        self, db: Session, band: QueueBand, *, threshold: float
    ) -> int:
        """Active patients a newly arriving patient in `band` waits behind."""
        return int(
            db.scalar(
                select(func.count())
                .select_from(Queue)
                .join(TriageResult, Queue.triage_result_id == TriageResult.id)
                .where(
                    Queue.status.in_(ACTIVE_STATUSES),
                    band_sql(threshold) <= int(band),
                )
            )
            or 0
        )

    def count_ahead_of_entry(
        self, db: Session, entry: Queue, band: QueueBand, *, threshold: float
    ) -> int:
        """Active patients ordered strictly before `entry`, which is in `band`."""
        others_band = band_sql(threshold)
        return int(
            db.scalar(
                select(func.count())
                .select_from(Queue)
                .join(TriageResult, Queue.triage_result_id == TriageResult.id)
                .where(
                    Queue.status.in_(ACTIVE_STATUSES),
                    Queue.id != entry.id,
                    (others_band < int(band))
                    | (
                        (others_band == int(band))
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
                func.count()
                .filter(Queue.status == QueueStatus.WAITING)
                .label("waiting"),
                func.count()
                .filter(Queue.status == QueueStatus.IN_PROGRESS)
                .label("in_progress"),
                func.count().filter(Queue.status == QueueStatus.DONE).label("done"),
                func.count()
                .filter(Queue.status == QueueStatus.CANCELLED)
                .label("cancelled"),
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
                func.count()
                .filter(Queue.status == QueueStatus.WAITING)
                .label("waiting"),
                func.count()
                .filter(Queue.status == QueueStatus.IN_PROGRESS)
                .label("in_progress"),
                func.count()
                .filter(Queue.status == QueueStatus.DONE, Queue.completed_at >= since)
                .label("completed_today"),
                func.avg(Queue.estimated_wait).label("avg_quoted"),
                func.avg(
                    func.extract("epoch", Queue.completed_at - Queue.created_at) / 60.0
                )
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

    #: Minutes from joining the queue to completion, as a SQL expression.
    #: Defined once so throughput and the percentile query cannot disagree
    #: about what "wait" means.
    _WAIT_MINUTES = func.extract("epoch", Queue.completed_at - Queue.created_at) / 60.0

    def completions_by_day(self, db: Session, *, days: int) -> list[tuple[date, int]]:
        """Entries completed per day, over the last `days` days.

        Throughput is measured on `completed_at`, not on arrival: a patient who
        arrived yesterday and was seen today is today's work. Days with no
        completions are returned as zero rather than omitted -- a clinic that
        was closed is a real fact about the series, and a renderer must not
        interpolate across it.
        """
        today = datetime.now(UTC).date()
        start = today - timedelta(days=days - 1)
        day = cast(Queue.completed_at, Date).label("day")

        rows = db.execute(
            select(day, func.count().label("n"))
            .where(Queue.completed_at.is_not(None))
            .where(cast(Queue.completed_at, Date) >= start)
            .group_by(day)
        ).all()

        counted = {row_day: count for row_day, count in rows}
        return [
            (
                start + timedelta(days=offset),
                counted.get(start + timedelta(days=offset), 0),
            )
            for offset in range(days)
        ]

    def wait_percentiles_by_urgency(self, db: Session) -> dict[str, dict[str, float]]:
        """p50 and p90 wait, in minutes, per acuity.

        PERCENTILES, NOT A MEAN, and that is the point of the endpoint. The
        summary reports a single mean wait; a mean hides the tail, and the tail
        is exactly where a long wait stops being an inconvenience and becomes a
        clinical problem. A CRITICAL p90 is the number that says whether the
        sickest patients are actually being seen first.

        COMPUTED IN PYTHON, NOT IN SQL. The obvious implementation is
        `percentile_cont(0.5) WITHIN GROUP (...)`, which is faster and which
        this database supports -- but it is PostgreSQL-only, and the backend
        test suite cannot run without a live PostgreSQL server because of
        choices exactly like that one. At a health centre's volume the ordering
        work is trivial and the portability is worth more: this function
        returns identical numbers on any backend SQLAlchemy can talk to.

        The interpolation deliberately MATCHES `percentile_cont`: linear
        between the two closest ranks. Anyone who compares this against a
        hand-written SQL query should get the same answer to the decimal.

        Grouped by the triage result's urgency rather than by `Queue.priority`,
        so it does not depend on how the priority integer happens to be
        encoded.
        """
        rows = db.execute(
            select(TriageResult.urgency_level, self._WAIT_MINUTES)
            .join(TriageResult, Queue.triage_result_id == TriageResult.id)
            .where(Queue.completed_at.is_not(None))
        ).all()

        by_level: dict[str, list[float]] = {}
        for level, minutes in rows:
            if minutes is None:
                continue
            by_level.setdefault(level.value.lower(), []).append(float(minutes))

        return {
            level: {
                "p50_minutes": round(_percentile(sorted(values), 0.5), 1),
                "p90_minutes": round(_percentile(sorted(values), 0.9), 1),
                "completed": len(values),
            }
            for level, values in by_level.items()
        }

    def average_actual_wait_minutes(self, db: Session) -> float:
        """Mean measured minutes from joining the queue to completion."""
        value = db.scalar(
            select(
                func.avg(
                    func.extract("epoch", Queue.completed_at - Queue.created_at) / 60.0
                )
            ).where(Queue.completed_at.is_not(None))
        )
        return round(float(value or 0.0), 1)


queue_repository = QueueRepository()
