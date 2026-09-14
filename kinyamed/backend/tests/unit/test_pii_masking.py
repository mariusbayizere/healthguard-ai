"""PII is masked where logs are produced, not at each call site (L11).

A call site that forgets to mask is the normal way a phone number reaches a log,
which is how 336 log lines came to carry one. These tests hold the processor
that every structlog event passes through, and the filter on stdlib loggers.
"""

from __future__ import annotations

import logging

import pytest
from app.core.pii import (
    PiiLogFilter,
    mask_email,
    mask_phone,
    mask_pii_processor,
    scrub_text,
)


@pytest.mark.parametrize(
    ("raw", "masked"),
    [
        ("+250788123456", "+**********56"),
        ("0788123456", "********56"),
        ("250788123456", "**********56"),
        ("+14155550123", "+*********23"),
    ],
)
def test_mask_phone_keeps_only_the_last_two_digits(raw: str, masked: str) -> None:
    assert mask_phone(raw) == masked


def test_scrub_text_masks_phones_inside_free_text() -> None:
    text = "sms to=+250788123456 and 0788 123 456 and 0788-123-456 failed"
    scrubbed = scrub_text(text)
    for digits in ("250788123456", "0788123456", "0788 123 456", "0788-123-456"):
        assert digits not in scrubbed
    assert "56 failed" in scrubbed


def test_scrub_text_masks_a_phone_at_the_end_of_a_sentence() -> None:
    assert "0788123456" not in scrub_text("Call the patient on 0788123456.")


@pytest.mark.parametrize(
    "harmless",
    [
        "request_id=881dfdb6-f51b-40e3-9046-644926aa4fa2",
        "2026-09-14T08:12:47.816557Z",
        "duration_ms=30489.42",
        "epoch=1726304167.123456",
        "token=Ab9047647837xYz",
        "queue_number=366 queue_position=1",
        "sha256=0c9c3a39119f2cacbd324da6f3a08c9b5b057d1a71f0a7b0f54d25914aaef152",
    ],
)
def test_scrub_text_leaves_ids_timestamps_and_counts_alone(harmless: str) -> None:
    assert scrub_text(harmless) == harmless


def test_mask_email() -> None:
    assert mask_email("uwimana.alice@example.rw") == "u***@example.rw"
    assert "uwimana" not in scrub_text("account exists for uwimana.alice@example.rw")


def test_the_processor_masks_nested_values_and_sensitive_keys() -> None:
    event = {
        "event": "sms_stubbed",
        "to": "+250788123456",
        "phone": "0788123456",
        "patient_name": "Uwimana Alice",
        "full_name": "Uwimana Alice",
        "detail": {"rows": ["contact 0788123456", ("uwimana.alice@example.rw",)]},
        "exception": "Traceback ... Failing row contains (+250788123456)",
        "request_id": "881dfdb6-f51b-40e3-9046-644926aa4fa2",
    }
    out = mask_pii_processor(None, "info", event)
    flat = repr(out)
    for leaked in ("788123456", "Uwimana Alice", "uwimana.alice"):
        assert leaked not in flat, f"{leaked!r} survived the processor"
    assert out["request_id"] == "881dfdb6-f51b-40e3-9046-644926aa4fa2"
    assert out["event"] == "sms_stubbed"


def test_names_in_free_text_are_not_maskable_by_pattern() -> None:
    """Stated limit: a name inside a sentence has no shape to match.

    Names are masked by KEY (patient_name, full_name, ...). Free text that could
    quote a row -- a database driver's error -- is therefore not logged at all
    (see the IntegrityError handler and test_pii_scan.py). This test pins the
    limit so nobody assumes the processor covers it.
    """
    out = mask_pii_processor(
        None, "info", {"event": "x", "detail": "row (Uwimana Alice)"}
    )
    assert "Uwimana Alice" in out["detail"]


def test_the_stdlib_filter_masks_uvicorn_access_lines() -> None:
    """uvicorn logs the full path, query string included: ?search=0788123456."""
    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:5000", "GET", "/api/v1/patients?search=0788123456", "1.1", 200),
        None,
    )
    assert PiiLogFilter().filter(record) is True
    assert "0788123456" not in record.getMessage()


def test_filtered_access_records_still_format_with_uvicorns_formatter() -> None:
    """uvicorn's AccessFormatter unpacks record.args; the filter must keep its shape.

    An earlier version set args to None: every access line then raised inside
    logging and printed a traceback instead of the line. Found on a real server.
    """
    from uvicorn.logging import AccessFormatter

    record = logging.LogRecord(
        "uvicorn.access",
        logging.INFO,
        __file__,
        1,
        '%s - "%s %s HTTP/%s" %d',
        ("127.0.0.1:5000", "GET", "/api/v1/patients?search=0788123456", "1.1", 200),
        None,
    )
    PiiLogFilter().filter(record)
    line = AccessFormatter(
        '%(client_addr)s - "%(request_line)s" %(status_code)s'
    ).format(record)
    assert "0788123456" not in line
    assert "200" in line


def test_non_string_arguments_are_masked_too() -> None:
    """httpx logs a URL object; its str() carries the query string."""

    class _Url:
        def __str__(self) -> str:
            return "http://testserver/api/v1/patients?search=0788123456"

    record = logging.LogRecord(
        "httpx", logging.INFO, __file__, 1, "HTTP Request: %s %s", ("GET", _Url()), None
    )
    PiiLogFilter().filter(record)
    assert "0788123456" not in record.getMessage()


def test_the_logging_configuration_installs_both() -> None:
    import structlog
    from app.core.logging import configure_logging

    configure_logging()
    assert mask_pii_processor in structlog.get_config()["processors"]
    for name in ("", "uvicorn", "uvicorn.access", "uvicorn.error"):
        assert any(
            isinstance(f, PiiLogFilter) for f in logging.getLogger(name).filters
        ), f"no PII filter on logger {name!r}"
    handlers = logging.getLogger().handlers
    assert handlers and all(
        any(isinstance(f, PiiLogFilter) for f in h.filters) for h in handlers
    ), "records propagated from library loggers reach unfiltered root handlers"
