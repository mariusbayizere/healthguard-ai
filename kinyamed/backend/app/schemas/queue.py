from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class QueueItemResponse(BaseModel):
    queue_number: int
    queue_position: int
    patient_name: str
    patient_phone: str
    urgency_level: str
    symptoms: str
    status: str
    estimated_wait: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
