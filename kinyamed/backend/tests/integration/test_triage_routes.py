"""The core guarantee: a more urgent patient is seen first."""

from __future__ import annotations


def _triage(client, patient_id: int, symptoms: str) -> dict:
    response = client.post(
        "/api/v1/triage", json={"patient_id": patient_id, "symptoms_input": symptoms}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_critical_patient_overtakes_earlier_routine_patients(client, patient_factory):
    routine_first = patient_factory(name="Routine Arrival")
    critical_later = patient_factory(name="Critical Arrival")

    _triage(client, routine_first["id"], "ndumva nkeneye kubonana na muganga")
    critical = _triage(client, critical_later["id"], "mfite ububabare bw'igituza")

    assert critical["urgency_level"] == "CRITICAL"
    assert critical["queue_position"] == 1, "a critical case must jump the queue"

    queue = client.get("/api/v1/queue").json()["items"]
    assert [item["patient_name"] for item in queue] == ["Critical Arrival", "Routine Arrival"]
    assert [item["queue_position"] for item in queue] == [1, 2]


def test_equal_urgency_keeps_arrival_order(client, patient_factory):
    first = patient_factory(name="First Fever")
    second = patient_factory(name="Second Fever")

    _triage(client, first["id"], "mfite umuriro mwinshi")
    _triage(client, second["id"], "mfite umuriro mwinshi")

    queue = client.get("/api/v1/queue").json()["items"]
    assert [item["patient_name"] for item in queue] == ["First Fever", "Second Fever"]


def test_critical_patient_is_quoted_no_wait(client, patient_factory):
    patient = patient_factory()
    result = _triage(client, patient["id"], "kuva amaraso menshi")
    assert result["estimated_wait"] == 0


def test_positions_close_up_when_a_patient_is_removed(client, patient_factory):
    first = patient_factory(name="Leaves")
    second = patient_factory(name="Stays")
    _triage(client, first["id"], "mfite umuriro")
    _triage(client, second["id"], "mfite umuriro")

    queue = client.get("/api/v1/queue").json()["items"]
    assert client.delete(f"/api/v1/queue/{queue[0]['id']}").status_code == 200

    remaining = client.get("/api/v1/queue").json()["items"]
    assert [item["patient_name"] for item in remaining] == ["Stays"]
    assert remaining[0]["queue_position"] == 1, "positions must be recomputed, not stale"


def test_queue_numbers_are_never_reused(client, patient_factory):
    first = patient_factory(name="One")
    second = patient_factory(name="Two")
    first_ticket = _triage(client, first["id"], "mfite umuriro")["queue_number"]

    queue = client.get("/api/v1/queue").json()["items"]
    client.delete(f"/api/v1/queue/{queue[0]['id']}")

    second_ticket = _triage(client, second["id"], "mfite umuriro")["queue_number"]
    assert second_ticket != first_ticket, "ticket numbers must come from a sequence"


def test_triage_records_the_full_chain(client, patient_factory, db):
    from app.models.queue import Queue
    from app.models.symptom_report import SymptomReport
    from app.models.triage_result import TriageResult

    patient = patient_factory()
    _triage(client, patient["id"], "mfite umuriro mwinshi")

    assert db.query(SymptomReport).count() == 1
    assert db.query(TriageResult).count() == 1
    assert db.query(Queue).count() == 1
