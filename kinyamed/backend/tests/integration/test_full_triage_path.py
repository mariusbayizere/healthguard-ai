"""The whole path a patient actually travels, end to end.

The unit tests cover each piece. These cover the SEAMS, which is where this
system has actually broken: an import that was never bound, a response field
that existed in the schema but was never populated by the route, an SMS
composer that returned text nobody authored.

Every test here asserts something a clinic would notice.
"""

from __future__ import annotations


def _triage(client, patient_id: int, text: str):
    response = client.post(
        "/api/v1/triage",
        json={"patient_id": patient_id, "symptoms_input": text},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_symptom_description_reaches_a_queue_position(client, patient_factory):
    """Intake to queue, in one call, with everything the frontend renders."""
    patient = patient_factory(name="Uwimana Alice", phone="+250780000001")
    body = _triage(client, patient["id"], "mfite umuriro mwinshi kandi ndakorora")

    # Each of these is read by a specific element of frontend/index.html. A
    # missing one renders as "undefined" rather than failing, which is why they
    # are asserted here rather than left to the eye.
    for field in (
        "triage_id",
        "urgency_level",
        "queue_number",
        "queue_position",
        "language_detected",
        "patient_response",
        "response_pending",
    ):
        assert field in body, f"{field} missing; the intake view renders it"

    assert body["urgency_level"] in {"CRITICAL", "URGENT", "ROUTINE"}
    assert body["queue_position"] >= 1
    assert body["queue_number"] >= 1


def test_the_queue_orders_critical_before_routine(client, patient_factory):
    """The one ordering guarantee the whole system exists to provide.

    Deliberately submits ROUTINE first, so a queue that merely preserved
    arrival order would fail.
    """
    routine = patient_factory(name="Routine First", phone="+250780000002")
    critical = patient_factory(name="Critical Second", phone="+250780000003")

    _triage(client, routine["id"], "ndashaka ko bapima amaraso")
    _triage(
        client,
        critical["id"],
        "mu gituza harandya cyane kandi sinshobora guhumeka neza",
    )

    rows = client.get("/api/v1/queue").json()
    rows = rows if isinstance(rows, list) else rows.get("items", [])
    assert rows, "queue is empty after two triages"

    # Imported, not restated. A test with its own copy of the ordering passes
    # when the ordering is wrong everywhere consistently, which is the failure
    # it exists to catch.
    from app.models.triage_result import UrgencyLevel

    priorities = [UrgencyLevel(r["urgency_level"]).priority for r in rows]
    assert priorities == sorted(priorities), (
        f"queue is not urgency-ordered: {[r['urgency_level'] for r in rows]}"
    )


def test_a_patient_response_is_never_invented(client, patient_factory):
    """Either speaker-authored text, or an explicit pending state. Never both,
    never neither, and never a placeholder.

    This is the invariant the whole response-template design rests on, and it
    is the one a future refactor is most likely to break by adding a
    "sensible default".
    """
    patient = patient_factory(name="Nkurunziza Jean", phone="+250780000004")
    body = _triage(client, patient["id"], "mfite umuriro")

    if body["response_pending"]:
        assert not body.get("patient_response"), (
            "a pending response must be empty; anything else is a placeholder "
            "being served as if a speaker had written it"
        )
        assert body.get("response_pending_reason"), (
            "a pending response must say why, or staff cannot act on it"
        )
    else:
        assert body["patient_response"].strip(), (
            "not pending, but no text — the endpoint would render blank advice"
        )
        assert "{" not in body["patient_response"], (
            "an unfilled template slot reached the patient-facing field"
        )


def test_triage_is_retrievable_after_creation(client, patient_factory):
    """The frontend links to a triage by id; the read path must agree."""
    patient = patient_factory(name="Mukamana Rose", phone="+250780000005")
    created = _triage(client, patient["id"], "umutwe urandya cyane")

    fetched = client.get(f"/api/v1/triage/{created['triage_id']}")
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["urgency_level"] == created["urgency_level"], (
        "the stored urgency differs from the one returned at creation"
    )


def test_a_doctor_can_be_assigned_and_the_status_advanced(
    client, patient_factory, doctor_factory
):
    """The dashboard's two write actions, against a real queue entry."""
    patient = patient_factory(name="Habimana Eric", phone="+250780000006")
    doctor = doctor_factory(name="Dr Ineza")
    _triage(client, patient["id"], "mfite umuriro mwinshi")

    rows = client.get("/api/v1/queue").json()
    rows = rows if isinstance(rows, list) else rows.get("items", [])
    entry = rows[0]

    assigned = client.patch(
        f"/api/v1/queue/{entry['id']}/assign-doctor",
        json={"doctor_id": doctor["id"]},
    )
    assert assigned.status_code == 200, assigned.text

    advanced = client.patch(
        f"/api/v1/queue/{entry['id']}/status", json={"status": "IN_PROGRESS"}
    )
    assert advanced.status_code == 200, advanced.text
    assert advanced.json()["status"] == "IN_PROGRESS"


def test_an_empty_description_is_rejected_rather_than_triaged(client, patient_factory):
    """A blank submission must not produce an urgency.

    The classifier will happily return a label for an empty string, and that
    label would enter the queue looking exactly like a real assessment.
    """
    patient = patient_factory(name="Blank Case", phone="+250780000007")
    response = client.post(
        "/api/v1/triage", json={"patient_id": patient["id"], "symptoms_input": "   "}
    )
    assert response.status_code in (400, 422), (
        f"blank symptoms produced {response.status_code}; an empty description "
        "must not yield a triage decision"
    )


def test_a_patient_cannot_triage_someone_else(patient_client_factory, patient_factory):
    """Submitting on another patient's behalf is staff-only."""
    victim = patient_factory(name="Other Patient", phone="+250780000008")
    # The factory takes an optional patient_id and creates its own record when
    # given none; it does not take a name.
    attacker_client, attacker_id = patient_client_factory()
    assert attacker_id != victim["id"]
    response = attacker_client.post(
        "/api/v1/triage",
        json={"patient_id": victim["id"], "symptoms_input": "mfite umuriro"},
    )
    assert response.status_code in (401, 403), (
        f"a patient triaged another patient and got {response.status_code}"
    )
