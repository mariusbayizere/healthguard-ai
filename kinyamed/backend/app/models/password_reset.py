"""Six-digit password-reset codes (FR-05-12).

The row holds a bcrypt digest and never the code. The threat this addresses is
not an attacker guessing a code -- the window, the single use and the attempt
cap handle that -- but a READ of this table: a backup, a query log, a support
export. With plaintext codes any of those becomes account takeover for every
reset in flight.

Spent codes are kept rather than deleted, so "was a reset requested for this
account, and was it used" can be answered without the code ever having been
recoverable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.user import User


class PasswordResetCode(TimestampedModel):
    __tablename__ = "password_reset_codes"

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    user: Mapped[User] = relationship()

    @property
    def is_spent(self) -> bool:
        return self.consumed_at is not None

    def is_live(self, *, now: datetime | None = None) -> bool:
        """Unspent and inside its window."""
        moment = now or datetime.now(UTC)
        return not self.is_spent and self.expires_at > moment

    def __repr__(self) -> str:
        return (
            f"<PasswordResetCode user_id={self.user_id} "
            f"spent={self.is_spent} expires={self.expires_at.isoformat()}>"
        )
