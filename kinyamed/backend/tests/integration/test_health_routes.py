"""Probe and application-level behaviour."""

from __future__ import annotations


def test_health_is_a_liveness_probe(client):
    """Liveness must answer without touching the database."""
    body = client.get("/health").json()
    assert body["status"] == "healthy"
    assert body["service"]
    assert "database" not in body


def test_ready_reports_dependency_state(client):
    body = client.get("/ready").json()
    assert body["status"] == "ready"
    assert body["database"] == "ok"
    assert isinstance(body["model"], bool)


def test_health_ready_reports_model_false_without_a_model(client):
    """The test process has no model, so readiness must say so, as a boolean."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["model"] is False
    assert body["database"] == "ok"
    # No model is NOT "not ready": the queue and records still work, and the
    # dashboards need the API up to show the triage-offline banner.
    assert body["status"] == "ready"


def test_health_ready_reports_model_true_when_a_model_is_loaded(client, monkeypatch):
    from app.services import triage_service

    monkeypatch.setattr(triage_service, "get_classifier", lambda: object())
    assert client.get("/health/ready").json()["model"] is True


def test_ready_and_health_ready_agree(client):
    assert client.get("/ready").json() == client.get("/health/ready").json()


def test_root_reports_service_metadata(client):
    body = client.get("/").json()
    assert body["status"] == "ok"
    assert body["service"]


def test_openapi_schema_builds(client):
    """A broken response_model would fail here rather than in production."""
    schema = client.get("/openapi.json").json()
    assert "/api/v1/queue" in schema["paths"]
    assert "/api/v1/patients" in schema["paths"]


def test_errors_use_the_shared_envelope_with_a_code(client):
    body = client.get("/api/v1/patients/999999").json()
    assert body["error"]["code"] == "PATIENT_NOT_FOUND"
    assert body["error"]["message"]
    assert body["error"]["details"]["resource"] == "Patient"


def test_responses_carry_a_request_id(client):
    response = client.get("/api/v1/patients")
    assert response.headers["X-Request-ID"]
    assert float(response.headers["X-Response-Time-ms"]) >= 0


def test_supplied_request_id_is_echoed(client):
    response = client.get("/api/v1/patients", headers={"X-Request-ID": "audit-trace-1"})
    assert response.headers["X-Request-ID"] == "audit-trace-1"
