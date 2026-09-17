"""Patient business rules."""

from __future__ import annotations

from collections.abc import Sequence

import structlog
from sqlalchemy.orm import Session

from app.core.audit_context import AuditContext
from app.core.exceptions import PatientHasClinicalRecordsError, PatientNotFoundError
from app.models.patient import Patient
from app.repositories import patient_repository
from app.schemas.patient import PatientCreate, PatientUpdate
from app.services.audit import record, snapshot

logger = structlog.get_logger(__name__)


def get_patient(db: Session, patient_id: int) -> Patient:
    """Return a patient, or raise `PatientNotFoundError`."""
    patient = patient_repository.get_by_id(db, patient_id)
    if patient is None:
        raise PatientNotFoundError(patient_id)
    return patient


def list_patients(
    db: Session, *, search: str | None, skip: int, limit: int
) -> tuple[Sequence[Patient], int]:
    """Return a page of patients and the total matching the same filter."""
    return patient_repository.search(db, search=search, skip=skip, limit=limit)


def create_patient(db: Session, data: PatientCreate, *, audit: AuditContext) -> Patient:
    """Register a patient."""
    patient = patient_repository.create(db, commit=False, **data.model_dump())
    record(
        db,
        action="CREATE_PATIENT",
        table_name="patients",
        record_id=patient.id,
        after=snapshot(patient),
        actor=audit.actor,
        ip_address=audit.ip_address,
        user_agent=audit.user_agent,
    )
    db.commit()
    db.refresh(patient)
    logger.info("patient_registered", patient_id=patient.id)
    return patient


def update_patient(
    db: Session, patient_id: int, data: PatientUpdate, *, audit: AuditContext
) -> Patient:
    """Apply only the fields the caller supplied."""
    patient = get_patient(db, patient_id)
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        return patient
    before = snapshot(patient)
    patient_repository.update(db, patient, commit=False, **changes)
    record(
        db,
        action="UPDATE_PATIENT",
        table_name="patients",
        record_id=patient_id,
        before=before,
        after=snapshot(patient),
        actor=audit.actor,
        ip_address=audit.ip_address,
        user_agent=audit.user_agent,
    )
    db.commit()
    logger.info("patient_updated", patient_id=patient_id, fields=sorted(changes))
    return patient


def delete_patient(
    db: Session, patient_id: int, *, cascade: bool = False, audit: AuditContext
) -> None:
    """Delete a patient.

    Refused by default when clinical records exist: deleting a patient discards
    their symptom reports, triage results, queue history and SMS log. A caller
    that genuinely intends that must ask for it explicitly.
    """
    patient = get_patient(db, patient_id)
    if not cascade:
        records = patient_repository.count_clinical_records(db, patient_id)
        if records:
            raise PatientHasClinicalRecordsError(patient_id, records)
    before = snapshot(patient)
    patient_repository.delete(db, patient, commit=False)
    record(
        db,
        action="DELETE_PATIENT",
        table_name="patients",
        record_id=patient_id,
        before=before,
        actor=audit.actor,
        ip_address=audit.ip_address,
        user_agent=audit.user_agent,
    )
    db.commit()
    logger.warning("patient_deleted", patient_id=patient_id, cascade=cascade)
