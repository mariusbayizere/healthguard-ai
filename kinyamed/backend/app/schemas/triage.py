"""Triage request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, field_validator

from app.core.config import settings
from app.models.triage_result import UrgencyLevel


class TriageRequest(BaseModel):
    patient_id: Annotated[int, Field(gt=0)]
    symptoms_input: Annotated[
        str,
        Field(
            min_length=3,
            max_length=settings.MAX_SYMPTOM_LENGTH,
            examples=["Mfite umuriro mwinshi n'ububabare bw'umutwe"],
            description="The patient's own description of their symptoms.",
        ),
    ]

    @field_validator("symptoms_input")
    @classmethod
    def _strip_symptoms(cls, value: str) -> str:
        stripped = value.strip()
        if len(stripped) < 3:
            raise ValueError("symptoms_input must contain at least 3 characters")
        return stripped


class TriageResponse(BaseModel):
    triage_id: int
    patient_id: int
    patient_name: str
    urgency_level: UrgencyLevel
    possible_conditions: str | None
    confidence_score: float | None
    ai_response_rw: str | None
    language_detected: str | None
    queue_number: int
    queue_position: int = Field(description="1-based place in the live queue at the time of triage.")
    estimated_wait: int | None = Field(description="Minutes, as quoted to the patient by SMS.")
    created_at: datetime
