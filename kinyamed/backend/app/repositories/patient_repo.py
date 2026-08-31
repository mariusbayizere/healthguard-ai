"""Patient data access."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.symptom_report import SymptomReport
from app.repositories.base import BaseRepository


class PatientRepository(BaseRepository[Patient]):
    def __init__(self) -> None:
        super().__init__(Patient)

    def search(
        self, db: Session, *, search: str | None = None, skip: int = 0, limit: int = 50
    ) -> tuple[Sequence[Patient], int]:
        """Return a page of patients and the total matching the same filter."""
        statement = select(Patient)
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(Patient.name.ilike(pattern), Patient.phone.ilike(pattern))
            )
        total = self._count_for(db, statement)
        rows = db.scalars(
            statement.order_by(Patient.created_at.desc(), Patient.id.desc())
            .offset(skip)
            .limit(limit)
        ).all()
        return rows, total

    def count_clinical_records(self, db: Session, patient_id: int) -> int:
        """Number of symptom reports held for a patient."""
        return int(
            db.scalar(
                select(func.count())
                .select_from(SymptomReport)
                .where(SymptomReport.patient_id == patient_id)
            )
            or 0
        )


patient_repository = PatientRepository()
