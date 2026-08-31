"""Queue request/response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field

from app.models.queue import QueueStatus
from app.models.triage_result import UrgencyLevel


class QueueItemResponse(BaseModel):
    id: int
    queue_number: int
    queue_position: int = Field(
        description="1-based place in the live queue, recomputed on every read."
    )
    patient_id: int
    patient_name: str
    patient_phone: str
    urgency_level: UrgencyLevel
    symptoms: str
    language_detected: str | None
    status: QueueStatus
    estimated_wait: int | None = Field(
        description="Minutes still expected, recomputed from the current position."
    )
    quoted_wait_at_intake: int | None = Field(
        description="Minutes quoted to the patient by SMS when they were registered."
    )
    waiting_minutes: int = Field(description="Minutes elapsed since the patient joined the queue.")
    doctor_id: int | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class QueueStatusUpdate(BaseModel):
    status: QueueStatus = Field(description="Target status; only legal transitions are accepted.")


class QueueDoctorAssignment(BaseModel):
    doctor_id: Annotated[int, Field(gt=0)]
