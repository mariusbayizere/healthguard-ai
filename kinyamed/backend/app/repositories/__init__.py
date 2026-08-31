"""Data-access layer. Every query in the system lives here."""

from app.repositories.analytics_repo import AnalyticsRepository, analytics_repository
from app.repositories.base import BaseRepository
from app.repositories.doctor_repo import DoctorRepository, doctor_repository
from app.repositories.patient_repo import PatientRepository, patient_repository
from app.repositories.queue_repo import QueueRepository, queue_repository
from app.repositories.sms_repo import SMSLogRepository, sms_log_repository
from app.repositories.user_repo import (
    RefreshTokenRepository,
    UserRepository,
    refresh_token_repository,
    user_repository,
)
from app.repositories.triage_repo import (
    SymptomReportRepository,
    TriageRepository,
    symptom_report_repository,
    triage_repository,
)

__all__ = [
    "AnalyticsRepository",
    "BaseRepository",
    "DoctorRepository",
    "PatientRepository",
    "QueueRepository",
    "SMSLogRepository",
    "SymptomReportRepository",
    "RefreshTokenRepository",
    "TriageRepository",
    "UserRepository",
    "analytics_repository",
    "doctor_repository",
    "patient_repository",
    "queue_repository",
    "sms_log_repository",
    "symptom_report_repository",
    "refresh_token_repository",
    "triage_repository",
    "user_repository",
]
