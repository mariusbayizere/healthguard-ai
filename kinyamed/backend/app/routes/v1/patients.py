"""Patient endpoints. HTTP only — all rules live in `patient_service`."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import (
    AdminUser,
    CurrentUser,
    StaffUser,
    assert_may_act_for_patient,
)
from app.schemas.common import PaginatedResponse, PaginationParams, pagination
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate
from app.services import patient_service

router = APIRouter(prefix="/patients", tags=["Patients"])


@router.post("", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    data: PatientCreate, _staff: StaffUser, db: Session = Depends(get_db)
) -> PatientResponse:
    """Register a walk-in patient. Clinical staff only.

    Patients registering themselves use `POST /auth/register`, which creates
    the login and this record together.
    """
    return PatientResponse.model_validate(patient_service.create_patient(db, data))


@router.get("", response_model=PaginatedResponse[PatientResponse])
def list_patients(
    _staff: StaffUser,
    db: Session = Depends(get_db),
    page: PaginationParams = Depends(pagination),
    search: Annotated[
        str | None,
        Query(min_length=2, max_length=100, description="Match against name or phone."),
    ] = None,
) -> PaginatedResponse[PatientResponse]:
    """List patients, newest first. Always paginated."""
    patients, total = patient_service.list_patients(
        db, search=search, skip=page.offset, limit=page.limit
    )
    return PaginatedResponse[PatientResponse].build(
        [PatientResponse.model_validate(patient) for patient in patients],
        total=total,
        params=page,
    )


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: int, user: CurrentUser, db: Session = Depends(get_db)
) -> PatientResponse:
    """Fetch one patient. Staff may read any; a patient only their own."""
    assert_may_act_for_patient(user, patient_id)
    return PatientResponse.model_validate(patient_service.get_patient(db, patient_id))


@router.patch("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id: int,
    data: PatientUpdate,
    user: CurrentUser,
    db: Session = Depends(get_db),
) -> PatientResponse:
    """Update the supplied fields only. Staff, or the patient themselves."""
    assert_may_act_for_patient(user, patient_id)
    return PatientResponse.model_validate(
        patient_service.update_patient(db, patient_id, data)
    )


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id: int,
    _admin: AdminUser,
    db: Session = Depends(get_db),
    cascade: Annotated[
        bool,
        Query(description="Also delete this patient's clinical records. Irreversible."),
    ] = False,
) -> Response:
    """Delete a patient. Administrators only; refused if records exist."""
    patient_service.delete_patient(db, patient_id, cascade=cascade)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
