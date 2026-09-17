"""Masking of personal data at the points where it leaves the service (L11).

Phones, email addresses and personal names are masked in ONE place per exit,
not at call sites, because a call site that forgets is how a phone number
reaches a log:

  * `mask_pii_processor`  — every structlog event, just before rendering.
  * `PiiLogFilter`        — every stdlib record (uvicorn access lines carry the
                            query string, e.g. ?search=0788123456).
  * `MaskedPhone`         — every API response field that carries a phone.

The stored column keeps the full E.164 number; nothing here touches storage.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping, MutableMapping
from typing import Annotated, Any, Final

from pydantic import PlainSerializer

# 9-15 digits, optionally led by "+", optionally split by single spaces or
# hyphens, and not part of a longer word or number. The boundaries keep UUIDs,
# hashes and tokens out (their digit runs touch letters) and decimals out (a
# dot followed by a digit), while a phone at the end of a sentence ("... on
# 0788123456.") is still masked.
_PHONE: Final = re.compile(r"(?<![\w*+])(?<!\d\.)\+?\d(?:[ \-]?\d){8,14}(?!\w)(?!\.\d)")
_EMAIL: Final = re.compile(r"(?<![\w.+-])([\w.+-])[\w.+-]*@([\w-]+(?:\.[\w-]+)+)")

KEPT_DIGITS: Final = 2
REDACTED: Final = "[redacted]"

# Keys whose value is personal data whatever it looks like.
PHONE_KEYS: Final = frozenset(
    {"phone", "to", "phone_number", "patient_phone", "phone_sent_to", "msisdn"}
)
NAME_KEYS: Final = frozenset(
    {"name", "full_name", "patient_name", "first_name", "last_name"}
)


def mask_phone(value: str) -> str:
    """Every digit but the last two becomes '*'; a leading '+' is kept."""
    digits = re.sub(r"\D", "", value)
    prefix = "+" if value.strip().startswith("+") else ""
    kept = digits[-KEPT_DIGITS:]
    return f"{prefix}{'*' * (len(digits) - len(kept))}{kept}"


def mask_email(value: str) -> str:
    return _EMAIL.sub(lambda m: f"{m.group(1)}***@{m.group(2)}", value)


def scrub_text(value: str) -> str:
    """Mask every phone- or email-shaped substring of free text."""
    return mask_email(_PHONE.sub(lambda m: mask_phone(m.group(0)), value))


def _scrub(value: Any, key: str | None = None) -> Any:
    if key in NAME_KEYS and value:
        return REDACTED
    if key in PHONE_KEYS and isinstance(value, str) and value:
        return mask_phone(value) if re.search(r"\d", value) else REDACTED
    if isinstance(value, str):
        return scrub_text(value)
    if isinstance(value, Mapping):
        return {k: _scrub(v, str(k)) for k, v in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return type(value)(_scrub(v) for v in value)
    return value


def mask_pii_processor(
    _logger: Any, _method: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """structlog processor: mask personal data in every field of every event."""
    for key in list(event_dict):
        event_dict[key] = _scrub(event_dict[key], key)
    return event_dict


class PiiLogFilter(logging.Filter):
    """stdlib filter: mask personal data in a record's message and arguments."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Arguments keep their positions and types, because formatters unpack
        # them (uvicorn's AccessFormatter reads args[2] as the path and args[4]
        # as an int status). Only an argument whose text would carry personal
        # data is replaced, by its scrubbed text; that includes non-strings
        # whose str() does, such as the URL object httpx logs.
        if isinstance(record.msg, str):
            record.msg = scrub_text(record.msg)
        if isinstance(record.args, tuple):
            record.args = tuple(_scrub_arg(arg) for arg in record.args)
        elif isinstance(record.args, Mapping):
            record.args = {k: _scrub_arg(v) for k, v in record.args.items()}
        return True


def _scrub_arg(arg: object) -> object:
    if isinstance(arg, int | float | bool) or arg is None:
        return arg
    text = str(arg)
    scrubbed = scrub_text(text)
    if isinstance(arg, str) or scrubbed != text:
        return scrubbed
    return arg


MaskedPhone = Annotated[str, PlainSerializer(mask_phone, return_type=str)]
"""A phone number in an API response. Serialised masked; validated unchanged."""


def _json_safe(value: Any) -> Any:
    """Coerce a column value to something JSONB can store.

    Model snapshots carry datetimes, enums and decimals. Rendering them here
    rather than at the call site keeps the audit payload a faithful view of the
    row instead of whatever each caller happened to serialise.
    """
    import datetime
    import decimal
    import enum
    import uuid

    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, datetime.datetime | datetime.date | datetime.time):
        return value.isoformat()
    if isinstance(value, decimal.Decimal):
        return float(value)
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Mapping):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        return [_json_safe(v) for v in value]
    if isinstance(value, str | int | float | bool) or value is None:
        return value
    return str(value)


def scrub_payload(payload: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Mask personal data in an audit payload and make it JSONB-storable.

    The same `_scrub` the log processors use, so a key masked in a log line is
    masked in an audit row: one definition of what counts as personal data,
    not two that drift apart.
    """
    if payload is None:
        return None
    return {str(k): _json_safe(_scrub(v, str(k))) for k, v in payload.items()}
