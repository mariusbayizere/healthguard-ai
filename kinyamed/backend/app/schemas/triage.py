from pydantic import BaseModel
from typing import Optional

class TriageRequest(BaseModel):
    patient_id: int
    symptoms_input: str

class TriageResponse(BaseModel):
    patient_id: int
    patient_name: str
    urgency_level: str
    possible_conditions: Optional[str]
    confidence_score: Optional[float]
    ai_response_rw: Optional[str]
    queue_number: int
    estimated_wait: Optional[int]
