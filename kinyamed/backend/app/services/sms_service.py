"""Patient SMS notifications.

Delivery goes through an `SMSProvider`, so the network client can be swapped
(Africa's Talking, a test double, the logging stub used in development) without
touching triage logic. Every attempt is recorded in `sms_logs` with its real
outcome: a message that was not actually sent is never logged as SENT.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol

import structlog
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.sms_log import SMSLog, SMSStatus
from app.repositories import sms_log_repository

logger = structlog.get_logger(__name__)

# Single-segment GSM-7 messages are 160 characters; longer messages are billed
# per 153-character segment, so intake texts are kept short deliberately.
SMS_SEGMENT_LENGTH = 160


@dataclass(frozen=True)
class SMSDeliveryResult:
    status: SMSStatus
    provider_message_id: str | None = None
    error_detail: str | None = None


class SMSProvider(Protocol):
    """Anything able to deliver a text message to a phone number."""

    def send(self, *, to: str, message: str) -> SMSDeliveryResult:
        """Deliver `message` to `to`, reporting the outcome."""
        ...


class LoggingSMSProvider:
    """Development provider: records the message without contacting a carrier.

    Returns SKIPPED rather than SENT so that development data cannot be
    mistaken for evidence that patients were actually notified.
    """

    def send(self, *, to: str, message: str) -> SMSDeliveryResult:
        """Log the message and report SKIPPED — nothing was delivered."""
        logger.info("sms_stubbed", to=to, message_length=len(message))
        return SMSDeliveryResult(status=SMSStatus.SKIPPED, error_detail="SMS delivery disabled")


class UnconfiguredSMSProvider:
    """Stand-in used when delivery is enabled but no carrier client is wired.

    Fails loudly per message instead of silently dropping notifications.
    """

    def send(self, *, to: str, message: str) -> SMSDeliveryResult:
        """Report FAILED with a configuration error — never silently drop."""
        return SMSDeliveryResult(
            status=SMSStatus.FAILED,
            error_detail=(
                "SMS_ENABLED is true but no SMS provider is implemented; "
                "wire an Africa's Talking client into get_sms_provider()"
            ),
        )


def get_sms_provider() -> SMSProvider:
    """Return the provider for the current configuration."""
    if not settings.SMS_ENABLED:
        return LoggingSMSProvider()
    return UnconfiguredSMSProvider()


def build_triage_sms(
    name: str, urgency: str, queue_number: int, wait: int | None,
    language: str = "kinyarwanda",
) -> str:
    """Compose the patient's SMS from a SPEAKER-AUTHORED template, or return "".

    RULED 2026-09-08. This function used to hold machine-drafted Kinyarwanda --
    "Jya kwa muganga NONE NONE" -- telling a patient to go to hospital
    immediately. That is patient-facing clinical instruction and falls under the
    same rule as the endpoint's response templates: it is speaker-authored or it
    does not exist.

    RETURNING "" MEANS NO MESSAGE IS SENT. That is the intended behaviour while
    the templates are unauthored. Sending a machine-drafted instruction is worse
    than sending nothing: the patient is in the queue either way, and a wrong
    urgency instruction in their hand is an active harm rather than a missing
    convenience.
    """
    from app.services import response_templates

    template = response_templates.resolve(language, urgency, channel="sms")
    if template.pending:
        logger.info("sms_template_pending", language=language, urgency=urgency,
                    reason=template.reason, action="no message will be sent")
        return ""
    return template.text.format(
        name=name, queue_number=queue_number,
        wait="" if wait is None else str(wait),
    )


def send_sms(
    db: Session,
    *,
    patient_id: int,
    phone: str,
    message: str,
    provider: SMSProvider | None = None,
) -> SMSLog:
    """Record and attempt one SMS, committing the outcome.

    Never raises: a carrier outage must not undo a completed triage. Failures
    are persisted as FAILED with the provider's error for later retry.
    """
    log = sms_log_repository.create(
        db, patient_id=patient_id, message=message, status=SMSStatus.PENDING
    )

    provider = provider or get_sms_provider()
    try:
        result = provider.send(to=phone, message=message)
    except Exception as exc:  # noqa: BLE001 - any provider failure is recorded, not raised
        logger.exception(
            "sms_delivery_failed", patient_id=patient_id, error_type=type(exc).__name__
        )
        result = SMSDeliveryResult(status=SMSStatus.FAILED, error_detail=str(exc)[:500])

    sms_log_repository.update(
        db,
        log,
        status=result.status,
        provider_message_id=result.provider_message_id,
        error_detail=result.error_detail,
        sent_at=datetime.now(timezone.utc) if result.status == SMSStatus.SENT else None,
    )
    logger.info("sms_recorded", patient_id=patient_id, status=result.status.value)
    return log


def send_sms_in_background(patient_id: int, phone: str, message: str) -> None:
    """Deliver an SMS outside the request/response cycle.

    Opens its own session: the request-scoped session is already closed by the
    time a background task runs.
    """
    with SessionLocal() as db:
        try:
            send_sms(db, patient_id=patient_id, phone=phone, message=message)
        except Exception:  # noqa: BLE001 - background work must not crash the worker
            logger.exception("background_sms_failed", patient_id=patient_id)
