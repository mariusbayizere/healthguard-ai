"""Doctor business rules."""

from __future__ import annotations

from typing import Sequence

import structlog
from sqlalchemy.orm import Session

from app.core.exceptions import (
    DoctorEmailAlreadyExistsError,
    DoctorHasConsultationsError,
    DoctorNotFoundError,
)
from app.models.doctor import Doctor
from app.repositories import doctor_repository
from app.schemas.doctor import DoctorCreate, DoctorUpdate

logger = structlog.get_logger(__name__)


def get_doctor(db: Session, doctor_id: int) -> Doctor:
    """Return a clinician, or raise `DoctorNotFoundError`."""
    doctor = doctor_repository.get_by_id(db, doctor_id)
    if doctor is None:
        raise DoctorNotFoundError(doctor_id)
    return doctor


def list_doctors(
    db: Session, *, on_duty: bool | None, skip: int, limit: int
) -> tuple[Sequence[Doctor], int]:
    """Return a page of clinicians and the total matching the same filter."""
    return doctor_repository.list_doctors(db, on_duty=on_duty, skip=skip, limit=limit)


def list_on_duty(db: Session) -> Sequence[Doctor]:
    """Return every clinician currently available to take patients."""
    return doctor_repository.list_on_duty(db)


def create_doctor(db: Session, data: DoctorCreate) -> Doctor:
    """Register a clinician.

    The unique index on `email` is the real guard; this pre-check exists only to
    return a named error instead of a bare integrity violation.
    """
    if doctor_repository.email_taken(db, data.email):
        raise DoctorEmailAlreadyExistsError(data.email)
    doctor = doctor_repository.create(db, **data.model_dump())
    logger.info("doctor_registered", doctor_id=doctor.id)
    return doctor


def update_doctor(db: Session, doctor_id: int, data: DoctorUpdate) -> Doctor:
    """Apply only the fields the caller supplied, rejecting a taken email."""
    doctor = get_doctor(db, doctor_id)
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        return doctor
    if "email" in changes and doctor_repository.email_taken(
        db, changes["email"], exclude_id=doctor_id
    ):
        raise DoctorEmailAlreadyExistsError(changes["email"])
    doctor_repository.update(db, doctor, **changes)
    logger.info("doctor_updated", doctor_id=doctor_id, fields=sorted(changes))
    return doctor


def toggle_duty(db: Session, doctor_id: int) -> Doctor:
    """Flip a clinician's duty status."""
    doctor = get_doctor(db, doctor_id)
    doctor_repository.update(db, doctor, is_on_duty=not doctor.is_on_duty)
    logger.info("doctor_duty_toggled", doctor_id=doctor_id, is_on_duty=doctor.is_on_duty)
    return doctor


def delete_doctor(db: Session, doctor_id: int) -> None:
    """Delete a clinician who has no consultations on record.

    Consultations are clinical history and keep their author, so a doctor who
    has seen patients cannot be deleted — take them off duty instead.
    """
    doctor = get_doctor(db, doctor_id)
    consultations = doctor_repository.count_consultations(db, doctor_id)
    if consultations:
        raise DoctorHasConsultationsError(doctor_id, doctor.name, consultations)
    doctor_repository.delete(db, doctor)
    logger.warning("doctor_deleted", doctor_id=doctor_id)
