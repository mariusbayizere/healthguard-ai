"""Symptom triage.

The classifier sits behind a small interface: the current implementation is a
multilingual keyword baseline, and the fine-tuned AfroXLMR model replaces it by
implementing `SymptomClassifier` and being returned from `get_classifier()` —
with no changes to any caller.

All queries are delegated to the repository layer; this module holds the rules
and the transaction boundary.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import structlog
from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.queue import Queue
from app.models.symptom_report import SymptomReport
from app.models.triage_result import TriageResult, UrgencyLevel
from app.core.exceptions import TriageResultNotFoundError
from app.repositories import symptom_report_repository, triage_repository
from app.services import queue_service
from app.services.sms_service import build_triage_sms

logger = structlog.get_logger(__name__)

SUPPORTED_LANGUAGES = frozenset(
    {"kinyarwanda", "english", "french", "swahili", "mixed", "unknown"}
)


@dataclass(frozen=True)
class Classification:
    """What the classifier concluded about a symptom description."""

    urgency: UrgencyLevel
    possible_conditions: str
    confidence: float
    advice_rw: str


@dataclass(frozen=True)
class TriageOutcome:
    """Everything a triage produced, ready to be returned and notified on."""

    report: SymptomReport
    result: TriageResult
    queue_entry: Queue
    queue_position: int
    sms_message: str


class SymptomClassifier(Protocol):
    """Maps a free-text symptom description to a triage decision."""

    def classify(self, text: str) -> Classification:
        """Return the triage decision for a free-text symptom description."""
        ...


def fold(text: str) -> str:
    """Strip accents so that "fievre" matches "fièvre".

    Patients type symptoms on feature-phone keypads and through USSD, where
    accented characters are routinely dropped. Matching on the folded form means
    accent-free French and Kinyarwanda still triage correctly.
    """
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def _term_pattern(terms: tuple[str, ...]) -> re.Pattern[str]:
    """Compile terms into one accent-insensitive, whole-word alternation.

    Whole-word matching is the point: a substring test makes "pain" fire on
    "painting" and "kuva" fire on "kuvamo".
    """
    alternation = "|".join(re.escape(fold(term)) for term in terms)
    return re.compile(rf"(?<!\w)(?:{alternation})(?!\w)", re.IGNORECASE)


# Red-flag terms across all four supported languages. Kinyarwanda comes first
# because this service exists for Kinyarwanda speakers, and an English-only
# keyword list silently triaged every Kinyarwanda report as ROUTINE.
CRITICAL_TERMS: tuple[str, ...] = (
    # Kinyarwanda
    "guhumeka nabi", "sinshobora guhumeka", "kuva amaraso", "amaraso menshi",
    "ububabare bw'igituza", "igituza kirababara", "yataye ubwenge", "yatakaje ubwenge",
    "kugagara", "umutima urahagarara",
    # English
    "chest pain", "can't breathe", "cannot breathe", "breathing", "breathless",
    "unconscious", "bleeding", "haemorrhage", "hemorrhage", "stroke", "seizure",
    "convulsion", "collapsed",
    # French
    "douleur thoracique", "je ne peux pas respirer", "difficulté à respirer",
    "saignement", "hémorragie", "inconscient", "convulsions", "avc",
    # Swahili
    "maumivu ya kifua", "siwezi kupumua", "kutokwa damu", "damu nyingi",
    "kupoteza fahamu", "kifafa", "amezimia",
)
URGENT_TERMS: tuple[str, ...] = (
    # Kinyarwanda
    "umuriro", "umuriro mwinshi", "kuruka", "impiswi", "malariya",
    "ububabare bukabije", "gucika intege", "kubabara cyane", "indwara y'inzoka",
    # English
    "fever", "vomiting", "vomit", "severe", "infection", "malaria", "typhoid",
    "diarrhoea", "diarrhea", "dehydrated", "high temperature",
    # French
    "fièvre", "vomissements", "vomir", "paludisme", "typhoïde", "infection",
    "diarrhée", "douleur intense", "déshydraté",
    # Swahili
    "homa", "kutapika", "malaria", "homa ya matumbo", "kuhara", "maambukizi",
    "maumivu makali",
)

_CRITICAL_PATTERN = _term_pattern(CRITICAL_TERMS)
_URGENT_PATTERN = _term_pattern(URGENT_TERMS)

# Marker words used only to identify the language, never to classify urgency.
LANGUAGE_MARKERS: dict[str, tuple[str, ...]] = {
    "kinyarwanda": (
        "mfite", "ndwaye", "muraho", "ndabona", "kubabara", "ububabare", "cyane",
        "nabi", "amaraso", "igituza", "umutwe", "inda", "kuruka", "sinshobora",
        "ndi", "yanjye", "cyawe", "munsi", "muganga", "umuriro",
    ),
    "english": (
        "i", "have", "my", "pain", "feel", "the", "and", "with", "since", "days",
        "fever", "cough", "head", "stomach", "cannot", "very",
    ),
    "french": (
        "je", "j'ai", "mon", "ma", "douleur", "depuis", "jours", "et", "avec",
        "le", "la", "les", "très", "mal", "tête", "ventre", "fièvre", "ne", "pas",
    ),
    # Note: "na", "ni" and "kwa" are deliberately absent. They are ordinary
    # Kinyarwanda words as well as Swahili ones, so they discriminate nothing
    # and made short Kinyarwanda reports read as "mixed".
    "swahili": (
        "nina", "ninahisi", "yangu", "maumivu", "siku", "sana", "kichwa",
        "tumbo", "homa", "kikohozi", "siwezi", "ninaumwa", "tangu",
    ),
}

_MARKER_PATTERNS: dict[str, re.Pattern[str]] = {
    language: _term_pattern(terms) for language, terms in LANGUAGE_MARKERS.items()
}


def _assert_markers_are_discriminative() -> None:
    """A marker listed under two languages carries no signal — fail loudly.

    This runs at import so a future edit that reintroduces an ambiguous marker
    is caught immediately rather than degrading detection silently.
    """
    seen: dict[str, str] = {}
    for language, terms in LANGUAGE_MARKERS.items():
        for term in terms:
            term = fold(term)
            if term in seen:
                raise ValueError(
                    f"Language marker {term!r} appears under both {seen[term]!r} "
                    f"and {language!r}; markers must be unique to one language."
                )
            seen[term] = language


_assert_markers_are_discriminative()

# A language is called outright only when it leads the runner-up by this factor;
# otherwise the report is genuinely mixed, which is the common case in Rwanda.
_DOMINANCE_RATIO = 3


def detect_language(text: str) -> str:
    """Classify the report as one of the four supported languages, mixed or unknown.

    All four languages are written in the Latin alphabet, so script cannot
    separate them; marker-word counts can.
    """
    folded = fold(text)
    hits = {
        language: len(pattern.findall(folded))
        for language, pattern in _MARKER_PATTERNS.items()
    }
    scored = sorted(hits.items(), key=lambda item: item[1], reverse=True)
    best_language, best_score = scored[0]
    runner_up_score = scored[1][1]

    if best_score == 0:
        return "unknown"
    if runner_up_score == 0 or best_score >= runner_up_score * _DOMINANCE_RATIO:
        return best_language
    return "mixed"


class KeywordClassifier:
    """Baseline classifier matching curated red-flag terms in four languages.

    It is deliberately conservative: anything matching a critical term is
    CRITICAL, because under-triage is the dangerous error in this system.
    """

    def classify(self, text: str) -> Classification:
        """Return the triage decision for a symptom description."""
        folded = fold(text)
        if _CRITICAL_PATTERN.search(folded):
            return Classification(
                urgency=UrgencyLevel.CRITICAL,
                possible_conditions="Possible cardiac, respiratory or haemorrhagic emergency",
                confidence=0.91,
                advice_rw="Ikibazo cyawe ni CRITICAL. Jya kwa muganga NONE NONE!",
            )
        if _URGENT_PATTERN.search(folded):
            return Classification(
                urgency=UrgencyLevel.URGENT,
                possible_conditions="Possible malaria, typhoid or other infection",
                confidence=0.78,
                advice_rw="Ikibazo cyawe ni URGENT. Genda kwa muganga uyu munsi.",
            )
        return Classification(
            urgency=UrgencyLevel.ROUTINE,
            possible_conditions="Routine consultation needed",
            confidence=0.65,
            advice_rw="Ikibazo cyawe ni ROUTINE. Uzabona muganga vuba.",
        )


@lru_cache(maxsize=1)
def get_classifier() -> SymptomClassifier:
    """Return the classifier in use. Swap the implementation here."""
    return KeywordClassifier()


def run_triage(
    db: Session,
    *,
    patient: Patient,
    symptoms_input: str,
    classifier: SymptomClassifier | None = None,
) -> TriageOutcome:
    """Triage a symptom report and place the patient in the queue.

    The report, its triage result and the queue entry are written in a single
    transaction, so a failure can never leave a symptom report with no triage or
    a triage with no place in the queue.

    The SMS is deliberately not sent here: the caller dispatches
    `outcome.sms_message` after the commit, so a carrier outage cannot roll back
    a completed triage.
    """
    classifier = classifier or get_classifier()
    language = detect_language(symptoms_input)
    logger.info(
        "triage_started",
        patient_id=patient.id,
        language=language,
        text_length=len(symptoms_input),
    )

    report = symptom_report_repository.create(
        db,
        commit=False,
        patient_id=patient.id,
        raw_input=symptoms_input,
        language_detected=language,
        # Replaced by the NLP model's extracted entities once it lands.
        symptoms_extracted=symptoms_input,
    )

    classification = classifier.classify(symptoms_input)
    result = triage_repository.create(
        db,
        commit=False,
        symptom_report_id=report.id,
        urgency_level=classification.urgency,
        possible_conditions=classification.possible_conditions,
        confidence_score=classification.confidence,
        ai_response_rw=classification.advice_rw,
    )

    queue_entry = queue_service.enqueue(db, result, commit=False)
    db.commit()

    position = queue_service.position_of(db, queue_entry)
    logger.info(
        "triage_completed",
        patient_id=patient.id,
        triage_id=result.id,
        urgency=classification.urgency.value,
        confidence=classification.confidence,
        language=language,
        queue_number=queue_entry.queue_number,
        queue_position=position,
    )

    return TriageOutcome(
        report=report,
        result=result,
        queue_entry=queue_entry,
        queue_position=position,
        sms_message=build_triage_sms(
            patient.name,
            classification.urgency.value,
            queue_entry.queue_number,
            queue_entry.estimated_wait,
        ),
    )


def get_triage(db: Session, triage_id: int) -> TriageResult:
    """Load a triage result with its patient chain and queue entry, or raise."""
    result = triage_repository.get_with_relations(db, triage_id)
    if result is None:
        raise TriageResultNotFoundError(triage_id)
    return result
