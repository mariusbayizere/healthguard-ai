"""The live patient queue.

Ordering rule: strictly by clinical priority, then by arrival time. A patient's
*position* is therefore derived from that ordering at read time (see
`app.services.queue_service`) rather than stored, so it can never drift from
reality when entries are added, completed or removed.
"""

from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Sequence,
    SmallInteger,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.consultation import Consultation
    from app.models.doctor import Doctor
    from app.models.triage_result import TriageResult


class QueueStatus(enum.Enum):
    WAITING = "WAITING"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    CANCELLED = "CANCELLED"


# Transitions the queue is allowed to make. Anything else is rejected, so a
# completed consultation cannot be pushed back into the waiting room.
ALLOWED_STATUS_TRANSITIONS: dict[QueueStatus, frozenset[QueueStatus]] = {
    QueueStatus.WAITING: frozenset({QueueStatus.IN_PROGRESS, QueueStatus.CANCELLED}),
    QueueStatus.IN_PROGRESS: frozenset({QueueStatus.DONE, QueueStatus.WAITING, QueueStatus.CANCELLED}),
    QueueStatus.DONE: frozenset(),
    QueueStatus.CANCELLED: frozenset(),
}

# Statuses that still occupy a place in the waiting room.
ACTIVE_STATUSES: frozenset[QueueStatus] = frozenset(
    {QueueStatus.WAITING, QueueStatus.IN_PROGRESS}
)

# Postgres allocates ticket numbers, so concurrent intakes cannot collide and
# numbers are not reused after a deletion.
queue_number_seq = Sequence("queue_number_seq", start=1, increment=1)


class Queue(TimestampedModel):
    __tablename__ = "queue"
    __table_args__ = (
        CheckConstraint("priority >= 1 AND priority <= 3", name="ck_queue_priority_range"),
        CheckConstraint(
            "estimated_wait IS NULL OR estimated_wait >= 0", name="ck_queue_estimated_wait_non_negative"
        ),
        # Covers the live-queue read: filter on status, order by priority then arrival.
        Index("ix_queue_live_order", "status", "priority", "created_at"),
        Index("ix_queue_completed_at", "completed_at"),
    )

    triage_result_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("triage_results.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # a triage result enters the queue exactly once
        index=True,
    )
    doctor_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("doctors.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    queue_number: Mapped[int] = mapped_column(
        Integer,
        queue_number_seq,
        server_default=queue_number_seq.next_value(),
        nullable=False,
        unique=True,
    )
    # Denormalised copy of `triage_result.urgency_level.priority` so the queue
    # can be ordered without joining, and indexed for the live-queue read.
    priority: Mapped[int] = mapped_column(SmallInteger, nullable=False, index=True)
    status: Mapped[QueueStatus] = mapped_column(
        SAEnum(QueueStatus, name="queuestatus", validate_strings=True),
        nullable=False,
        default=QueueStatus.WAITING,
        server_default=QueueStatus.WAITING.value,
        index=True,
    )
    # Wait quoted to the patient at intake, in minutes. Kept as written so the
    # SMS we sent stays auditable; the live estimate is recomputed on read.
    estimated_wait: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    triage_result: Mapped["TriageResult"] = relationship(back_populates="queue_entry")
    doctor: Mapped["Doctor | None"] = relationship(back_populates="queue_entries")
    consultation: Mapped["Consultation | None"] = relationship(
        back_populates="queue_entry",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    @property
    def is_active(self) -> bool:
        return self.status in ACTIVE_STATUSES

    def __repr__(self) -> str:
        return f"<Queue id={self.id} number={self.queue_number} status={self.status.value}>"
