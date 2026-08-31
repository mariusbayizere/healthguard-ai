"""Analytics business rules.

Every figure means literally what its name says: "completed today" is filtered
to today, and average waits are separated into *quoted* (what the patient was
told at intake) and *measured* (what actually happened).
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Sequence

import structlog
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import ConflictError
from app.models.analytics import Analytics
from app.repositories import (
    analytics_repository,
    doctor_repository,
    patient_repository,
    queue_repository,
    sms_log_repository,
    triage_repository,
)

logger = structlog.get_logger(__name__)

CLEAR_ALL_TOKEN = "CLEAR_ALL"


def _start_of_today_utc() -> datetime:
    return datetime.combine(datetime.now(timezone.utc).date(), time.min, tzinfo=timezone.utc)


def _percentage(count: int, total: int) -> float:
    return round(count / total * 100, 1) if total else 0.0


def build_summary(db: Session) -> dict[str, int]:
    """Headline counts across patients, triage, queue and SMS."""
    triage = triage_repository.urgency_counts(db)
    queue = queue_repository.status_counts(db)
    sms = sms_log_repository.status_counts(db)
    return {
        "total_patients": patient_repository.count(db),
        "total_triage_done": triage["total"],
        "critical_cases": triage["critical"],
        "urgent_cases": triage["urgent"],
        "routine_cases": triage["routine"],
        "queue_waiting": queue["waiting"],
        "queue_in_progress": queue["in_progress"],
        "queue_done": queue["done"],
        "queue_cancelled": queue["cancelled"],
        "sms_sent": sms["sent"],
        "sms_failed": sms["failed"],
        "doctors_on_duty": doctor_repository.count_on_duty(db),
    }


def build_urgency_breakdown(db: Session) -> dict:
    """Share of cases at each acuity. No data yields zeroes, not an error."""
    counts = triage_repository.urgency_counts(db)
    total = counts["total"]
    return {
        "total": total,
        "critical": {"count": counts["critical"], "percentage": _percentage(counts["critical"], total)},
        "urgent": {"count": counts["urgent"], "percentage": _percentage(counts["urgent"], total)},
        "routine": {"count": counts["routine"], "percentage": _percentage(counts["routine"], total)},
    }


def build_queue_performance(db: Session) -> dict:
    """Queue throughput, comparing the wait we quote with the wait we deliver."""
    stats = queue_repository.performance(db, since=_start_of_today_utc())
    return {
        "currently_waiting": stats["waiting"],
        "currently_in_progress": stats["in_progress"],
        "completed_today": stats["completed_today"],
        "average_quoted_wait_minutes": stats["avg_quoted"],
        "average_actual_wait_minutes": stats["avg_actual"],
    }


def build_language_breakdown(db: Session) -> dict[str, int]:
    """Reports per detected language — the multilingual coverage metric."""
    from app.repositories import symptom_report_repository

    return symptom_report_repository.language_counts(db)


def list_snapshots(
    db: Session, *, skip: int, limit: int
) -> tuple[Sequence[Analytics], int]:
    """Stored daily snapshots, most recent first."""
    return analytics_repository.list_snapshots(db, skip=skip, limit=limit)


def save_daily_snapshot(db: Session) -> Analytics:
    """Record today's snapshot, replacing any snapshot already taken today."""
    triage = triage_repository.urgency_counts(db)
    snapshot = analytics_repository.upsert(
        db,
        {
            "snapshot_date": datetime.now(timezone.utc).date(),
            "total_patients": patient_repository.count(db),
            "total_triaged": triage["total"],
            "critical_cases": triage["critical"],
            "urgent_cases": triage["urgent"],
            "routine_cases": triage["routine"],
            "avg_wait_time_mins": queue_repository.average_actual_wait_minutes(db),
            # Left unset until the NLP model extracts symptom entities; a guess
            # here would be indistinguishable from a real measurement.
            "top_symptom": None,
        },
    )
    logger.info(
        "analytics_snapshot_saved",
        snapshot_date=str(snapshot.snapshot_date),
        total_triaged=snapshot.total_triaged,
    )
    return snapshot


def delete_snapshot(db: Session, snapshot_date: date) -> int:
    """Delete one day's snapshot. Returns the number of rows removed."""
    return analytics_repository.delete_by_date(db, snapshot_date)


def clear_all_snapshots(db: Session, confirm: str | None) -> int:
    """Delete every stored snapshot.

    Guarded twice: refused outright in production, and elsewhere requires an
    explicit confirmation token so a stray DELETE cannot wipe the history.
    """
    if settings.is_production:
        raise ConflictError(
            "Bulk analytics deletion is disabled in production",
            code="BULK_DELETE_DISABLED",
        )
    if confirm != CLEAR_ALL_TOKEN:
        raise ConflictError(
            f"Refusing to delete all analytics snapshots without ?confirm={CLEAR_ALL_TOKEN}",
            code="CONFIRMATION_REQUIRED",
        )
    deleted = analytics_repository.delete_all(db)
    logger.warning("analytics_cleared", deleted_rows=deleted)
    return deleted
