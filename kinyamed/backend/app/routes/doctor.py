from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.core.database import get_db
from app.models.doctor import Doctor
from pydantic import BaseModel

router = APIRouter(prefix="/doctors", tags=["Doctors"])

class DoctorCreate(BaseModel):
    name: str
    email: str
    specialty: Optional[str] = None
    is_on_duty: Optional[bool] = True

class DoctorResponse(BaseModel):
    id: int
    name: str
    email: str
    specialty: Optional[str]
    is_on_duty: bool

    class Config:
        from_attributes = True

# CREATE
@router.post("/", response_model=DoctorResponse)
def create_doctor(data: DoctorCreate, db: Session = Depends(get_db)):
    existing = db.query(Doctor).filter(Doctor.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    doctor = Doctor(**data.model_dump())
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor

# GET ALL
@router.get("/", response_model=List[DoctorResponse])
def get_all_doctors(db: Session = Depends(get_db)):
    return db.query(Doctor).all()

# GET ON DUTY
@router.get("/on-duty", response_model=List[DoctorResponse])
def get_on_duty_doctors(db: Session = Depends(get_db)):
    return db.query(Doctor).filter(Doctor.is_on_duty == True).all()

# GET ONE
@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return doctor

# UPDATE
@router.put("/{doctor_id}", response_model=DoctorResponse)
def update_doctor(doctor_id: int, data: DoctorCreate, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    for key, value in data.model_dump().items():
        setattr(doctor, key, value)
    db.commit()
    db.refresh(doctor)
    return doctor

# TOGGLE DUTY STATUS
@router.patch("/{doctor_id}/toggle-duty")
def toggle_duty(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    doctor.is_on_duty = not doctor.is_on_duty
    db.commit()
    db.refresh(doctor)
    status = "on duty" if doctor.is_on_duty else "off duty"
    return {"message": f"Dr. {doctor.name} is now {status}"}

# DELETE
@router.delete("/{doctor_id}")
def delete_doctor(doctor_id: int, db: Session = Depends(get_db)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    db.delete(doctor)
    db.commit()
    return {"message": f"Doctor {doctor_id} deleted successfully"}
