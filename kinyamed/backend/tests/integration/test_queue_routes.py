"""Queue state machine and doctor assignment."""

from __future__ import annotations


def _queue_entry(client, patient_factory, symptoms: str = "mfite umuriro") -> dict:
    patient = patient_factory()
    client.post("/api/v1/triage", json={"patient_id": patient["id"], "symptoms_input": symptoms})
    return client.get("/api/v1/queue").json()["items"][0]


def test_status_transition_is_validated(client, patient_factory):
    entry = _queue_entry(client, patient_factory)

    started = client.patch(f"/api/v1/queue/{entry['id']}/status", json={"status": "IN_PROGRESS"})
    assert started.status_code == 200
    assert started.json()["started_at"] is not None

    finished = client.patch(f"/api/v1/queue/{entry['id']}/status", json={"status": "DONE"})
    assert finished.status_code == 200
    assert finished.json()["completed_at"] is not None

    reopened = client.patch(f"/api/v1/queue/{entry['id']}/status", json={"status": "WAITING"})
    assert reopened.status_code == 409, "a completed consultation must not reopen"


def test_unknown_status_is_rejected(client, patient_factory):
    entry = _queue_entry(client, patient_factory)
    assert client.patch(f"/api/v1/queue/{entry['id']}/status", json={"status": "NONSENSE"}).status_code == 422


def test_completed_entries_leave_the_live_queue(client, patient_factory):
    entry = _queue_entry(client, patient_factory)
    client.patch(f"/api/v1/queue/{entry['id']}/status", json={"status": "IN_PROGRESS"})
    client.patch(f"/api/v1/queue/{entry['id']}/status", json={"status": "DONE"})
    assert client.get("/api/v1/queue").json()["total"] == 0


def test_assigning_an_unknown_doctor_returns_404(client, patient_factory):
    entry = _queue_entry(client, patient_factory)
    response = client.patch(
        f"/api/v1/queue/{entry['id']}/assign-doctor", json={"doctor_id": 999999}
    )
    assert response.status_code == 404, "the old code raised a foreign-key 500 here"


def test_assigning_an_off_duty_doctor_is_refused(client, patient_factory, doctor_factory):
    doctor = doctor_factory(is_on_duty=False)
    entry = _queue_entry(client, patient_factory)
    response = client.patch(
        f"/api/v1/queue/{entry['id']}/assign-doctor", json={"doctor_id": doctor["id"]}
    )
    assert response.status_code == 409


def test_assignment_starts_the_consultation(client, patient_factory, doctor_factory):
    doctor = doctor_factory()
    entry = _queue_entry(client, patient_factory)
    response = client.patch(
        f"/api/v1/queue/{entry['id']}/assign-doctor", json={"doctor_id": doctor["id"]}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["doctor_id"] == doctor["id"]
    assert body["status"] == "IN_PROGRESS"


def test_removal_preserves_clinical_history(client, patient_factory, db):
    from app.models.triage_result import TriageResult

    entry = _queue_entry(client, patient_factory)
    assert client.delete(f"/api/v1/queue/{entry['id']}").status_code == 200
    assert client.get("/api/v1/queue").json()["total"] == 0
    assert db.query(TriageResult).count() == 1, "cancelling must not delete the triage record"


def test_queue_read_does_not_issue_a_query_per_row(client, patient_factory):
    """The patient chain must be eagerly loaded (previously 3 queries per row)."""
    from sqlalchemy import event

    from app.core.database import engine

    for _ in range(5):
        patient = patient_factory()
        client.post(
            "/api/v1/triage", json={"patient_id": patient["id"], "symptoms_input": "mfite umuriro"}
        )

    statements: list[str] = []

    def _record(conn, cursor, statement, parameters, context, executemany):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", _record)
    try:
        client.get("/api/v1/queue")
    finally:
        event.remove(engine, "before_cursor_execute", _record)

    selects = [s for s in statements if s.lstrip().upper().startswith("SELECT")]
    assert len(selects) <= 4, f"expected a constant number of queries, got {len(selects)}"


def test_missing_queue_entry_returns_404(client):
    assert client.get("/api/v1/queue/999999").status_code == 404
