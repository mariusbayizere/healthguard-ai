"""Patient records."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.sms_log import SMSLog
    from app.models.symptom_report import SymptomReport


class Patient(TimestampedModel):
    __tablename__ = "patients"
    __table_args__ = (
        CheckConstraint("age IS NULL OR (age >= 0 AND age <= 130)", name="ck_patients_age_range"),
        CheckConstraint("length(btrim(name)) > 0", name="ck_patients_name_not_blank"),
        CheckConstraint("length(btrim(phone)) > 0", name="ck_patients_phone_not_blank"),
    )

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Deliberately not unique: shared household handsets are common in the
    # communities this service targets, so two patients may share a number.
    # Indexed because phone is how staff look a patient up.
    phone: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    age: Mapped[int | None] = mapped_column(Integer)
    gender: Mapped[str | None] = mapped_column(String(10))
    location: Mapped[str | None] = mapped_column(String(100), index=True)

    symptom_reports: Mapped[list["SymptomReport"]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    sms_logs: Mapped[list["SMSLog"]] = relationship(
        back_populates="patient",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Patient id={self.id} name={self.name!r}>"
