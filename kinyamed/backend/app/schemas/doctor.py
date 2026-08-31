"""Doctor request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.schemas.common import ORMModel

NameStr = Annotated[str, Field(min_length=2, max_length=100)]


class DoctorBase(BaseModel):
    name: NameStr
    email: Annotated[EmailStr, Field(max_length=255)]
    specialty: Annotated[str | None, Field(default=None, max_length=100)] = None
    is_on_duty: bool = True

    @field_validator("name", "specialty")
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class DoctorCreate(DoctorBase):
    """Payload for registering a clinician."""


class DoctorUpdate(BaseModel):
    """Partial update: only the supplied fields are changed."""

    name: NameStr | None = None
    email: Annotated[EmailStr | None, Field(default=None, max_length=255)] = None
    specialty: Annotated[str | None, Field(default=None, max_length=100)] = None
    is_on_duty: bool | None = None

    _strip_text = field_validator("name", "specialty")(DoctorBase._strip_text.__func__)

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str | None) -> str | None:
        return value.strip().lower() if value is not None else None


class DoctorResponse(ORMModel):
    id: int
    name: str
    email: str
    specialty: str | None
    is_on_duty: bool
    created_at: datetime
