"""Raw symptom submissions from patients."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import TimestampedModel

if TYPE_CHECKING:
    from app.models.patient import Patient
    from app.models.triage_result import TriageResult


class SymptomReport(TimestampedModel):
    __tablename__ = "symptom_reports"

    patient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("patients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_input: Mapped[str] = mapped_column(Text, nullable=False)
    language_detected: Mapped[str | None] = mapped_column(String(20), index=True)
    symptoms_extracted: Mapped[str | None] = mapped_column(Text)

    patient: Mapped["Patient"] = relationship(back_populates="symptom_reports")
    triage_result: Mapped["TriageResult | None"] = relationship(
        back_populates="symptom_report",
        uselist=False,
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<SymptomReport id={self.id} patient_id={self.patient_id}>"
