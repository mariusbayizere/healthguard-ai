"""Per-doctor record that a CRITICAL alert reached a human.

Its own table, not a column on `queue`, and the reason is worth stating where
somebody will read it before deciding to "simplify" the schema:

    Acknowledgement means an alert reached a person. It does NOT mean the
    patient was assessed.

Folding it into `queue.status` would make "dismissed a popup" and "saw the
patient" the same fact, in the clinical record, in every audit built on it, and
in any retraining set that reads dispositions. The two would then be
indistinguishable for ever, because the information to separate them would
never have been written down.

Per doctor, because "seen by the doctor going off shift" is not "seen by the
doctor coming on".
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.queue import Queue
    from app.models.user import User


class QueueAlertAcknowledgement(TimestampedModel):
    __tablename__ = "queue_alert_acknowledgements"

    __table_args__ = (
        UniqueConstraint("queue_id", "user_id", name="uq_alert_ack_queue_user"),
    )

    queue_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("queue.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    acknowledged_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    queue_entry: Mapped[Queue] = relationship()
    user: Mapped[User] = relationship()

    def __repr__(self) -> str:
        return (
            f"<QueueAlertAcknowledgement queue_id={self.queue_id} "
            f"user_id={self.user_id}>"
        )
