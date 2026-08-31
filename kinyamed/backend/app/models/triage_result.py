"""AI triage outcomes for a symptom report."""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.queue import Queue
    from app.models.symptom_report import SymptomReport


class UrgencyLevel(enum.Enum):
    """Triage acuity, most urgent first.

    `priority` is the queue sort key; lower sorts earlier. It lives here so the
    ordering rule has exactly one definition.
    """

    CRITICAL = "CRITICAL"
    URGENT = "URGENT"
    ROUTINE = "ROUTINE"

    @property
    def priority(self) -> int:
        return _URGENCY_PRIORITY[self]


_URGENCY_PRIORITY: dict[UrgencyLevel, int] = {
    UrgencyLevel.CRITICAL: 1,
    UrgencyLevel.URGENT: 2,
    UrgencyLevel.ROUTINE: 3,
}


class TriageResult(TimestampedModel):
    __tablename__ = "triage_results"
    __table_args__ = (
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_triage_results_confidence_range",
        ),
    )

    symptom_report_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("symptom_reports.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # one triage result per report; enforced, not assumed
        index=True,
    )
    urgency_level: Mapped[UrgencyLevel] = mapped_column(
        SAEnum(UrgencyLevel, name="urgencylevel", validate_strings=True),
        nullable=False,
        index=True,
    )
    possible_conditions: Mapped[str | None] = mapped_column(Text)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    ai_response_rw: Mapped[str | None] = mapped_column(Text)

    symptom_report: Mapped["SymptomReport"] = relationship(back_populates="triage_result")
    queue_entry: Mapped["Queue | None"] = relationship(
        back_populates="triage_result",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<TriageResult id={self.id} urgency={self.urgency_level.value}>"
