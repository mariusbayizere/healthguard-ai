from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.database import create_tables
from app.routes import (
    patient_router, triage_router,
    queue_router, doctor_router, analytics_router
)

app = FastAPI(
    title="KinyaMed API",
    description="AI-Powered Medical Triage for Kinyarwanda speakers",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

create_tables()

app.include_router(patient_router,   prefix="/api/v1")
app.include_router(triage_router,    prefix="/api/v1")
app.include_router(queue_router,     prefix="/api/v1")
app.include_router(doctor_router,    prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")

@app.get("/")
def root():
    return {"status": "KinyaMed API is running"}

@app.get("/health")
def health():
    return {"status": "healthy", "module": "KinyaMed"}
