"""Daily analytics snapshots.

One row per calendar day; re-running a snapshot updates that day's row rather
than appending a duplicate.
"""

from __future__ import annotations

from datetime import date as date_type

from sqlalchemy import CheckConstraint, Date, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import TimestampedModel


class Analytics(TimestampedModel):
    __tablename__ = "analytics"
    __table_args__ = (
        CheckConstraint("avg_wait_time_mins >= 0", name="ck_analytics_avg_wait_non_negative"),
    )

    snapshot_date: Mapped[date_type] = mapped_column(
        Date, nullable=False, unique=True, index=True
    )
    total_patients: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    total_triaged: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    critical_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    urgent_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    routine_cases: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    avg_wait_time_mins: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0, server_default="0"
    )
    top_symptom: Mapped[str | None] = mapped_column(String(100))

    def __repr__(self) -> str:
        return f"<Analytics date={self.snapshot_date} triaged={self.total_triaged}>"
