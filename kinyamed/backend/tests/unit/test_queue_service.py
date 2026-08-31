"""Queue wait-estimation rules. Pure logic — no database."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.models.triage_result import UrgencyLevel
from app.services.queue_service import _wait_for

CRITICAL = UrgencyLevel.CRITICAL.priority
URGENT = UrgencyLevel.URGENT.priority
ROUTINE = UrgencyLevel.ROUTINE.priority


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


@pytest.mark.parametrize("priority", [CRITICAL, URGENT, ROUTINE])
def test_wait_is_never_negative(priority: int):
    assert _wait_for(priority, ahead=0, capacity=1) >= 0


def test_urgency_priority_ordering_is_the_clinical_ordering():
    """Lower sorts earlier; a regression here silently reorders the queue."""
    assert CRITICAL < URGENT < ROUTINE
