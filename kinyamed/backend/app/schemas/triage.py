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


CLINICIAN_HINT_NOTICE = (
    "Urgency and confidence are a prioritisation hint for clinicians reviewing "
    "the queue. They are not advice for the patient."
)


class TriageResponse(BaseModel):
    triage_id: int
    patient_id: int
    patient_name: str
    # ── For clinicians only ────────────────────────────────────────────────
    urgency_level: UrgencyLevel = Field(
        description="Model prioritisation hint for clinicians. Never shown to patients."
    )
    confidence_score: float | None = Field(
        description="Uncalibrated softmax maximum (ECE 0.18). Not a probability."
    )
    requires_human_review: bool = Field(
        description="True when confidence is below MODEL_CONFIDENCE_THRESHOLD."
    )
    review_reason: str | None
    clinician_hint_notice: str = CLINICIAN_HINT_NOTICE
    # ── For the patient ────────────────────────────────────────────────────
    # The same receipt for every urgency: report received, queue place, and a
    # generic escalation line. See services/patient_message.py for why the
    # model's urgency is never turned into advice for the patient.
    patient_response: str
    patient_message_language: str
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
