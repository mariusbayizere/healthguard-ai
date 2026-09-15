"""Triage and symptom-report data access."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import cast, func, select
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.types import Date

from app.models.symptom_report import SymptomReport
from app.models.triage_result import TriageResult, UrgencyLevel
from app.repositories.base import BaseRepository


class SymptomReportRepository(BaseRepository[SymptomReport]):
    def __init__(self) -> None:
        super().__init__(SymptomReport)

    def language_counts(self, db: Session) -> dict[str, int]:
        """Reports grouped by detected language, for the research benchmark."""
        rows = db.execute(
            select(SymptomReport.language_detected, func.count())
            .group_by(SymptomReport.language_detected)
            .order_by(func.count().desc())
        ).all()
        return {language or "unknown": count for language, count in rows}


class TriageRepository(BaseRepository[TriageResult]):
    def __init__(self) -> None:
        super().__init__(TriageResult)

    def get_with_relations(self, db: Session, triage_id: int) -> TriageResult | None:
        """Return one triage result with its patient chain and queue entry, or None."""
        return (
            db.scalars(
                select(TriageResult)
                .options(
                    joinedload(TriageResult.symptom_report).joinedload(
                        SymptomReport.patient
                    ),
                    joinedload(TriageResult.queue_entry),
                )
                .where(TriageResult.id == triage_id)
            )
            .unique()
            .one_or_none()
        )

    def urgency_by_day(
        self, db: Session, *, days: int
    ) -> list[tuple[date, dict[str, int]]]:
        """Cases per acuity per day, over the last `days` days.

        COMPUTED FROM RAW TRIAGE ROWS, not from the `analytics` snapshot table.
        That table stores CUMULATIVE all-time counts -- `save_daily_snapshot`
        calls the same `urgency_counts` that the headline summary uses -- so
        plotting it over time would draw three monotonically rising curves and
        suggest acuity was climbing when the clinic was merely open. Nothing
        schedules the snapshot either, so differencing consecutive rows would
        attribute several days of cases to one. This reads the source of truth
        and is correct retroactively over data already collected.

        EVERY DAY IN THE RANGE IS RETURNED, including days with no cases. A
        time series with missing days lets the renderer join across a gap and
        draw a slope that never happened; explicit zeroes cannot be misdrawn.
        """
        today = datetime.now(UTC).date()
        start = today - timedelta(days=days - 1)
        day = cast(TriageResult.created_at, Date).label("day")

        rows = db.execute(
            select(day, TriageResult.urgency_level, func.count().label("n"))
            .where(cast(TriageResult.created_at, Date) >= start)
            .group_by(day, TriageResult.urgency_level)
        ).all()

        empty = {"critical": 0, "urgent": 0, "routine": 0}
        buckets: dict[date, dict[str, int]] = {
            start + timedelta(days=offset): dict(empty) for offset in range(days)
        }
        for row_day, level, count in rows:
            bucket = buckets.get(row_day)
            if bucket is not None:
                bucket[level.value.lower()] = count
        return sorted(buckets.items())

    def urgency_counts(self, db: Session) -> dict[str, int]:
        """Every acuity count in one pass over the table."""
        row = db.execute(
            select(
                func.count().label("total"),
                func.count()
                .filter(TriageResult.urgency_level == UrgencyLevel.CRITICAL)
                .label("critical"),
                func.count()
                .filter(TriageResult.urgency_level == UrgencyLevel.URGENT)
                .label("urgent"),
                func.count()
                .filter(TriageResult.urgency_level == UrgencyLevel.ROUTINE)
                .label("routine"),
            ).select_from(TriageResult)
        ).one()
        return {
            "total": row.total,
            "critical": row.critical,
            "urgent": row.urgent,
            "routine": row.routine,
        }

    def average_confidence(self, db: Session) -> float:
        """Mean classifier confidence across all triage results."""
        value = db.scalar(select(func.avg(TriageResult.confidence_score)))
        return round(float(value or 0.0), 3)


symptom_report_repository = SymptomReportRepository()
triage_repository = TriageRepository()
