"""Four queue bands: CRITICAL, NEEDS REVIEW, URGENT, ROUTINE; arrival within each.

A triage the model could not confidently classify (requires_human_review) was
sorted by the very class it could not confidently assign. Measured with v2d,
"sinshobora guhumeka" ("I can't breathe") came back ROUTINE at 0.598, was flagged,
and landed at the bottom of the queue, below every unflagged case. A clinician
working top-down never reached it.

A low-confidence CRITICAL stays in the CRITICAL band: moving it down would demote
a CRITICAL prediction, and CRITICAL must outrank everything.
"""

from __future__ import annotations

import itertools
import random

import pytest

NEEDS_REVIEW_LABEL = "Model could not classify — review these first"
CONFIDENT, LOW = 0.9, 0.598


@pytest.fixture
def submit(client, patient_factory):
    """Triage a new patient at a chosen (urgency, confidence). Returns the response."""
    import main
    from app.models.triage_result import UrgencyLevel
    from app.routes.v1.triage import get_triage_classifier
    from app.services.triage_service import Classification

    script: dict[str, tuple[str, float]] = {}

    class _Scripted:
        def classify(self, text: str) -> Classification:
            urgency, confidence = script[text]
            return Classification(urgency=UrgencyLevel(urgency), confidence=confidence)

    main.app.dependency_overrides[get_triage_classifier] = lambda: _Scripted()
    counter = itertools.count()

    def _submit(name: str, urgency: str, confidence: float) -> dict:
        text = f"scripted case {next(counter)}"
        script[text] = (urgency, confidence)
        patient = patient_factory(name=name)
        response = client.post(
            "/api/v1/triage", json={"patient_id": patient["id"], "symptoms_input": text}
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _submit


def _queue(client) -> list[dict]:
    return client.get("/api/v1/queue", params={"page_size": 200}).json()["items"]


def test_a_flagged_routine_case_sorts_above_unflagged_urgent_and_routine(
    client, submit
):
    for name in ("Routine One", "Routine Two", "Routine Three"):
        submit(name, "ROUTINE", CONFIDENT)
    submit("Urgent Confident", "URGENT", CONFIDENT)
    flagged = submit("Cannot Breathe", "ROUTINE", LOW)

    rows = _queue(client)
    assert [r["patient_name"] for r in rows] == [
        "Cannot Breathe",
        "Urgent Confident",
        "Routine One",
        "Routine Two",
        "Routine Three",
    ]
    assert [r["band"] for r in rows] == [
        "NEEDS_REVIEW",
        "URGENT",
        "ROUTINE",
        "ROUTINE",
        "ROUTINE",
    ]
    assert [r["queue_position"] for r in rows] == [1, 2, 3, 4, 5]
    assert flagged["queue_position"] == 1, (
        "the triage response disagreed with the queue"
    )


def test_critical_outranks_needs_review_even_when_it_arrives_later(client, submit):
    submit("Flagged First", "URGENT", LOW)
    submit("Critical Later", "CRITICAL", CONFIDENT)
    assert [r["patient_name"] for r in _queue(client)] == [
        "Critical Later",
        "Flagged First",
    ]


def test_a_low_confidence_critical_stays_in_the_critical_band(client, submit):
    submit("Flagged Routine", "ROUTINE", LOW)
    critical = submit("Unsure Critical", "CRITICAL", 0.4)
    rows = _queue(client)
    assert rows[0]["patient_name"] == "Unsure Critical"
    assert rows[0]["band"] == "CRITICAL"
    assert rows[0]["requires_human_review"] is True
    assert critical["queue_position"] == 1


def test_arrival_order_within_needs_review_ignores_the_predicted_class(client, submit):
    submit("Flagged Routine Earlier", "ROUTINE", LOW)
    submit("Flagged Urgent Later", "URGENT", LOW)
    assert [r["patient_name"] for r in _queue(client)] == [
        "Flagged Routine Earlier",
        "Flagged Urgent Later",
    ]


def test_the_band_label_says_what_it_means_to_a_clinician(client, submit):
    submit("Flagged", "ROUTINE", LOW)
    submit("Confident", "ROUTINE", CONFIDENT)
    flagged, confident = _queue(client)
    assert flagged["band_label"] == NEEDS_REVIEW_LABEL
    assert confident["band_label"] != NEEDS_REVIEW_LABEL


def test_every_single_entry_position_agrees_with_the_list(client, submit):
    submit("Routine Sure", "ROUTINE", CONFIDENT)
    submit("Routine Unsure", "ROUTINE", LOW)
    submit("Urgent Sure", "URGENT", CONFIDENT)
    submit("Critical Sure", "CRITICAL", CONFIDENT)
    for row in _queue(client):
        single = client.get(f"/api/v1/queue/{row['id']}").json()
        assert single["queue_position"] == row["queue_position"], row["patient_name"]
        assert single["band"] == row["band"]


def test_the_configured_threshold_decides_band_membership(client, submit, monkeypatch):
    from app.core.config import settings

    submit("Earlier Routine", "ROUTINE", CONFIDENT)
    submit("Later Routine", "ROUTINE", 0.8)
    assert [r["band"] for r in _queue(client)] == ["ROUTINE", "ROUTINE"]

    monkeypatch.setattr(settings, "MODEL_CONFIDENCE_THRESHOLD", 0.85)
    rows = _queue(client)
    assert [r["patient_name"] for r in rows] == ["Later Routine", "Earlier Routine"]
    assert [r["band"] for r in rows] == ["NEEDS_REVIEW", "ROUTINE"]


# ── Property test ─────────────────────────────────────────────────────────────
BAND_RANK = {"CRITICAL": 1, "NEEDS_REVIEW": 2, "URGENT": 3, "ROUTINE": 4}
CONFIDENCES = (0.2, LOW, 0.7499, 0.75, 0.8, CONFIDENT, 0.99)


def _expected_band(row: dict) -> str:
    if row["urgency_level"] == "CRITICAL":
        return "CRITICAL"
    return "NEEDS_REVIEW" if row["requires_human_review"] else row["urgency_level"]


def test_property_no_flagged_case_is_ever_below_an_unflagged_non_critical_case(
    client, submit, db
):
    """Random arrival sequences, any mix of classes and flags, seeded and reproducible."""
    from app.models.queue import Queue, QueueStatus
    from sqlalchemy import update

    seed = 20260914
    rng = random.Random(seed)
    for sequence in range(30):
        arrivals = [
            (rng.choice(("CRITICAL", "URGENT", "ROUTINE")), rng.choice(CONFIDENCES))
            for _ in range(rng.randint(1, 10))
        ]
        for k, (urgency, confidence) in enumerate(arrivals):
            submit(f"Seq{sequence} Arrival{k}", urgency, confidence)
        rows = _queue(client)
        context = f"seed {seed}, sequence {sequence}, arrivals {arrivals}"

        assert len(rows) == len(arrivals), context
        assert [r["queue_position"] for r in rows] == list(range(1, len(rows) + 1)), (
            context
        )
        for row in rows:
            assert row["band"] == _expected_band(row), context
        for i, upper in enumerate(rows):
            for lower in rows[i + 1 :]:
                # The requirement: a flagged case never below an unflagged non-CRITICAL one.
                assert not (
                    lower["requires_human_review"]
                    and not upper["requires_human_review"]
                    and upper["urgency_level"] != "CRITICAL"
                ), context
                # CRITICAL still outranks everything.
                assert not (
                    lower["urgency_level"] == "CRITICAL"
                    and upper["urgency_level"] != "CRITICAL"
                ), context
                # Bands never go backwards; arrival order within a band.
                assert BAND_RANK[upper["band"]] <= BAND_RANK[lower["band"]], context
                if upper["band"] == lower["band"]:
                    assert upper["queue_number"] < lower["queue_number"], context

        db.execute(update(Queue).values(status=QueueStatus.CANCELLED))
        db.commit()
