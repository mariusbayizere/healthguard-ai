"""Clinician records."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.consultation import Consultation
    from app.models.queue import Queue


class Doctor(TimestampedModel):
    __tablename__ = "doctors"
    __table_args__ = (
        CheckConstraint("length(btrim(name)) > 0", name="ck_doctors_name_not_blank"),
        CheckConstraint("position('@' in email) > 1", name="ck_doctors_email_shape"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    specialty: Mapped[str | None] = mapped_column(String(100))
    is_on_duty: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )

    # A doctor is unassigned from the queue on delete (ON DELETE SET NULL),
    # never taking waiting patients with them.
    queue_entries: Mapped[list["Queue"]] = relationship(
        back_populates="doctor", passive_deletes=True
    )
    # Consultations are clinical history: the database refuses to delete a
    # doctor who has any (ON DELETE RESTRICT).
    consultations: Mapped[list["Consultation"]] = relationship(
        back_populates="doctor", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Doctor id={self.id} name={self.name!r} on_duty={self.is_on_duty}>"
