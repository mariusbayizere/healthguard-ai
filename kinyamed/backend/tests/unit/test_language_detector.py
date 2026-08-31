"""Language detection and symptom classification."""

from __future__ import annotations

import pytest

from app.models.triage_result import UrgencyLevel
from app.services.triage_service import (
    LANGUAGE_MARKERS,
    detect_language,
    get_classifier,
)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("ndwaye cyane mfite umuriro mwinshi", "kinyarwanda"),
        ("ndumva nkeneye kubonana na muganga", "kinyarwanda"),
        ("I have a headache and fever since two days", "english"),
        ("j'ai de la fievre depuis trois jours et mal a la tete", "french"),
        ("nina homa na maumivu ya kichwa siku tatu", "swahili"),
        ("ninaumwa tumbo sana tangu siku mbili", "swahili"),
        ("I have umuriro na ububabare mu mutwe", "mixed"),
        ("zzz qqq", "unknown"),
    ],
)
def test_detect_language(text: str, expected: str) -> None:
    assert detect_language(text) == expected


def test_every_supported_language_is_reachable() -> None:
    """A label the detector can never emit is a silent coverage gap."""
    from app.services.triage_service import SUPPORTED_LANGUAGES

    assert set(LANGUAGE_MARKERS) | {"mixed", "unknown"} == set(SUPPORTED_LANGUAGES)


def test_markers_are_unique_to_one_language() -> None:
    """A marker in two lists carries no signal and skews detection to 'mixed'."""
    seen: dict[str, str] = {}
    for language, terms in LANGUAGE_MARKERS.items():
        for term in terms:
            assert term not in seen, f"{term!r} in both {seen.get(term)!r} and {language!r}"
            seen[term] = language


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("mfite ububabare bw'igituza", UrgencyLevel.CRITICAL),
        ("kuva amaraso menshi", UrgencyLevel.CRITICAL),
        ("chest pain since this morning", UrgencyLevel.CRITICAL),
        ("mfite umuriro mwinshi", UrgencyLevel.URGENT),
        ("severe vomiting", UrgencyLevel.URGENT),
        ("douleur thoracique depuis ce matin", UrgencyLevel.CRITICAL),
        ("siwezi kupumua", UrgencyLevel.CRITICAL),
        ("j'ai de la fievre", UrgencyLevel.URGENT),
        ("nina homa sana", UrgencyLevel.URGENT),
        ("ndumva nkeneye kubonana na muganga", UrgencyLevel.ROUTINE),
    ],
)
def test_classification(text: str, expected: UrgencyLevel) -> None:
    assert get_classifier().classify(text).urgency is expected


def test_substring_matches_do_not_trigger_urgency() -> None:
    """'painting' must not be read as 'pain'."""
    assert get_classifier().classify("I am painting my house").urgency is UrgencyLevel.ROUTINE
