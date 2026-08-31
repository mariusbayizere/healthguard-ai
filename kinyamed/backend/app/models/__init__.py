"""ORM models.

Importing this package registers every mapper, which SQLAlchemy needs before
relationships can be resolved and which Alembic's autogenerate relies on.
"""

from app.models.analytics import Analytics
from app.models.base import TimestampedModel
from app.models.consultation import Consultation
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.queue import (
    ACTIVE_STATUSES,
    ALLOWED_STATUS_TRANSITIONS,
    Queue,
    QueueStatus,
)
from app.models.sms_log import SMSLog, SMSStatus
from app.models.symptom_report import SymptomReport
from app.models.triage_result import TriageResult, UrgencyLevel
from app.models.user import RefreshToken, User, UserRole

__all__ = [
    "ACTIVE_STATUSES",
    "ALLOWED_STATUS_TRANSITIONS",
    "Analytics",
    "Consultation",
    "Doctor",
    "Patient",
    "RefreshToken",
    "Queue",
    "QueueStatus",
    "SMSLog",
    "SMSStatus",
    "SymptomReport",
    "TimestampedModel",
    "TriageResult",
    "UrgencyLevel",
    "User",
    "UserRole",
]
