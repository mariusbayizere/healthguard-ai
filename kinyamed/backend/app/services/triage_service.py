"""Symptom triage.

The classifier sits behind a small interface, `SymptomClassifier`, and its only
implementation is the fine-tuned model (`model_classifier.ModelClassifier`).
`get_classifier()` returns that model or `None`; `run_triage()` refuses to
classify, and writes nothing, when it gets `None` or when the model raises.
There is no fallback classifier: when the model cannot answer, a person must.

All queries are delegated to the repository layer; this module holds the rules
and the transaction boundary.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Protocol

import structlog
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import TriageModelUnavailableError, TriageResultNotFoundError
from app.models.patient import Patient
from app.models.queue import Queue
from app.models.symptom_report import SymptomReport
from app.models.triage_result import TriageResult, UrgencyLevel
from app.repositories import symptom_report_repository, triage_repository
from app.services import queue_service, red_flags
from app.services.patient_message import patient_receipt
from app.services.review import ReviewStatus, review_status
from app.services.text_fold import fold

logger = structlog.get_logger(__name__)

__all__ = ["ReviewStatus", "fold", "review_status"]  # re-exported for existing callers

SUPPORTED_LANGUAGES = frozenset(
    {"kinyarwanda", "english", "french", "swahili", "mixed", "unknown"}
)


@dataclass(frozen=True)
class Classification:
    """What the classifier concluded about a symptom description."""

    urgency: UrgencyLevel
    confidence: float


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


def _term_pattern(terms: tuple[str, ...]) -> re.Pattern[str]:
    """Compile terms into one accent-insensitive, whole-word alternation.

    Whole-word matching is the point: a substring test makes "pain" fire on
    "painting" and "kuva" fire on "kuvamo".
    """
    alternation = "|".join(re.escape(fold(term)) for term in terms)
    return re.compile(rf"(?<!\w)(?:{alternation})(?!\w)", re.IGNORECASE)


# Marker words used only to identify the language, never to classify urgency.
LANGUAGE_MARKERS: dict[str, tuple[str, ...]] = {
    "kinyarwanda": (
        "mfite",
        "ndwaye",
        "muraho",
        "ndabona",
        "kubabara",
        "ububabare",
        "cyane",
        "nabi",
        "amaraso",
        "igituza",
        "umutwe",
        "inda",
        "kuruka",
        "sinshobora",
        "ndi",
        "yanjye",
        "cyawe",
        "munsi",
        "muganga",
        "umuriro",
    ),
    "english": (
        "i",
        "have",
        "my",
        "pain",
        "feel",
        "the",
        "and",
        "with",
        "since",
        "days",
        "fever",
        "cough",
        "head",
        "stomach",
        "cannot",
        "very",
    ),
    "french": (
        "je",
        "j'ai",
        "mon",
        "ma",
        "douleur",
        "depuis",
        "jours",
        "et",
        "avec",
        "le",
        "la",
        "les",
        "très",
        "mal",
        "tête",
        "ventre",
        "fièvre",
        "ne",
        "pas",
    ),
    # Note: "na", "ni" and "kwa" are deliberately absent. They are ordinary
    # Kinyarwanda words as well as Swahili ones, so they discriminate nothing
    # and made short Kinyarwanda reports read as "mixed".
    "swahili": (
        "nina",
        "ninahisi",
        "yangu",
        "maumivu",
        "siku",
        "sana",
        "kichwa",
        "tumbo",
        "homa",
        "kikohozi",
        "siwezi",
        "ninaumwa",
        "tangu",
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


# What get_classifier() selected, or why nothing was, for the startup log.
ACTIVE_CLASSIFIER_DESCRIPTION: str = "not yet selected"


@lru_cache(maxsize=1)
def get_classifier() -> SymptomClassifier | None:
    """Return the loaded model, or None when there is no model to use.

    Selection lives in `model_classifier.build_classifier()`. `None` is not an
    error here; it is the fail-closed state, and `run_triage()` turns it into a
    503. Imported lazily so this module stays importable without the optional
    ML dependencies.
    """
    global ACTIVE_CLASSIFIER_DESCRIPTION
    from app.services.model_classifier import build_classifier

    classifier, description = build_classifier()
    ACTIVE_CLASSIFIER_DESCRIPTION = description
    return classifier


def _fail_closed() -> TriageModelUnavailableError:
    return TriageModelUnavailableError(settings.TRIAGE_UNAVAILABLE_RETRY_AFTER_SECONDS)


def _classify(classifier: SymptomClassifier | None, text: str) -> Classification:
    """The model's classification, or a 503. Never any other classification."""
    if classifier is None:
        raise _fail_closed()
    try:
        return classifier.classify(text)
    except Exception as error:  # any inference failure fails closed, re-raised as 503
        # The error type only: an exception message may quote the patient's text.
        logger.error(
            "triage_inference_failed",
            error_type=type(error).__name__,
            action="returning 503; nothing written; triage manually",
        )
        raise _fail_closed() from error


def run_triage(
    db: Session,
    *,
    patient: Patient,
    symptoms_input: str,
    classifier: SymptomClassifier | None,
    lexicon: red_flags.RedFlagLexicon | None = None,
) -> TriageOutcome:
    """Triage a symptom report and place the patient in the queue.

    FAILS CLOSED. Classification happens before any write. If `classifier` is
    None or raises, `TriageModelUnavailableError` (503) propagates and nothing
    is written: no report, no result, no queue entry.

    The report, its triage result and the queue entry are written in a single
    transaction, so a failure can never leave a symptom report with no triage or
    a triage with no place in the queue.

    RED-FLAG LAYER (CLAUDE.md L2). The lexicon is matched BEFORE the model is
    called. A match forces CRITICAL whatever the model says; nothing lowers
    urgency, and PostgreSQL rejects any row that would. The model's own urgency
    is stored as `model_urgency_raw`. A match does not bypass fail-closed: with no
    model the request is still a 503 and nothing is written. Whether rules alone
    should enqueue a CRITICAL without the model is a clinical decision (H6). With
    the shipped, empty lexicon the layer matches nothing, so the stored urgency
    equals the model's.

    The SMS is deliberately not sent here: the caller dispatches
    `outcome.sms_message` after the commit, so a carrier outage cannot roll back
    a completed triage.
    """
    rule_match = (lexicon if lexicon is not None else red_flags.get_lexicon()).match(
        symptoms_input
    )
    classification = _classify(classifier, symptoms_input)
    decision = red_flags.apply(classification.urgency, rule_match)
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

    result = triage_repository.create(
        db,
        commit=False,
        symptom_report_id=report.id,
        urgency_level=decision.urgency,
        model_urgency_raw=decision.model_urgency,
        rules_layer_triggered=decision.triggered,
        rules_layer_reason=decision.reason,
        # Retired columns: no condition is ever named, and no machine-drafted
        # advice is stored. Written as NULL until a migration drops them.
        possible_conditions=None,
        confidence_score=classification.confidence,
        ai_response_rw=None,
    )

    queue_entry = queue_service.enqueue(db, result, commit=False)
    db.commit()

    position = queue_service.position_of(db, queue_entry)
    logger.info(
        "triage_completed",
        patient_id=patient.id,
        triage_id=result.id,
        urgency=decision.urgency.value,
        model_urgency=decision.model_urgency.value,
        rules_layer_triggered=decision.triggered,
        # concept_ids only, never text (L11)
        rules_layer_concepts=list(rule_match.concept_ids),
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
        # The SMS says exactly what the app says: the urgency-independent receipt.
        sms_message=patient_receipt(
            queue_number=queue_entry.queue_number, queue_position=position
        ),
    )


def get_triage(db: Session, triage_id: int) -> TriageResult:
    """Load a triage result with its patient chain and queue entry, or raise."""
    result = triage_repository.get_with_relations(db, triage_id)
    if result is None:
        raise TriageResultNotFoundError(triage_id)
    return result
