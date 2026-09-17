"""Immutable record of every state-changing operation (FR-03-09).

An audit row answers "who changed what, when, from what to what" after the
fact, when the structured logs have rotated away and the row itself has been
changed again. It is written inside the transaction of the change it records,
so the two land together or neither does.

PRIVACY (L11). `before_value` and `after_value` are scrubbed before they are
written: a personal name is redacted and a phone is masked, whatever key it
arrived under. Permanent storage is a worse place for a leak than a rotating
log, because it outlives the retention policy that would have cleared it. The
actor's own name is the single exception, kept in its own column because
"who did this" is the point of the table.

The rows are append-only by intent. Nothing in the service layer updates or
deletes one, and a migration that changes that should be argued for first.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.user import User


class AuditLog(TimestampedModel):
    __tablename__ = "audit_logs"

    __table_args__ = (
        # The two documented lookup paths: "what happened to this record" and
        # "what did this person do".
        Index("ix_audit_logs_target", "table_name", "record_id"),
        Index("ix_audit_logs_actor", "user_id", "created_at"),
    )

    # Nullable, and SET NULL rather than CASCADE on purpose: an anonymous
    # triage has no actor, and deleting a user must not erase the evidence of
    # what they did.
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL")
    )
    # Denormalised so the row still says who acted after the account is gone.
    user_name: Mapped[str | None] = mapped_column(String(200))
    user_role: Mapped[str | None] = mapped_column(String(32))

    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    table_name: Mapped[str] = mapped_column(String(64), nullable=False)
    record_id: Mapped[int | None] = mapped_column(Integer)

    before_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    after_value: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    ip_address: Mapped[str | None] = mapped_column(String(45))  # INET6 length
    user_agent: Mapped[str | None] = mapped_column(Text)

    user: Mapped[User | None] = relationship()

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} action={self.action} "
            f"{self.table_name}#{self.record_id} by={self.user_id}>"
        )
