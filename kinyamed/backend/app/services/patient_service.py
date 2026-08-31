"""Patient business rules."""

from __future__ import annotations

from typing import Sequence

import structlog
from sqlalchemy.orm import Session

from app.core.exceptions import PatientHasClinicalRecordsError, PatientNotFoundError
from app.models.patient import Patient
from app.repositories import patient_repository
from app.schemas.patient import PatientCreate, PatientUpdate

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


def create_patient(db: Session, data: PatientCreate) -> Patient:
    """Register a patient."""
    patient = patient_repository.create(db, **data.model_dump())
    logger.info("patient_registered", patient_id=patient.id)
    return patient


def update_patient(db: Session, patient_id: int, data: PatientUpdate) -> Patient:
    """Apply only the fields the caller supplied."""
    patient = get_patient(db, patient_id)
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        return patient
    patient_repository.update(db, patient, **changes)
    logger.info("patient_updated", patient_id=patient_id, fields=sorted(changes))
    return patient


def delete_patient(db: Session, patient_id: int, *, cascade: bool = False) -> None:
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
    patient_repository.delete(db, patient)
    logger.warning("patient_deleted", patient_id=patient_id, cascade=cascade)
