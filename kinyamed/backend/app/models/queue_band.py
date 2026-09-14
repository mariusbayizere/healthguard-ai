"""The four bands the live queue is ordered by, and the one rule that assigns them.

    1. CRITICAL      the model predicted CRITICAL, at any confidence
    2. NEEDS_REVIEW  the model's confidence is below the review threshold
    3. URGENT
    4. ROUTINE

Arrival order within each band.

WHY NEEDS REVIEW SITS ABOVE URGENT. A flagged case is one the model could not
classify with confidence. Sorting it by the class it could not confidently
assign is circular: measured with v2d, "sinshobora guhumeka" ("I can't
breathe") came back ROUTINE at 0.598 and sank below every confident case.

WHY A LOW-CONFIDENCE CRITICAL STAYS CRITICAL. Moving it into NEEDS REVIEW would
demote a CRITICAL prediction below other CRITICAL cases. A flag may only ever
move a case up. The flag is still reported on the entry.

The same rule exists twice, in Python (`band_for`) and as SQL (`band_sql`), so
the database can order and count by it. Tests check they agree on every
combination and on random queues.
"""

from __future__ import annotations

import enum

from sqlalchemy import ColumnElement, case, or_

from app.models.queue import Queue
from app.models.triage_result import TriageResult, UrgencyLevel


class QueueBand(enum.IntEnum):
    """Lower sorts earlier."""

    CRITICAL = 1
    NEEDS_REVIEW = 2
    URGENT = 3
    ROUTINE = 4

    @property
    def label(self) -> str:
        return BAND_LABELS[self]


BAND_LABELS: dict[QueueBand, str] = {
    QueueBand.CRITICAL: "Critical",
    QueueBand.NEEDS_REVIEW: "Model could not classify — review these first",
    QueueBand.URGENT: "Urgent",
    QueueBand.ROUTINE: "Routine",
}


def band_for(urgency: UrgencyLevel, *, requires_review: bool) -> QueueBand:
    if urgency is UrgencyLevel.CRITICAL:
        return QueueBand.CRITICAL
    if requires_review:
        return QueueBand.NEEDS_REVIEW
    return QueueBand.URGENT if urgency is UrgencyLevel.URGENT else QueueBand.ROUTINE


def band_sql(threshold: float) -> ColumnElement[int]:
    """`band_for` as a SQL expression. The statement must join TriageResult.

    Mirrors `app.services.review.needs_review`: NULL confidence or below threshold.
    """
    flagged = or_(
        TriageResult.confidence_score.is_(None),
        TriageResult.confidence_score < threshold,
    )
    return case(
        (Queue.priority == UrgencyLevel.CRITICAL.priority, int(QueueBand.CRITICAL)),
        (flagged, int(QueueBand.NEEDS_REVIEW)),
        (Queue.priority == UrgencyLevel.URGENT.priority, int(QueueBand.URGENT)),
        else_=int(QueueBand.ROUTINE),
    )
