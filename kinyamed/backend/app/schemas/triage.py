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
    # Below MODEL_CONFIDENCE_THRESHOLD a clinician must review the urgency.
    requires_human_review: bool
    review_reason: str | None
    ai_response_rw: str | None
    # C1. The patient-facing sentence, and an explicit statement of whether one
    # exists. `response_pending=True` means no speaker has authored a template
    # for this language and urgency yet; `patient_response` is then empty and
    # MUST NOT be shown to a patient. It is not filled with a machine draft,
    # because a sentence telling someone to go to hospital now is the text this
    # project does not machine-draft. See services/response_templates.py.
    patient_response: str | None = None
    response_pending: bool = True
    response_pending_reason: str | None = None
    language_detected: str | None
    # The queue entry's own primary key, distinct from queue_number (which is
    # the human-facing ticket). Returned so a client can address
    # /queue/{id}/status and /queue/{id}/assign-doctor for the row it just
    # created, without a second fetch to discover it.
    queue_id: int
    queue_number: int
    queue_position: int = Field(
        description="1-based place in the live queue at the time of triage."
    )
    estimated_wait: int | None = Field(
        description="Minutes, as quoted to the patient by SMS."
    )
    created_at: datetime
