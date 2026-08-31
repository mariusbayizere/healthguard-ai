"""Patient request/response schemas."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from app.schemas.common import ORMModel

# Rwandan mobile numbers are 9 digits beginning 7[2389]; accept the local
# (07…), national (2507…) and E.164 (+2507…) spellings and store one form.
_RW_MOBILE = re.compile(r"^(?:\+?250|0)?(7[2389]\d{7})$")
_E164 = re.compile(r"^\+[1-9]\d{7,14}$")

Gender = Literal["male", "female", "other", "unknown"]

NameStr = Annotated[str, Field(min_length=2, max_length=100)]


def normalise_phone(value: str) -> str:
    """Return `value` in E.164 form, raising if it is not a usable number."""
    candidate = re.sub(r"[\s\-().]", "", value.strip())
    rwandan = _RW_MOBILE.match(candidate)
    if rwandan:
        return f"+250{rwandan.group(1)}"
    if _E164.match(candidate):
        return candidate
    raise ValueError(
        "phone must be a Rwandan mobile number (e.g. 0788123456) "
        "or an international number in E.164 form (e.g. +14155550123)"
    )


class PatientBase(BaseModel):
    name: NameStr
    phone: Annotated[str, Field(max_length=20, examples=["0788123456"])]
    age: Annotated[int | None, Field(default=None, ge=0, le=130)] = None
    gender: Gender | None = None
    location: Annotated[str | None, Field(default=None, max_length=100)] = None

    @field_validator("name", "location")
    @classmethod
    def _strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be blank")
        return stripped

    @field_validator("phone")
    @classmethod
    def _normalise_phone(cls, value: str) -> str:
        return normalise_phone(value)

    @field_validator("gender", mode="before")
    @classmethod
    def _lowercase_gender(cls, value: object) -> object:
        return value.lower().strip() if isinstance(value, str) else value


class PatientCreate(PatientBase):
    """Payload for registering a patient."""


class PatientUpdate(BaseModel):
    """Partial update: only the supplied fields are changed."""

    name: NameStr | None = None
    phone: Annotated[str | None, Field(default=None, max_length=20)] = None
    age: Annotated[int | None, Field(default=None, ge=0, le=130)] = None
    gender: Gender | None = None
    location: Annotated[str | None, Field(default=None, max_length=100)] = None

    _strip_text = field_validator("name", "location")(PatientBase._strip_text.__func__)

    @field_validator("phone")
    @classmethod
    def _normalise_phone(cls, value: str | None) -> str | None:
        return normalise_phone(value) if value is not None else None

    @field_validator("gender", mode="before")
    @classmethod
    def _lowercase_gender(cls, value: object) -> object:
        return value.lower().strip() if isinstance(value, str) else value


class PatientResponse(ORMModel):
    id: int
    name: str
    phone: str
    age: int | None
    gender: str | None
    location: str | None
    created_at: datetime
