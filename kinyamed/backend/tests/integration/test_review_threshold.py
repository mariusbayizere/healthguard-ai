"""The configured confidence threshold decides requires_human_review.

MODEL_CONFIDENCE_THRESHOLD existed in configuration and was read by no code.
Below it, the triage is flagged for a clinician, and the response says why.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def classify_with_confidence(client):
    """Serve every triage at a chosen confidence, urgency fixed at URGENT."""
    import main
    from app.models.triage_result import UrgencyLevel
    from app.routes.v1.triage import get_triage_classifier
    from app.services.triage_service import Classification

    def _set(confidence: float) -> None:
        class _Fixed:
            def classify(self, text: str) -> Classification:
                return Classification(
                    urgency=UrgencyLevel.URGENT, confidence=confidence
                )

        main.app.dependency_overrides[get_triage_classifier] = lambda: _Fixed()

    return _set


def _triage(client, patient_factory) -> dict:
    patient = patient_factory()
    response = client.post(
        "/api/v1/triage",
        json={"patient_id": patient["id"], "symptoms_input": "any description"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_below_threshold_requires_human_review(
    client, patient_factory, classify_with_confidence
):
    classify_with_confidence(0.598)
    body = _triage(client, patient_factory)

    assert body["requires_human_review"] is True
    assert "0.60" in body["review_reason"]
    assert "0.75" in body["review_reason"]


def test_at_or_above_threshold_does_not(
    client, patient_factory, classify_with_confidence
):
    for confidence in (0.75, 0.9):
        classify_with_confidence(confidence)
        body = _triage(client, patient_factory)
        assert body["requires_human_review"] is False, confidence
        assert body["review_reason"] is None


def test_the_threshold_is_read_from_configuration(
    client, patient_factory, classify_with_confidence, monkeypatch
):
    from app.core.config import settings

    monkeypatch.setattr(settings, "MODEL_CONFIDENCE_THRESHOLD", 0.95)
    classify_with_confidence(0.9)
    body = _triage(client, patient_factory)
    assert body["requires_human_review"] is True
    assert "0.95" in body["review_reason"]


def test_the_flag_reaches_the_doctor_queue(
    client, patient_factory, classify_with_confidence
):
    classify_with_confidence(0.5)
    created = _triage(client, patient_factory)

    row = next(
        item
        for item in client.get("/api/v1/queue").json()["items"]
        if item["id"] == created["queue_id"]
    )
    assert row["requires_human_review"] is True
    assert row["confidence_score"] == pytest.approx(0.5)
    assert row["review_reason"]


def test_the_read_path_agrees(client, patient_factory, classify_with_confidence):
    classify_with_confidence(0.4)
    created = _triage(client, patient_factory)
    fetched = client.get(f"/api/v1/triage/{created['triage_id']}").json()
    assert fetched["requires_human_review"] is True


def test_the_review_flag_does_not_change_the_patient_message(
    client, patient_factory, classify_with_confidence
):
    import re

    classify_with_confidence(0.3)
    low = _triage(client, patient_factory)["patient_response"]
    classify_with_confidence(0.99)
    high = _triage(client, patient_factory)["patient_response"]
    assert re.sub(r"\d+", "#", low) == re.sub(r"\d+", "#", high)
