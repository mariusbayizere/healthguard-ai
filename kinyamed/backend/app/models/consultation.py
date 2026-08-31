"""Clinician notes recorded against a queue entry."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.doctor import Doctor
    from app.models.queue import Queue


class Consultation(TimestampedModel):
    __tablename__ = "consultations"

    queue_entry_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("queue.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # one consultation per queue entry
        index=True,
    )
    # Clinical authorship must survive: Postgres refuses to delete a doctor who
    # has consultations on record.
    doctor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("doctors.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    notes: Mapped[str | None] = mapped_column(Text)
    diagnosis: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(String(100), index=True)

    queue_entry: Mapped["Queue"] = relationship(back_populates="consultation")
    doctor: Mapped["Doctor"] = relationship(back_populates="consultations")

    def __repr__(self) -> str:
        return f"<Consultation id={self.id} queue_entry_id={self.queue_entry_id}>"
