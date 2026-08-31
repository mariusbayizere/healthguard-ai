"""Triage and symptom-report data access."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

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
                    joinedload(TriageResult.symptom_report).joinedload(SymptomReport.patient),
                    joinedload(TriageResult.queue_entry),
                )
                .where(TriageResult.id == triage_id)
            )
            .unique()
            .one_or_none()
        )

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
