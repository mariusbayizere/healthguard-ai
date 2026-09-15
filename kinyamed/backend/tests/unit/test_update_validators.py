"""Characterisation of the partial-update validators shared with the base schemas.

PatientUpdate and DoctorUpdate reuse their base model's `_strip_text` through
`__func__`. The mypy backlog changed only how that line is typed; these tests pin
the behaviour so a later refactor into a shared validator cannot change it.
"""

from __future__ import annotations

import pytest
from app.schemas.doctor import DoctorUpdate
from app.schemas.patient import PatientUpdate
from pydantic import ValidationError


@pytest.mark.parametrize("field", ["name", "location"])
def test_patient_update_strips_and_rejects_blank(field: str) -> None:
    assert getattr(PatientUpdate(**{field: "  Uwase Aline  "}), field) == "Uwase Aline"
    with pytest.raises(ValidationError, match="must not be blank"):
        PatientUpdate(**{field: "   "})
    assert getattr(PatientUpdate(**{field: None}), field) is None


@pytest.mark.parametrize("field", ["name", "specialty"])
def test_doctor_update_strips_and_rejects_blank(field: str) -> None:
    assert getattr(DoctorUpdate(**{field: "  Paediatrics  "}), field) == "Paediatrics"
    with pytest.raises(ValidationError, match="must not be blank"):
        DoctorUpdate(**{field: "   "})
    assert getattr(DoctorUpdate(**{field: None}), field) is None


def test_fields_not_named_are_untouched() -> None:
    assert PatientUpdate().model_dump(exclude_unset=True) == {}
    assert DoctorUpdate().model_dump(exclude_unset=True) == {}
