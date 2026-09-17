"""Publishing a CRITICAL to the alert topic (step 4).

WHAT THIS MUST NOT DO is more important than what it does. Kafka is the latency
half of the design; the alert is already durable in Postgres before any publish
is attempted. So:

  * a broker outage must not fail a triage, because a clinical record must not
    depend on a message bus being up;
  * the publish happens AFTER the transaction commits, following the SMS
    precedent, so it cannot roll one back;
  * it must not block the request, because a hung broker would otherwise become
    a hung triage endpoint.

THE TOPIC CARRIES NO PERSONAL DATA AT ALL: no symptom text, no phone, no name.
Only identifiers, urgency and a timestamp. That is stricter than the frame a
doctor's socket receives, deliberately -- a dashboard needs a name and is read
by a clinician treating that patient, while a topic is retained, replicated and
often mirrored into an estate nobody here controls. `test_pii_scan.py` used to
record that this service had no Kafka payloads to scan; that exemption ends
here, and the scan is extended to cover them.
"""

from __future__ import annotations

import pytest

CRITICAL_PHRASE = "mfite ububabare bw'igituza"
ROUTINE_PHRASE = "umutwe urandya cyane"


@pytest.fixture
def recorded(monkeypatch):
    """Capture what would be published, without a broker."""
    from app.core import alert_stream

    alert_stream.reset_producer()
    sent: list[tuple[str, dict]] = []

    class Recorder:
        def send(self, topic, value=None, key=None):
            sent.append((topic, value))

        def flush(self, timeout=None):
            return None

    monkeypatch.setattr(alert_stream, "_build_producer", lambda: Recorder())
    yield sent
    alert_stream.reset_producer()


@pytest.fixture
def broker_down(monkeypatch):
    """A broker that cannot be reached at all."""
    from app.core import alert_stream

    alert_stream.reset_producer()

    def refuse():
        raise OSError("no route to broker")

    monkeypatch.setattr(alert_stream, "_build_producer", refuse)
    yield
    alert_stream.reset_producer()


def _triage(client, patient_factory, phrase: str = CRITICAL_PHRASE):
    patient = patient_factory()
    return client.post(
        "/api/v1/triage", json={"patient_id": patient["id"], "symptoms_input": phrase}
    )


# ── What is published ────────────────────────────────────────────────────


def test_a_critical_is_published(client, patient_factory, recorded):
    response = _triage(client, patient_factory, CRITICAL_PHRASE)
    assert response.status_code == 201
    assert len(recorded) == 1
    topic, payload = recorded[0]
    assert topic == "kinyamed_alerts"
    assert payload["queue_id"] == response.json()["queue_id"]
    assert payload["urgency"] == "CRITICAL"


def test_a_routine_triage_publishes_nothing(client, patient_factory, recorded):
    """The topic is for alerts, not for traffic."""
    assert _triage(client, patient_factory, ROUTINE_PHRASE).status_code == 201
    assert recorded == []


def test_the_payload_carries_no_symptom_text(client, patient_factory, recorded):
    _triage(client, patient_factory, CRITICAL_PHRASE)
    assert CRITICAL_PHRASE not in str(recorded)


def test_the_payload_carries_no_personal_data_at_all(
    client, patient_factory, recorded, db
):
    """Stricter than the socket frame, deliberately.

    A dashboard needs a name and its audience is a clinician looking at that
    patient. A topic is retained, replicated and often mirrored into an estate
    nobody here controls, and its audience is whoever has read access in five
    years. The consumer has a database connection and resolves the name itself.
    """
    import re

    from app.models.patient import Patient
    from sqlalchemy import select

    _triage(client, patient_factory, CRITICAL_PHRASE)
    text = str(recorded)

    assert not re.search(r"(?<![\w*+])\+?\d(?:[ \-]?\d){8,14}(?!\w)", text), (
        "a phone-shaped number reached the alert topic"
    )
    for patient in db.scalars(select(Patient)).all():
        assert patient.name not in text, (
            f"the patient's name reached the alert topic: {patient.name!r}"
        )


# ── Degradation (ENGINEERING_SPEC §6.3) ──────────────────────────────────


def test_a_triage_succeeds_when_the_broker_is_down(
    client, patient_factory, broker_down
):
    """A clinical record must not depend on a message bus."""
    response = _triage(client, patient_factory, CRITICAL_PHRASE)
    assert response.status_code == 201, response.text


def test_the_alert_is_still_outstanding_when_the_broker_is_down(
    client, patient_factory, broker_down, db, user_factory
):
    """Nothing is lost: the backfill does not read from Kafka."""
    from app.models.doctor import Doctor
    from app.models.user import UserRole
    from app.services import alerts

    record = Doctor(name="Dr Down", email="dr.down@kinyamed.rw", is_on_duty=True)
    db.add(record)
    db.commit()
    doctor = user_factory(UserRole.DOCTOR, doctor_id=record.id)

    response = _triage(client, patient_factory, CRITICAL_PHRASE)
    db.expire_all()
    owed = [e.id for e in alerts.outstanding_for(db, user_id=doctor.id)]
    assert response.json()["queue_id"] in owed


def test_a_publish_failure_is_logged_once_not_per_request(
    client, patient_factory, broker_down, capsys
):
    """A broker outage during a busy clinic must not bury the logs."""
    for _ in range(3):
        _triage(client, patient_factory, CRITICAL_PHRASE)
    captured = capsys.readouterr()
    assert captured.out.count("alert_stream_unavailable") <= 1


# ── Readiness reports it, and does not gate on it ────────────────────────


def test_readiness_reports_kafka(client, broker_down):
    response = client.get("/health/ready")
    assert "kafka" in response.json()


def test_readiness_does_not_gate_on_kafka(client, broker_down):
    """A transport outage must not take the pod out of rotation."""
    response = client.get("/health/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"
