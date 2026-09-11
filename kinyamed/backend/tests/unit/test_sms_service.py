"""SMS composition and delivery-status honesty. No database, no carrier."""

from __future__ import annotations

from app.models.sms_log import SMSStatus
from app.services.sms_service import (
    SMS_SEGMENT_LENGTH,
    LoggingSMSProvider,
    UnconfiguredSMSProvider,
    build_triage_sms,
)


def test_no_message_is_sent_for_a_language_with_no_templates():
    """RULED 2026-09-08: patient-facing SMS is speaker-authored or absent.

    This function used to hold machine-drafted Kinyarwanda telling a patient to
    go to hospital immediately. The two tests that used to live here asserted
    that text's content, so they pinned exactly the behaviour the ruling
    removed. Sending nothing is correct while the templates are unauthored: the
    patient is in the queue either way, and a machine-drafted urgency
    instruction in their hand is an active harm rather than a missing
    convenience.
    """
    # This test follows the languages that are still unauthored. Kinyarwanda and
    # Swahili were both authored on 2026-09-08, so it now uses English. The
    # property under test is "unauthored means silent" -- when English is
    # authored, move it to French.
    #
    # TODO when all four languages are authored: replace the language argument
    # with a temporary fixture that points BRIEF_DIR at an empty directory,
    # rather than deleting this test. The property must outlive every language
    # being filled -- a regression that made an unauthored language fall back to
    # English instead of staying silent would then still be caught, and there
    # would be no real language left to catch it with.
    for urgency in ("CRITICAL", "URGENT", "ROUTINE"):
        assert (
            build_triage_sms("Uwimana", urgency, 12, wait=20, language="english") == ""
        )


def test_authored_kinyarwanda_sms_fits_one_segment_for_realistic_names():
    """The speaker's templates are long; a long name can push them over 160.

    Measured 2026-09-08: 116-148 characters for names up to 22 characters, and
    168 for a 40-character name -- which bills as two segments. This pins the
    realistic case and documents the boundary rather than asserting a limit the
    templates do not actually hold at every input.
    """
    for urgency in ("CRITICAL", "URGENT", "ROUTINE"):
        message = build_triage_sms("Nyiraneza Marie Claire", urgency, 12, wait=20)
        assert message, "kinyarwanda templates are authored and must render"
        assert "{" not in message
        assert len(message) <= SMS_SEGMENT_LENGTH


def test_an_authored_template_is_formatted_with_its_slots(monkeypatch):
    """When a speaker HAS authored one, the slots are filled and nothing else is."""
    from app.services import response_templates as rt

    authored = rt.ResponseTemplate(
        "kinyarwanda",
        "ROUTINE",
        "Muraho {name}, numero yawe ni {queue_number}. Itegereze ~{wait} min.",
        False,
        "",
    )
    monkeypatch.setattr(rt, "resolve", lambda *a, **k: authored)
    message = build_triage_sms("Uwimana", "ROUTINE", 12, wait=20)
    assert message == "Muraho Uwimana, numero yawe ni 12. Itegereze ~20 min."
    # No unfilled placeholder may reach a patient's phone.
    assert "{" not in message


def test_a_critical_template_never_receives_a_wait_time(monkeypatch):
    """Telling a critical patient to wait would be wrong, whoever authored it.

    The CRITICAL sms brief declares slots {name} {queue_number} only, so a
    template that referenced {wait} would be a brief violation. This pins that
    the composer does not supply one by accident.
    """
    from app.services import response_templates as rt

    authored = rt.ResponseTemplate(
        "kinyarwanda",
        "CRITICAL",
        "Muraho {name}, jya kwa muganga. Numero: {queue_number}.",
        False,
        "",
    )
    monkeypatch.setattr(rt, "resolve", lambda *a, **k: authored)
    message = build_triage_sms("Uwimana", "CRITICAL", 12, wait=40)
    assert "40" not in message
    assert "{" not in message


def test_message_handles_an_unknown_wait(monkeypatch):
    """An unknown wait must not reach a patient as the string "None"."""
    from app.services import response_templates as rt

    authored = rt.ResponseTemplate(
        "kinyarwanda", "ROUTINE", "Numero {queue_number}. ~{wait} min.", False, ""
    )
    monkeypatch.setattr(rt, "resolve", lambda *a, **k: authored)
    message = build_triage_sms("Uwimana", "ROUTINE", 12, wait=None)
    assert "None" not in message


def test_messages_fit_a_single_sms_segment():
    """Multi-segment messages are billed per segment."""
    for urgency in ("CRITICAL", "URGENT", "ROUTINE"):
        message = build_triage_sms("Nyirahabimana", urgency, 999, wait=30)
        assert len(message) <= SMS_SEGMENT_LENGTH, (
            f"{urgency} message is {len(message)} chars"
        )


def test_disabled_provider_reports_skipped_not_sent():
    """Development data must never look like a delivered notification."""
    result = LoggingSMSProvider().send(to="+250788123456", message="hello")
    assert result.status is SMSStatus.SKIPPED


def test_unconfigured_provider_fails_loudly():
    result = UnconfiguredSMSProvider().send(to="+250788123456", message="hello")
    assert result.status is SMSStatus.FAILED
    assert result.error_detail
