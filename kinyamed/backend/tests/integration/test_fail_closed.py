"""Triage fails closed when the trained model cannot classify.

There is exactly one thing allowed to put an urgency on a patient: the trained
model. When it is absent, or when it raises, the endpoint must refuse with 503,
tell staff to triage manually, and write nothing. A report that is not written
cannot sit in the queue looking like an assessment.

These tests use no classifier double. The "absent" case runs the real
selection path with TRIAGE_MODEL_PATH unset, which is how the test process is
configured.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def no_model_client(client):
    """The admin client with the test classifier removed: the real, absent path."""
    import main
    from app.routes.v1.triage import get_triage_classifier

    main.app.dependency_overrides.pop(get_triage_classifier, None)
    return client


def _clinical_row_counts(db) -> tuple[int, int, int]:
    from app.models.queue import Queue
    from app.models.symptom_report import SymptomReport
    from app.models.triage_result import TriageResult

    return (
        db.query(SymptomReport).count(),
        db.query(TriageResult).count(),
        db.query(Queue).count(),
    )


def test_the_test_process_really_has_no_model():
    """Guard for every test below: if a model were configured, they would prove nothing."""
    from app.services import triage_service

    triage_service.get_classifier.cache_clear()
    assert triage_service.get_classifier() is None


def test_absent_model_returns_503_with_retry_after(no_model_client, patient_factory):
    patient = patient_factory()
    response = no_model_client.post(
        "/api/v1/triage",
        json={"patient_id": patient["id"], "symptoms_input": "sinshobora guhumeka"},
    )

    assert response.status_code == 503, response.text
    retry_after = response.headers.get("Retry-After")
    assert retry_after is not None and int(retry_after) > 0


def test_absent_model_tells_staff_to_triage_manually(no_model_client, patient_factory):
    patient = patient_factory()
    body = no_model_client.post(
        "/api/v1/triage",
        json={"patient_id": patient["id"], "symptoms_input": "sinshobora guhumeka"},
    ).json()

    error = body["error"]
    assert error["code"] == "TRIAGE_MODEL_UNAVAILABLE"
    assert error["details"]["manual_triage_required"] is True
    assert error["details"]["report_saved"] is False
    assert "manual" in error["message"].lower()


def test_absent_model_returns_no_classification(no_model_client, patient_factory):
    """No urgency, confidence or patient-facing sentence may leave the service."""
    patient = patient_factory()
    body = no_model_client.post(
        "/api/v1/triage",
        json={"patient_id": patient["id"], "symptoms_input": "sinshobora guhumeka"},
    ).json()

    flat = str(body)
    for leaked in ("urgency_level", "CRITICAL", "URGENT", "ROUTINE", "confidence"):
        assert leaked not in flat, f"{leaked!r} appeared in a response with no model"
    for field in ("patient_response", "ai_response_rw", "queue_number"):
        assert field not in body


def test_absent_model_writes_nothing(no_model_client, patient_factory, db):
    patient = patient_factory()
    no_model_client.post(
        "/api/v1/triage",
        json={"patient_id": patient["id"], "symptoms_input": "sinshobora guhumeka"},
    )
    assert _clinical_row_counts(db) == (0, 0, 0)


def test_an_inference_failure_fails_closed(client, patient_factory, db):
    """A model that is loaded but raises is treated exactly like no model."""
    import main
    from app.routes.v1.triage import get_triage_classifier

    class _Exploding:
        def classify(self, text: str):
            raise RuntimeError("simulated forward-pass failure")

    main.app.dependency_overrides[get_triage_classifier] = lambda: _Exploding()
    patient = patient_factory()
    response = client.post(
        "/api/v1/triage",
        json={"patient_id": patient["id"], "symptoms_input": "sinshobora guhumeka"},
    )

    assert response.status_code == 503, response.text
    assert response.json()["error"]["code"] == "TRIAGE_MODEL_UNAVAILABLE"
    assert "Retry-After" in response.headers
    assert "simulated" not in response.text, "internal error detail leaked"
    assert _clinical_row_counts(db) == (0, 0, 0)


def test_the_keyword_matcher_is_gone():
    """Structural: the non-model classification path no longer exists to be selected."""
    from app.services import model_classifier, triage_service

    for name in ("KeywordClassifier", "CRITICAL_TERMS", "URGENT_TERMS"):
        assert not hasattr(triage_service, name), f"{name} still exists"
    assert not hasattr(model_classifier, "KeywordClassifier")


def test_a_batched_inference_timeout_fails_closed_through_the_same_path(
    client, patient_factory, db
):
    """A real BatchedInference whose forward outlasts its timeout. The timeout is not
    a second error path: it surfaces as the same TRIAGE_MODEL_UNAVAILABLE 503 as a
    missing model, with nothing written. Characterisation: the path already existed."""
    import threading

    import main
    from app.routes.v1.triage import get_triage_classifier
    from app.services.model_classifier import BatchedInference, ModelClassifier

    release = threading.Event()

    def stuck_forward(texts: list[str]) -> list[list[float]]:
        release.wait(5)
        return [[1.0, 0.0, 0.0] for _ in texts]

    engine = BatchedInference(
        stuck_forward, max_batch_size=1, max_wait_ms=0, timeout_s=0.2
    )
    classifier = ModelClassifier.with_engine(engine)
    main.app.dependency_overrides[get_triage_classifier] = lambda: classifier
    try:
        patient = patient_factory()
        response = client.post(
            "/api/v1/triage",
            json={"patient_id": patient["id"], "symptoms_input": "sinshobora guhumeka"},
        )
    finally:
        release.set()
        engine.close()

    assert response.status_code == 503, response.text
    assert response.json()["error"]["code"] == "TRIAGE_MODEL_UNAVAILABLE"
    assert "Retry-After" in response.headers
    assert "within" not in response.text, "internal timeout detail leaked"
    assert _clinical_row_counts(db) == (0, 0, 0)
