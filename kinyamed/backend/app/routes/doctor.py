from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.doctor import Doctor
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/doctors", tags=["Doctors"])

class DoctorCreate(BaseModel):
    name: str
    email: str
    specialty: Optional[str] = None

@router.post("/")
def create_doctor(data: DoctorCreate, db: Session = Depends(get_db)):
    doctor = Doctor(**data.model_dump())
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor

@router.get("/")
def get_doctors(db: Session = Depends(get_db)):
    return db.query(Doctor).all()

@router.get("/on-duty")
def get_on_duty_doctors(db: Session = Depends(get_db)):
    return db.query(Doctor).filter(Doctor.is_on_duty == True).all()
