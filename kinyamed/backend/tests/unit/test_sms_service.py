"""SMS composition and delivery-status honesty. No database, no carrier."""

from __future__ import annotations

from app.models.sms_log import SMSStatus
from app.services.sms_service import (
    SMS_SEGMENT_LENGTH,
    LoggingSMSProvider,
    UnconfiguredSMSProvider,
    build_triage_sms,
)


def test_critical_message_omits_a_wait_time():
    """Telling a critical patient to wait would be wrong."""
    message = build_triage_sms("Uwimana", "CRITICAL", 12, wait=40)
    assert "CRITICAL" in message
    assert "Itegereze" not in message


def test_routine_message_includes_the_wait():
    assert "~20 min" in build_triage_sms("Uwimana", "ROUTINE", 12, wait=20)


def test_message_handles_an_unknown_wait():
    message = build_triage_sms("Uwimana", "ROUTINE", 12, wait=None)
    assert "None" not in message


def test_messages_fit_a_single_sms_segment():
    """Multi-segment messages are billed per segment."""
    for urgency in ("CRITICAL", "URGENT", "ROUTINE"):
        message = build_triage_sms("Nyirahabimana", urgency, 999, wait=30)
        assert len(message) <= SMS_SEGMENT_LENGTH, f"{urgency} message is {len(message)} chars"


def test_disabled_provider_reports_skipped_not_sent():
    """Development data must never look like a delivered notification."""
    result = LoggingSMSProvider().send(to="+250788123456", message="hello")
    assert result.status is SMSStatus.SKIPPED


def test_unconfigured_provider_fails_loudly():
    result = UnconfiguredSMSProvider().send(to="+250788123456", message="hello")
    assert result.status is SMSStatus.FAILED
    assert result.error_detail
