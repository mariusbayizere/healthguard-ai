"""Doctor business rules."""

from __future__ import annotations

from collections.abc import Sequence

import structlog
from sqlalchemy.orm import Session

from app.core.audit_context import AuditContext
from app.core.exceptions import (
    DoctorEmailAlreadyExistsError,
    DoctorHasConsultationsError,
    DoctorNotFoundError,
)
from app.models.doctor import Doctor
from app.repositories import doctor_repository
from app.schemas.doctor import DoctorCreate, DoctorUpdate
from app.services.audit import record, snapshot

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


def create_doctor(db: Session, data: DoctorCreate, *, audit: AuditContext) -> Doctor:
    """Register a clinician.

    The unique index on `email` is the real guard; this pre-check exists only to
    return a named error instead of a bare integrity violation.

    The insert and its audit row commit together: `commit=False` on the write,
    one `db.commit()` after the record. A clinician account that exists with no
    trace of who created it is the gap this closes.
    """
    if doctor_repository.email_taken(db, data.email):
        raise DoctorEmailAlreadyExistsError(data.email)
    doctor = doctor_repository.create(db, commit=False, **data.model_dump())
    record(
        db,
        action="CREATE_DOCTOR",
        table_name="doctors",
        record_id=doctor.id,
        after=snapshot(doctor),
        actor=audit.actor,
        ip_address=audit.ip_address,
        user_agent=audit.user_agent,
    )
    db.commit()
    db.refresh(doctor)
    logger.info("doctor_registered", doctor_id=doctor.id)
    return doctor


def update_doctor(
    db: Session, doctor_id: int, data: DoctorUpdate, *, audit: AuditContext
) -> Doctor:
    """Apply only the fields the caller supplied, rejecting a taken email."""
    doctor = get_doctor(db, doctor_id)
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        return doctor
    if "email" in changes and doctor_repository.email_taken(
        db, changes["email"], exclude_id=doctor_id
    ):
        raise DoctorEmailAlreadyExistsError(changes["email"])
    before = snapshot(doctor)
    doctor_repository.update(db, doctor, commit=False, **changes)
    record(
        db,
        action="UPDATE_DOCTOR",
        table_name="doctors",
        record_id=doctor_id,
        before=before,
        after=snapshot(doctor),
        actor=audit.actor,
        ip_address=audit.ip_address,
        user_agent=audit.user_agent,
    )
    db.commit()
    logger.info("doctor_updated", doctor_id=doctor_id, fields=sorted(changes))
    return doctor


def toggle_duty(db: Session, doctor_id: int, *, audit: AuditContext) -> Doctor:
    """Flip a clinician's duty status."""
    doctor = get_doctor(db, doctor_id)
    before = snapshot(doctor)
    doctor_repository.update(db, doctor, commit=False, is_on_duty=not doctor.is_on_duty)
    record(
        db,
        action="TOGGLE_DOCTOR_DUTY",
        table_name="doctors",
        record_id=doctor_id,
        before=before,
        after=snapshot(doctor),
        actor=audit.actor,
        ip_address=audit.ip_address,
        user_agent=audit.user_agent,
    )
    db.commit()
    logger.info(
        "doctor_duty_toggled", doctor_id=doctor_id, is_on_duty=doctor.is_on_duty
    )
    return doctor


def delete_doctor(db: Session, doctor_id: int, *, audit: AuditContext) -> None:
    """Delete a clinician who has no consultations on record.

    Consultations are clinical history and keep their author, so a doctor who
    has seen patients cannot be deleted — take them off duty instead.
    """
    doctor = get_doctor(db, doctor_id)
    consultations = doctor_repository.count_consultations(db, doctor_id)
    if consultations:
        raise DoctorHasConsultationsError(doctor_id, doctor.name, consultations)
    before = snapshot(doctor)
    doctor_repository.delete(db, doctor, commit=False)
    record(
        db,
        action="DELETE_DOCTOR",
        table_name="doctors",
        record_id=doctor_id,
        before=before,
        actor=audit.actor,
        ip_address=audit.ip_address,
        user_agent=audit.user_agent,
    )
    db.commit()
    logger.warning("doctor_deleted", doctor_id=doctor_id)
