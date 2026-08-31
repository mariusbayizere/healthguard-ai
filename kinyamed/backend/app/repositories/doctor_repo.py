"""Doctor data access."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.consultation import Consultation
from app.models.doctor import Doctor
from app.repositories.base import BaseRepository


class DoctorRepository(BaseRepository[Doctor]):
    def __init__(self) -> None:
        super().__init__(Doctor)

    def get_by_email(self, db: Session, email: str) -> Doctor | None:
        """Return the clinician registered under this email, or None."""
        return db.scalars(select(Doctor).where(Doctor.email == email)).one_or_none()

    def email_taken(self, db: Session, email: str, *, exclude_id: int | None = None) -> bool:
        """Whether another doctor already holds this email."""
        statement = select(Doctor.id).where(Doctor.email == email)
        if exclude_id is not None:
            statement = statement.where(Doctor.id != exclude_id)
        return db.scalar(statement) is not None

    def list_doctors(
        self, db: Session, *, on_duty: bool | None = None, skip: int = 0, limit: int = 50
    ) -> tuple[Sequence[Doctor], int]:
        """Return a page of clinicians and the total matching the same filter."""
        statement = select(Doctor)
        if on_duty is not None:
            statement = statement.where(Doctor.is_on_duty.is_(on_duty))
        total = self._count_for(db, statement)
        rows = db.scalars(
            statement.order_by(Doctor.name.asc()).offset(skip).limit(limit)
        ).all()
        return rows, total

    def list_on_duty(self, db: Session) -> Sequence[Doctor]:
        """Return every clinician currently on duty, by name."""
        return db.scalars(
            select(Doctor).where(Doctor.is_on_duty.is_(True)).order_by(Doctor.name.asc())
        ).all()

    def count_on_duty(self, db: Session) -> int:
        """Count clinicians available to take patients; drives wait estimates."""
        return int(
            db.scalar(
                select(func.count()).select_from(Doctor).where(Doctor.is_on_duty.is_(True))
            )
            or 0
        )

    def count_consultations(self, db: Session, doctor_id: int) -> int:
        """Count consultations authored by a clinician."""
        return int(
            db.scalar(
                select(func.count())
                .select_from(Consultation)
                .where(Consultation.doctor_id == doctor_id)
            )
            or 0
        )


doctor_repository = DoctorRepository()
