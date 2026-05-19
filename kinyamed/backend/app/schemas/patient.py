from pydantic import BaseModel
from typing import Optional

class PatientCreate(BaseModel):
    name: str
    phone: str
    age: Optional[int] = None
    gender: Optional[str] = None
    location: Optional[str] = None

class PatientResponse(BaseModel):
    id: int
    name: str
    phone: str
    age: Optional[int]
    gender: Optional[str]
    location: Optional[str]

    class Config:
        from_attributes = True
