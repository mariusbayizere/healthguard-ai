"""Queue wait-estimation rules. Pure logic — no database."""

from __future__ import annotations

import pytest
from app.core.config import settings
from app.models.queue_band import QueueBand
from app.models.triage_result import UrgencyLevel
from app.services.queue_service import _wait_for_band as _wait_for

CRITICAL = QueueBand.CRITICAL
URGENT = QueueBand.URGENT
ROUTINE = QueueBand.ROUTINE


def test_critical_never_waits():
    assert _wait_for(CRITICAL, ahead=50, capacity=1) == 0


def test_routine_wait_scales_with_the_queue():
    per_patient = settings.MINUTES_PER_PATIENT
    assert _wait_for(ROUTINE, ahead=0, capacity=1) == 0
    assert _wait_for(ROUTINE, ahead=3, capacity=1) == 3 * per_patient


def test_wait_is_divided_across_clinicians_on_duty():
    """Two doctors clear a queue twice as fast as one."""
    one_doctor = _wait_for(ROUTINE, ahead=8, capacity=1)
    two_doctors = _wait_for(ROUTINE, ahead=8, capacity=2)
    assert two_doctors == one_doctor / 2


def test_urgent_wait_is_capped():
    capped = _wait_for(URGENT, ahead=100, capacity=1)
    assert capped == settings.URGENT_MAX_WAIT_MINUTES


@pytest.mark.parametrize("band", list(QueueBand))
def test_wait_is_never_negative(band: QueueBand):
    assert _wait_for(band, ahead=0, capacity=1) >= 0


def test_urgency_priority_ordering_is_the_clinical_ordering():
    """Lower sorts earlier; a regression here silently reorders the queue."""
    assert (
        UrgencyLevel.CRITICAL.priority
        < UrgencyLevel.URGENT.priority
        < UrgencyLevel.ROUTINE.priority
    )
    assert CRITICAL < URGENT < ROUTINE


# ── Bands (item 2d) ────────────────────────────────────────────────────────────
def test_the_four_bands_sort_in_clinical_review_order():
    from app.models.queue_band import QueueBand

    assert [b.name for b in sorted(QueueBand)] == [
        "CRITICAL",
        "NEEDS_REVIEW",
        "URGENT",
        "ROUTINE",
    ]


@pytest.mark.parametrize(
    ("urgency", "flagged", "band"),
    [
        (UrgencyLevel.CRITICAL, False, "CRITICAL"),
        (UrgencyLevel.CRITICAL, True, "CRITICAL"),
        (UrgencyLevel.URGENT, False, "URGENT"),
        (UrgencyLevel.URGENT, True, "NEEDS_REVIEW"),
        (UrgencyLevel.ROUTINE, False, "ROUTINE"),
        (UrgencyLevel.ROUTINE, True, "NEEDS_REVIEW"),
    ],
)
def test_band_for_every_combination(urgency, flagged, band):
    from app.models.queue_band import band_for

    assert band_for(urgency, requires_review=flagged).name == band


def test_a_flagged_case_is_quoted_no_longer_than_an_urgent_one():
    """NEEDS REVIEW is reviewed before URGENT, so its quoted wait is capped the same way."""
    from app.models.queue_band import QueueBand
    from app.services.queue_service import _wait_for_band

    assert _wait_for_band(QueueBand.NEEDS_REVIEW, ahead=100, capacity=1) == (
        settings.URGENT_MAX_WAIT_MINUTES
    )
    assert _wait_for_band(QueueBand.CRITICAL, ahead=100, capacity=1) == 0
