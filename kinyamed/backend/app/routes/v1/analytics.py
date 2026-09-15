"""Analytics endpoints. HTTP only — all rules live in `analytics_service`."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AdminUser
from app.schemas.analytics import (
    AnalyticsSnapshotResponse,
    LanguageBreakdownResponse,
    QueuePerformanceResponse,
    SummaryResponse,
    ThroughputResponse,
    UrgencyBreakdownResponse,
    UrgencyOverTimeResponse,
    WaitByUrgencyResponse,
)
from app.schemas.common import PaginatedResponse, PaginationParams, pagination
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/summary", response_model=SummaryResponse)
def get_summary(_admin: AdminUser, db: Session = Depends(get_db)) -> SummaryResponse:
    """Headline counts across patients, triage, queue and SMS."""
    return SummaryResponse(**analytics_service.build_summary(db))


@router.get("/urgency-breakdown", response_model=UrgencyBreakdownResponse)
def get_urgency_breakdown(
    _admin: AdminUser, db: Session = Depends(get_db)
) -> UrgencyBreakdownResponse:
    """Share of cases at each acuity."""
    return UrgencyBreakdownResponse(**analytics_service.build_urgency_breakdown(db))


@router.get("/queue-performance", response_model=QueuePerformanceResponse)
def get_queue_performance(
    _admin: AdminUser, db: Session = Depends(get_db)
) -> QueuePerformanceResponse:
    """Queue throughput, comparing quoted waits with measured waits."""
    return QueuePerformanceResponse(**analytics_service.build_queue_performance(db))


@router.get("/language-breakdown", response_model=LanguageBreakdownResponse)
def get_language_breakdown(
    _admin: AdminUser, db: Session = Depends(get_db)
) -> LanguageBreakdownResponse:
    """Symptom reports per detected language — the multilingual coverage metric."""
    counts = analytics_service.build_language_breakdown(db)
    return LanguageBreakdownResponse(counts=counts, total=sum(counts.values()))


@router.get("/urgency-over-time", response_model=UrgencyOverTimeResponse)
def get_urgency_over_time(
    _admin: AdminUser,
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="Days back, inclusive of today."),
) -> UrgencyOverTimeResponse:
    """Cases per acuity per day.

    Computed from triage rows, NOT from the daily snapshot table: that table
    stores cumulative all-time totals, so charting it would draw three rising
    curves whatever the clinic actually did. Every day in the window is
    returned, zero-filled, so a renderer cannot interpolate across a gap.
    """
    return UrgencyOverTimeResponse(
        **analytics_service.build_urgency_over_time(db, days=days)
    )


@router.get("/throughput", response_model=ThroughputResponse)
def get_throughput(
    _admin: AdminUser,
    db: Session = Depends(get_db),
    days: int = Query(30, ge=1, le=365, description="Days back, inclusive of today."),
) -> ThroughputResponse:
    """Queue entries completed per day, measured on completion rather than arrival."""
    return ThroughputResponse(**analytics_service.build_throughput(db, days=days))


@router.get("/wait-by-urgency", response_model=WaitByUrgencyResponse)
def get_wait_by_urgency(
    _admin: AdminUser, db: Session = Depends(get_db)
) -> WaitByUrgencyResponse:
    """p50 and p90 wait per acuity.

    Percentiles rather than the mean the summary reports: a mean hides the
    tail, and the tail is where a long wait becomes a clinical problem.
    """
    return WaitByUrgencyResponse(**analytics_service.build_wait_by_urgency(db))


@router.get("/daily", response_model=PaginatedResponse[AnalyticsSnapshotResponse])
def get_daily_analytics(
    _admin: AdminUser,
    db: Session = Depends(get_db),
    page: PaginationParams = Depends(pagination),
) -> PaginatedResponse[AnalyticsSnapshotResponse]:
    """Stored daily snapshots, most recent first."""
    rows, total = analytics_service.list_snapshots(
        db, skip=page.offset, limit=page.limit
    )
    return PaginatedResponse[AnalyticsSnapshotResponse].build(
        [AnalyticsSnapshotResponse.model_validate(row) for row in rows],
        total=total,
        params=page,
    )


@router.post(
    "/daily/snapshot",
    response_model=AnalyticsSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
def save_daily_snapshot(
    _admin: AdminUser, db: Session = Depends(get_db)
) -> AnalyticsSnapshotResponse:
    """Record today's snapshot, replacing any snapshot already taken today."""
    return AnalyticsSnapshotResponse.model_validate(
        analytics_service.save_daily_snapshot(db)
    )


@router.delete("/daily/{snapshot_date}", status_code=status.HTTP_204_NO_CONTENT)
def delete_daily_snapshot(
    snapshot_date: date, _admin: AdminUser, db: Session = Depends(get_db)
) -> Response:
    """Delete one day's snapshot."""
    analytics_service.delete_snapshot(db, snapshot_date)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/daily", status_code=status.HTTP_204_NO_CONTENT)
def clear_analytics(
    _admin: AdminUser,
    db: Session = Depends(get_db),
    confirm: Annotated[
        str | None,
        Query(description="Must be the literal string CLEAR_ALL to proceed."),
    ] = None,
) -> Response:
    """Delete every stored snapshot. Disabled in production."""
    analytics_service.clear_all_snapshots(db, confirm)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
