"""C1 — the patient-facing response slot, deliberately unfilled.

The endpoint returns an urgency LABEL and a RESPONSE. The label is produced by
the classifier. The response is the sentence a patient actually reads, and it is
the one piece of text in this system that tells a person to go to hospital now
or that it is safe to wait.

WHY THERE IS NO DEFAULT STRING HERE
------------------------------------
RULED 2026-09-08: response templates are speaker-authored, three per language,
one per urgency class. A machine-drafted sentence telling someone to go to
hospital immediately is exactly the text that must not be machine-drafted, and
a plausible-looking placeholder is worse than an empty slot because it reads as
real to everyone downstream -- a reviewer, a frontend developer, a screenshot in
a funding application.

So this module ships EMPTY and says so. `resolve()` returns a PENDING state that
the API surfaces explicitly. It does not fall back to English, it does not
return the urgency name as a sentence, and it does not echo the keyword
baseline's advice string, because all three would look like a working response.

The briefs are `review/speaker_brief_<language>_v2_responses.csv`, one row per
urgency, carrying what the sentence must convey and what it must not say.

WHAT IS ALREADY DECIDED, AND IS NOT THE TEMPLATE'S TO CHANGE
-------------------------------------------------------------
The response must not name a condition. The classifier predicts urgency only; it
was never trained to diagnose, and `ModelClassifier` leaves `possible_conditions`
empty for the same reason. A template that says "this may be malaria" would be
inventing a diagnosis at the last hop of a pipeline that carefully avoided one.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

# ml_model/review/, reached from backend/app/services/
BRIEF_DIR = Path(__file__).resolve().parents[3] / "ml_model" / "review"

SUPPORTED = ("kinyarwanda", "english", "french", "swahili")


@dataclass(frozen=True)
class ResponseTemplate:
    language: str
    urgency: str
    text: str
    pending: bool
    reason: str


def _brief_path(language: str) -> Path:
    return BRIEF_DIR / f"speaker_brief_{language}_v2_responses.csv"


def load(language: str, channel: str = "app") -> dict[str, str]:
    """Authored templates for one language and channel, keyed by urgency.

    `channel` is "app" (the endpoint response) or "sms". They are separate asks
    because an SMS is read once on a small screen under a character limit and
    carries a queue number, so the same sentence does not serve both.
    """
    path = _brief_path(language)
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for row in csv.DictReader(path.open(encoding="utf-8")):
        if (row.get("channel") or "app").strip().lower() != channel:
            continue
        phrasing = (row.get("your_phrasing") or "").strip()
        if phrasing:
            out[(row.get("urgency") or "").strip().upper()] = phrasing
    return out


def resolve(language: str, urgency: str, channel: str = "app") -> ResponseTemplate:
    """The sentence for this language and urgency, or an explicit PENDING state.

    PENDING is a first-class outcome, not an error. The endpoint reports it, the
    caller can see it, and nobody can mistake it for a response that exists.
    """
    language = (language or "").strip().lower()
    urgency = (urgency or "").strip().upper()

    if language not in SUPPORTED:
        return ResponseTemplate(
            language,
            urgency,
            "",
            True,
            f"language {language!r} is not one of {SUPPORTED}",
        )

    authored = load(language, channel)
    if not authored:
        return ResponseTemplate(
            language,
            urgency,
            "",
            True,
            f"no {channel} template is authored for {language}. The brief is "
            f"{_brief_path(language).name}; three rows per channel, one per "
            "urgency, awaiting a speaker. NOT machine-drafted by design.",
        )

    text = authored.get(urgency, "")
    if not text:
        return ResponseTemplate(
            language,
            urgency,
            "",
            True,
            f"{language} has authored templates but not for urgency {urgency!r}",
        )

    return ResponseTemplate(language, urgency, text, False, "")


def status() -> dict[str, dict[str, bool]]:
    """Per language, which urgency classes have an authored response."""
    return {
        f"{lang}/{ch}": {
            u: bool(load(lang, ch).get(u)) for u in ("CRITICAL", "URGENT", "ROUTINE")
        }
        for lang in SUPPORTED
        for ch in ("app", "sms")
    }
