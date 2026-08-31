"""Analytics response schemas."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class UrgencyCount(BaseModel):
    count: int
    percentage: float = Field(description="Share of all triaged cases, 0-100.")


class SummaryResponse(BaseModel):
    total_patients: int
    total_triage_done: int
    critical_cases: int
    urgent_cases: int
    routine_cases: int
    queue_waiting: int
    queue_in_progress: int
    queue_done: int
    queue_cancelled: int
    sms_sent: int
    sms_failed: int
    doctors_on_duty: int


class UrgencyBreakdownResponse(BaseModel):
    total: int
    critical: UrgencyCount
    urgent: UrgencyCount
    routine: UrgencyCount


class QueuePerformanceResponse(BaseModel):
    currently_waiting: int
    currently_in_progress: int
    completed_today: int = Field(description="Entries completed since midnight UTC.")
    average_quoted_wait_minutes: float = Field(
        description="Mean wait quoted to patients at intake."
    )
    average_actual_wait_minutes: float = Field(
        description="Mean measured time from joining the queue to completion."
    )


class LanguageBreakdownResponse(BaseModel):
    """Symptom reports grouped by detected language."""

    counts: dict[str, int] = Field(
        description="Report count per detected language, most frequent first."
    )
    total: int


class AnalyticsSnapshotResponse(ORMModel):
    id: int
    snapshot_date: date
    total_patients: int
    total_triaged: int
    critical_cases: int
    urgent_cases: int
    routine_cases: int
    avg_wait_time_mins: float
    top_symptom: str | None
    created_at: datetime
    updated_at: datetime
