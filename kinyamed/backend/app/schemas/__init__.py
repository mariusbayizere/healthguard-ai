"""Pydantic request/response schemas."""

from app.schemas.analytics import (
    AnalyticsSnapshotResponse,
    LanguageBreakdownResponse,
    QueuePerformanceResponse,
    SummaryResponse,
    UrgencyBreakdownResponse,
    UrgencyCount,
)
from app.schemas.common import (
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    Message,
    ORMModel,
    PaginatedResponse,
    PaginationParams,
    ReadinessResponse,
    ServiceInfoResponse,
    pagination,
)
from app.schemas.doctor import DoctorCreate, DoctorResponse, DoctorUpdate
from app.schemas.patient import PatientCreate, PatientResponse, PatientUpdate
from app.schemas.queue import (
    QueueDoctorAssignment,
    QueueItemResponse,
    QueueStatusUpdate,
)
from app.schemas.triage import TriageRequest, TriageResponse

__all__ = [
    "AnalyticsSnapshotResponse",
    "DoctorCreate",
    "DoctorResponse",
    "DoctorUpdate",
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
    "LanguageBreakdownResponse",
    "Message",
    "ORMModel",
    "PaginatedResponse",
    "PaginationParams",
    "PatientCreate",
    "PatientResponse",
    "PatientUpdate",
    "QueueDoctorAssignment",
    "QueueItemResponse",
    "QueuePerformanceResponse",
    "QueueStatusUpdate",
    "ReadinessResponse",
    "ServiceInfoResponse",
    "SummaryResponse",
    "TriageRequest",
    "TriageResponse",
    "UrgencyBreakdownResponse",
    "UrgencyCount",
    "pagination",
]
