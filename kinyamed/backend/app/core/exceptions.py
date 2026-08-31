"""Exception hierarchy for HealthGuard AI.

Every failure the system can anticipate has a named type carrying a stable
machine-readable `code`. Services raise these instead of `HTTPException`, which
keeps the domain layer independent of the web framework and gives clients a
contract they can branch on without parsing prose.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

logger = structlog.get_logger(__name__)


class HealthGuardBaseError(Exception):
    """Base exception for all HealthGuard AI errors."""

    # HTTP status used when this error reaches the API boundary.
    status_code: int = status.HTTP_400_BAD_REQUEST

    def __init__(
        self, message: str, code: str, *, details: dict[str, Any] | None = None
    ) -> None:
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(message)


# ── Generic ───────────────────────────────────────────────────────────────
class NotFoundError(HealthGuardBaseError):
    """A referenced record does not exist."""

    status_code = status.HTTP_404_NOT_FOUND

    def __init__(self, resource: str, identifier: Any) -> None:
        super().__init__(
            message=f"{resource} with ID {identifier} not found",
            code="NOT_FOUND",
            details={"resource": resource, "id": str(identifier)},
        )


class ConflictError(HealthGuardBaseError):
    """The request conflicts with the current state of a record."""

    status_code = status.HTTP_409_CONFLICT

    def __init__(self, message: str, code: str = "CONFLICT", **details: Any) -> None:
        super().__init__(message=message, code=code, details=details)


class ValidationError(HealthGuardBaseError):
    """The request is well-formed but semantically invalid."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT

    def __init__(self, message: str, code: str = "VALIDATION_ERROR", **details: Any) -> None:
        super().__init__(message=message, code=code, details=details)


# ── Patient ───────────────────────────────────────────────────────────────
class PatientNotFoundError(NotFoundError):
    def __init__(self, patient_id: int) -> None:
        super().__init__("Patient", patient_id)
        self.code = "PATIENT_NOT_FOUND"


class PatientHasClinicalRecordsError(ConflictError):
    def __init__(self, patient_id: int, record_count: int) -> None:
        super().__init__(
            message=(
                f"Patient {patient_id} has {record_count} clinical record(s). "
                "Retry with ?cascade=true to delete the patient and those records."
            ),
            code="PATIENT_HAS_CLINICAL_RECORDS",
            patient_id=patient_id,
            symptom_reports=record_count,
        )


# ── Triage / ML ───────────────────────────────────────────────────────────
class TriageServiceError(HealthGuardBaseError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, detail: str) -> None:
        super().__init__(f"Triage service error: {detail}", code="TRIAGE_ERROR")


class TriageResultNotFoundError(NotFoundError):
    def __init__(self, triage_id: int) -> None:
        super().__init__("Triage result", triage_id)
        self.code = "TRIAGE_NOT_FOUND"


class MLModelNotLoadedError(HealthGuardBaseError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    def __init__(self) -> None:
        super().__init__(
            "ML model is not loaded. Run the training pipeline first.",
            code="MODEL_NOT_LOADED",
        )


class MLInferenceError(HealthGuardBaseError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, detail: str) -> None:
        super().__init__(f"ML inference failed: {detail}", code="INFERENCE_ERROR")


class LowConfidenceError(HealthGuardBaseError):
    """Raised when the model is too unsure to be trusted with a triage decision."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT

    def __init__(self, confidence: float, threshold: float) -> None:
        super().__init__(
            f"Model confidence {confidence:.2f} is below threshold {threshold:.2f}",
            code="LOW_CONFIDENCE",
            details={"confidence": confidence, "threshold": threshold},
        )


# ── Queue ─────────────────────────────────────────────────────────────────
class QueueEntryNotFoundError(NotFoundError):
    def __init__(self, queue_id: int) -> None:
        super().__init__("Queue entry", queue_id)
        self.code = "QUEUE_NOT_FOUND"


class InvalidQueueStatusTransitionError(ConflictError):
    def __init__(self, current: str, requested: str, allowed: list[str]) -> None:
        super().__init__(
            message=f"Cannot transition queue status from {current} to {requested}",
            code="INVALID_STATUS_TRANSITION",
            current_status=current,
            requested_status=requested,
            allowed=allowed,
        )


class QueueEntryNotActiveError(ConflictError):
    def __init__(self, queue_id: int, current: str) -> None:
        super().__init__(
            message=f"Queue entry {queue_id} is {current} and cannot be assigned",
            code="QUEUE_ENTRY_NOT_ACTIVE",
            current_status=current,
        )


# ── Doctor ────────────────────────────────────────────────────────────────
class DoctorNotFoundError(NotFoundError):
    def __init__(self, doctor_id: int) -> None:
        super().__init__("Doctor", doctor_id)
        self.code = "DOCTOR_NOT_FOUND"


class DoctorNotOnDutyError(ConflictError):
    def __init__(self, doctor_id: int, name: str) -> None:
        super().__init__(
            message=f"Dr. {name} is off duty and cannot be assigned patients",
            code="DOCTOR_NOT_ON_DUTY",
            doctor_id=doctor_id,
        )


class DoctorEmailAlreadyExistsError(ConflictError):
    def __init__(self, email: str) -> None:
        super().__init__(
            message=f"Email {email} is already registered",
            code="DOCTOR_EMAIL_EXISTS",
            email=email,
        )


class DoctorHasConsultationsError(ConflictError):
    def __init__(self, doctor_id: int, name: str, count: int) -> None:
        super().__init__(
            message=(
                f"Dr. {name} has {count} consultation(s) on record and cannot be "
                "deleted. Set is_on_duty=false instead."
            ),
            code="DOCTOR_HAS_CONSULTATIONS",
            doctor_id=doctor_id,
            consultations=count,
        )


# ── Authentication / authorisation ────────────────────────────────────────
class AuthenticationError(HealthGuardBaseError):
    """The caller could not be identified."""

    status_code = status.HTTP_401_UNAUTHORIZED

    def __init__(self, message: str = "Not authenticated", code: str = "NOT_AUTHENTICATED") -> None:
        super().__init__(message=message, code=code)


class InvalidCredentialsError(AuthenticationError):
    def __init__(self) -> None:
        # Deliberately does not say whether the email exists: distinguishing
        # them turns the login form into an account-enumeration oracle.
        super().__init__("Incorrect email or password", "INVALID_CREDENTIALS")


class InvalidTokenError(AuthenticationError):
    def __init__(self, detail: str = "Token is invalid or expired") -> None:
        super().__init__(detail, "INVALID_TOKEN")


class RefreshTokenReusedError(AuthenticationError):
    """A refresh token was presented twice — the hallmark of a stolen token."""

    def __init__(self) -> None:
        super().__init__(
            "Refresh token has already been used; all sessions have been ended",
            "REFRESH_TOKEN_REUSED",
        )


class InactiveUserError(HealthGuardBaseError):
    status_code = status.HTTP_403_FORBIDDEN

    def __init__(self) -> None:
        super().__init__("This account has been deactivated", code="ACCOUNT_INACTIVE")


class InsufficientRoleError(HealthGuardBaseError):
    status_code = status.HTTP_403_FORBIDDEN

    def __init__(self, required: list[str], actual: str) -> None:
        super().__init__(
            f"This endpoint requires role {' or '.join(required)}",
            code="INSUFFICIENT_ROLE",
            details={"required": required, "actual": actual},
        )


class EmailAlreadyRegisteredError(ConflictError):
    def __init__(self, email: str) -> None:
        super().__init__(
            message=f"An account already exists for {email}",
            code="EMAIL_ALREADY_REGISTERED",
            email=email,
        )


class ForbiddenError(HealthGuardBaseError):
    """Authenticated, but not permitted to touch this particular record."""

    status_code = status.HTTP_403_FORBIDDEN

    def __init__(self, message: str, code: str = "FORBIDDEN", **details: Any) -> None:
        super().__init__(message=message, code=code, details=details)


# ── Infrastructure ────────────────────────────────────────────────────────
class DatabaseOperationError(HealthGuardBaseError):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    def __init__(self, operation: str, detail: str) -> None:
        super().__init__(f"Database {operation} failed: {detail}", code="DATABASE_ERROR")


class RateLimitExceededError(HealthGuardBaseError):
    status_code = status.HTTP_429_TOO_MANY_REQUESTS

    def __init__(self, limit: int, window_seconds: int) -> None:
        super().__init__(
            f"Rate limit exceeded: {limit} requests per {window_seconds}s",
            code="RATE_LIMIT_EXCEEDED",
            details={"limit": limit, "window_seconds": window_seconds},
        )


def error_response(
    status_code: int, message: str, code: str, details: dict[str, Any]
) -> JSONResponse:
    """Render the single error envelope every client can rely on."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {"code": code, "message": message, "details": details}},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers that keep internal detail out of client responses."""

    @app.exception_handler(HealthGuardBaseError)
    async def _handle_domain_error(
        request: Request, exc: HealthGuardBaseError
    ) -> JSONResponse:
        logger.info(
            "domain_error",
            code=exc.code,
            message=exc.message,
            path=request.url.path,
            method=request.method,
        )
        return error_response(exc.status_code, exc.message, exc.code, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _handle_request_validation(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "Request validation failed",
            "REQUEST_VALIDATION_ERROR",
            {"errors": [{k: str(v) for k, v in err.items()} for err in exc.errors()]},
        )

    @app.exception_handler(IntegrityError)
    async def _handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        # A constraint violation reaching this point is a race we did not
        # pre-check. Log the detail but never return it: the driver quotes the
        # offending row, which may contain patient data.
        logger.warning(
            "integrity_error", path=request.url.path, method=request.method, error=str(exc)
        )
        return error_response(
            status.HTTP_409_CONFLICT,
            "The request conflicts with existing data.",
            "INTEGRITY_ERROR",
            {},
        )

    @app.exception_handler(SQLAlchemyError)
    async def _handle_database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        logger.error(
            "database_error",
            path=request.url.path,
            method=request.method,
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The service is temporarily unable to reach its database.",
            "DATABASE_UNAVAILABLE",
            {},
        )
