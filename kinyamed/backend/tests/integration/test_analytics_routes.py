"""Analytics correctness."""

from __future__ import annotations


def _triage(client, patient_factory, symptoms: str) -> dict:
    patient = patient_factory()
    return client.post(
        "/api/v1/triage", json={"patient_id": patient["id"], "symptoms_input": symptoms}
    ).json()


def test_summary_counts_each_acuity(client, patient_factory):
    _triage(client, patient_factory, "mfite ububabare bw'igituza")
    _triage(client, patient_factory, "mfite umuriro mwinshi")
    _triage(client, patient_factory, "ndumva nkeneye kubonana na muganga")

    body = client.get("/api/v1/analytics/summary").json()
    assert (body["critical_cases"], body["urgent_cases"], body["routine_cases"]) == (1, 1, 1)
    assert body["total_patients"] == 3
    assert body["queue_waiting"] == 3


def test_urgency_breakdown_with_no_data_returns_zeroes(client):
    body = client.get("/api/v1/analytics/urgency-breakdown").json()
    assert body["total"] == 0
    assert body["critical"] == {"count": 0, "percentage": 0.0}


def test_completed_today_counts_only_completed_entries(client, patient_factory):
    _triage(client, patient_factory, "mfite umuriro")
    _triage(client, patient_factory, "mfite umuriro")
    entry = client.get("/api/v1/queue").json()["items"][0]

    before = client.get("/api/v1/analytics/queue-performance").json()
    assert before["completed_today"] == 0, "nothing has been completed yet"

    client.patch(f"/api/v1/queue/{entry['id']}/status", json={"status": "IN_PROGRESS"})
    client.patch(f"/api/v1/queue/{entry['id']}/status", json={"status": "DONE"})

    after = client.get("/api/v1/analytics/queue-performance").json()
    assert after["completed_today"] == 1
    assert after["currently_waiting"] == 1


def test_snapshot_is_upserted_per_day(client, patient_factory):
    _triage(client, patient_factory, "mfite umuriro")
    first = client.post("/api/v1/analytics/daily/snapshot").json()
    _triage(client, patient_factory, "mfite ububabare bw'igituza")
    second = client.post("/api/v1/analytics/daily/snapshot").json()

    assert first["id"] == second["id"], "re-running must update today's row, not duplicate it"
    assert second["total_triaged"] == 2
    listing = client.get("/api/v1/analytics/daily").json()
    assert listing["total"] == 1
    assert len(listing["items"]) == 1


def test_snapshot_records_patients_and_triage_separately(client, patient_factory):
    """total_patients previously held the triage count."""
    patient_factory()
    patient_factory()
    _triage(client, patient_factory, "mfite umuriro")

    snapshot = client.post("/api/v1/analytics/daily/snapshot").json()
    assert snapshot["total_patients"] == 3
    assert snapshot["total_triaged"] == 1


def test_bulk_delete_requires_confirmation(client):
    client.post("/api/v1/analytics/daily/snapshot")
    assert client.delete("/api/v1/analytics/daily").status_code == 409
    assert client.delete("/api/v1/analytics/daily", params={"confirm": "CLEAR_ALL"}).status_code == 204
