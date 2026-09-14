"""Whether a triage needs a clinician's review, from its stored model confidence.

Separate from triage_service so the queue can use it without an import cycle:
the queue's NEEDS REVIEW band and the review flag on every response must be the
same decision, made in one place.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import settings


@dataclass(frozen=True)
class ReviewStatus:
    """Whether a clinician must review this triage before relying on it."""

    requires_human_review: bool
    reason: str | None


def needs_review(confidence: float | None, threshold: float) -> bool:
    """The rule itself. A missing confidence needs review; so does one below threshold."""
    return confidence is None or confidence < threshold


def review_status(confidence: float | None) -> ReviewStatus:
    """Compare a stored confidence with the configured review threshold.

    Evaluated on read against the CURRENT threshold, so a threshold change takes
    effect for every entry at once, including its place in the queue. The flag
    as it stood at decision time is not persisted yet (that needs the deferred
    triage_results migration).

    The score is an uncalibrated softmax maximum (ECE 0.18), which the reason
    says, so nobody reads a high score as a guarantee.
    """
    threshold = settings.MODEL_CONFIDENCE_THRESHOLD
    if not needs_review(confidence, threshold):
        return ReviewStatus(False, None)
    if confidence is None:
        return ReviewStatus(True, "No model confidence was recorded for this triage.")
    return ReviewStatus(
        True,
        f"Model confidence {confidence:.2f} is below the review threshold "
        f"{threshold:.2f}. The score is uncalibrated; a clinician must review "
        "this urgency before relying on it.",
    )
