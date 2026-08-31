"""Doctor endpoints. HTTP only — all rules live in `doctor_service`."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AdminUser, StaffUser
from app.schemas.common import PaginatedResponse, PaginationParams, pagination
from app.schemas.doctor import DoctorCreate, DoctorResponse, DoctorUpdate
from app.services import doctor_service

router = APIRouter(prefix="/doctors", tags=["Doctors"])


@router.post("", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
def create_doctor(
    data: DoctorCreate, _admin: AdminUser, db: Session = Depends(get_db)
) -> DoctorResponse:
    """Register a clinician. Administrators only."""
    return DoctorResponse.model_validate(doctor_service.create_doctor(db, data))


@router.get("", response_model=PaginatedResponse[DoctorResponse])
def list_doctors(
    _staff: StaffUser,
    db: Session = Depends(get_db),
    page: PaginationParams = Depends(pagination),
    on_duty: Annotated[
        bool | None, Query(description="Filter by duty status; omit for all doctors.")
    ] = None,
) -> PaginatedResponse[DoctorResponse]:
    """List clinicians, optionally filtered by duty status."""
    doctors, total = doctor_service.list_doctors(
        db, on_duty=on_duty, skip=page.offset, limit=page.limit
    )
    return PaginatedResponse[DoctorResponse].build(
        [DoctorResponse.model_validate(doctor) for doctor in doctors],
        total=total,
        params=page,
    )


# Declared before /{doctor_id} so the literal path is not captured as an id.
@router.get("/on-duty", response_model=list[DoctorResponse])
def get_on_duty_doctors(
    _staff: StaffUser, db: Session = Depends(get_db)
) -> list[DoctorResponse]:
    """List clinicians currently available to take patients."""
    return [
        DoctorResponse.model_validate(doctor) for doctor in doctor_service.list_on_duty(db)
    ]


@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(
    doctor_id: int, _staff: StaffUser, db: Session = Depends(get_db)
) -> DoctorResponse:
    """Fetch one clinician."""
    return DoctorResponse.model_validate(doctor_service.get_doctor(db, doctor_id))


@router.patch("/{doctor_id}", response_model=DoctorResponse)
def update_doctor(
    doctor_id: int, data: DoctorUpdate, _admin: AdminUser, db: Session = Depends(get_db)
) -> DoctorResponse:
    """Update the supplied fields only. Administrators only."""
    return DoctorResponse.model_validate(doctor_service.update_doctor(db, doctor_id, data))


@router.patch("/{doctor_id}/toggle-duty", response_model=DoctorResponse)
def toggle_duty(
    doctor_id: int, _staff: StaffUser, db: Session = Depends(get_db)
) -> DoctorResponse:
    """Flip a clinician's duty status. Clinical staff only."""
    return DoctorResponse.model_validate(doctor_service.toggle_duty(db, doctor_id))


@router.delete("/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doctor(
    doctor_id: int, _admin: AdminUser, db: Session = Depends(get_db)
) -> Response:
    """Delete a clinician who has no consultations. Administrators only."""
    doctor_service.delete_doctor(db, doctor_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
