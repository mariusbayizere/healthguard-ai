"""Which CRITICAL alerts a doctor is owed on reconnect (no Kafka, no WebSocket).

This is step 2 of reports/ALERT_DELIVERY_DESIGN.md, and it is deliberately
testable with no transport at all: the safety property -- a doctor who drops
does not miss a CRITICAL -- lives entirely in this query. Wiring it to a socket
later cannot make it correct, and cannot make it wrong.

BOUNDED BY STATE, NOT BY TIME. There is no "since yesterday" clause anywhere
here. A CRITICAL still waiting after a week is still an emergency; one seen and
discharged an hour ago is history. A time window would have suppressed exactly
the row that matters most.

THE DISTINCTION THIS FILE GUARDS HARDEST is that acknowledging an alert is not
a clinical act. `test_acknowledging_never_changes_the_queue_status` is the one
assertion here whose failure would corrupt the audit trail and any future
retraining set, quietly, by making "dismissed a popup" indistinguishable from
"saw the patient".
"""

from __future__ import annotations

import pytest

CRITICAL_PHRASE = "mfite ububabare bw'igituza"  # scripted CRITICAL
ROUTINE_PHRASE = "umutwe urandya cyane"  # scripted ROUTINE


def _triage(client, patient_factory, phrase: str) -> dict:
    patient = patient_factory()
    response = client.post(
        "/api/v1/triage",
        json={"patient_id": patient["id"], "symptoms_input": phrase},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _owed(db, user_id: int) -> list[int]:
    from app.services import alerts

    db.expire_all()
    return [entry.id for entry in alerts.outstanding_for(db, user_id=user_id)]


@pytest.fixture
def doctor(db, user_factory):
    from app.models.doctor import Doctor
    from app.models.user import UserRole

    record = Doctor(name="Dr Alert", email="dr.alert@kinyamed.rw")
    db.add(record)
    db.commit()
    return user_factory(UserRole.DOCTOR, doctor_id=record.id)


# ── What is owed ─────────────────────────────────────────────────────────


def test_a_waiting_critical_is_owed(client, patient_factory, db, doctor):
    entry = _triage(client, patient_factory, CRITICAL_PHRASE)
    assert entry["queue_id"] in _owed(db, doctor.id)


def test_a_routine_entry_is_not_an_alert(client, patient_factory, db, doctor):
    entry = _triage(client, patient_factory, ROUTINE_PHRASE)
    assert entry["queue_id"] not in _owed(db, doctor.id)


def test_a_completed_critical_is_history_not_an_alert(
    client, patient_factory, db, doctor
):
    entry = _triage(client, patient_factory, CRITICAL_PHRASE)
    client.patch(
        f"/api/v1/queue/{entry['queue_id']}/status", json={"status": "IN_PROGRESS"}
    )
    client.patch(f"/api/v1/queue/{entry['queue_id']}/status", json={"status": "DONE"})
    assert entry["queue_id"] not in _owed(db, doctor.id)


def test_a_cancelled_critical_is_not_an_alert(client, patient_factory, db, doctor):
    entry = _triage(client, patient_factory, CRITICAL_PHRASE)
    client.delete(f"/api/v1/queue/{entry['queue_id']}")
    assert entry["queue_id"] not in _owed(db, doctor.id)


def test_an_in_progress_critical_is_still_owed(client, patient_factory, db, doctor):
    """Being seen is not the same as the alert having been received."""
    entry = _triage(client, patient_factory, CRITICAL_PHRASE)
    client.patch(
        f"/api/v1/queue/{entry['queue_id']}/status", json={"status": "IN_PROGRESS"}
    )
    assert entry["queue_id"] in _owed(db, doctor.id)


def test_age_alone_never_removes_an_alert(client, patient_factory, db, doctor):
    """The clause that is deliberately absent.

    Written as an explicit assertion rather than a comment, because "we did not
    add a time window" is exactly the kind of decision that gets undone by
    somebody optimising a query later.
    """
    from datetime import UTC, datetime, timedelta

    from app.models.queue import Queue

    entry = _triage(client, patient_factory, CRITICAL_PHRASE)
    row = db.get(Queue, entry["queue_id"])
    row.created_at = datetime.now(UTC) - timedelta(days=30)
    db.commit()

    assert entry["queue_id"] in _owed(db, doctor.id), (
        "a month-old CRITICAL still waiting was dropped; a time bound has crept in"
    )


# ── Acknowledgement ──────────────────────────────────────────────────────


def test_acknowledging_removes_it_for_that_doctor(client, patient_factory, db, doctor):
    from app.services import alerts

    entry = _triage(client, patient_factory, CRITICAL_PHRASE)
    alerts.acknowledge(db, queue_id=entry["queue_id"], user_id=doctor.id)
    assert entry["queue_id"] not in _owed(db, doctor.id)


def test_acknowledging_leaves_it_owed_to_everybody_else(
    client, patient_factory, db, doctor, user_factory
):
    """Shift change: the incoming doctor must still see it."""
    from app.models.user import UserRole
    from app.services import alerts

    incoming = user_factory(UserRole.DOCTOR, email="incoming@kinyamed.rw")
    entry = _triage(client, patient_factory, CRITICAL_PHRASE)
    alerts.acknowledge(db, queue_id=entry["queue_id"], user_id=doctor.id)

    assert entry["queue_id"] not in _owed(db, doctor.id)
    assert entry["queue_id"] in _owed(db, incoming.id), (
        "one doctor's dismissal hid a live CRITICAL from another"
    )


def test_acknowledging_twice_is_not_an_error(client, patient_factory, db, doctor):
    """A reconnect can re-send; the client can re-acknowledge."""
    from app.services import alerts

    entry = _triage(client, patient_factory, CRITICAL_PHRASE)
    alerts.acknowledge(db, queue_id=entry["queue_id"], user_id=doctor.id)
    alerts.acknowledge(db, queue_id=entry["queue_id"], user_id=doctor.id)
    assert entry["queue_id"] not in _owed(db, doctor.id)


# ── THE distinction ──────────────────────────────────────────────────────


def test_acknowledging_never_changes_the_queue_status(
    client, patient_factory, db, doctor
):
    """Acknowledgement is not a clinical act, and must never look like one.

    If this fails, "a doctor dismissed a popup" becomes indistinguishable from
    "a doctor saw the patient" in the queue record, in every audit built on it,
    and in any future retraining set that reads dispositions. It would be
    silent, and it would be wrong in the direction that matters.
    """
    from app.models.queue import Queue
    from app.services import alerts

    entry = _triage(client, patient_factory, CRITICAL_PHRASE)
    row = db.get(Queue, entry["queue_id"])
    before = (row.status, row.started_at, row.completed_at, row.doctor_id)

    alerts.acknowledge(db, queue_id=entry["queue_id"], user_id=doctor.id)

    db.expire_all()
    row = db.get(Queue, entry["queue_id"])
    assert (row.status, row.started_at, row.completed_at, row.doctor_id) == before, (
        "acknowledging an alert mutated the clinical record"
    )


def test_acknowledgement_is_recorded_separately_from_the_queue(
    client, patient_factory, db, doctor
):
    """The fact lives in its own table, not as a column on queue."""
    from app.models.queue import Queue

    assert not hasattr(Queue, "acknowledged_at"), (
        "acknowledgement moved onto queue, where it can be mistaken for a "
        "clinical disposition"
    )


# ── Measurement without policy (open question 1) ─────────────────────────


def test_acknowledged_and_still_waiting_is_measurable(
    client, patient_factory, db, doctor
):
    """A query, not an alarm.

    Whether an acknowledged CRITICAL that is still waiting should re-alert, and
    after how long, is a clinical-lead decision nobody here is qualified to
    make. The measurement exists so the question can be answered with data
    rather than intuition; no interval is defaulted and nothing escalates.
    """
    from datetime import timedelta

    from app.services import alerts

    entry = _triage(client, patient_factory, CRITICAL_PHRASE)
    alerts.acknowledge(db, queue_id=entry["queue_id"], user_id=doctor.id)

    # Caller supplies the interval every time. There is no default to inherit.
    immediately = alerts.acknowledged_and_still_waiting(db, longer_than=timedelta(0))
    assert entry["queue_id"] in [row.id for row in immediately]

    later = alerts.acknowledged_and_still_waiting(db, longer_than=timedelta(hours=1))
    assert entry["queue_id"] not in [row.id for row in later]


def test_the_measurement_requires_an_explicit_interval():
    """No default, so no de facto policy can arrive by accident."""
    import inspect

    from app.services import alerts

    parameter = inspect.signature(alerts.acknowledged_and_still_waiting).parameters[
        "longer_than"
    ]
    assert parameter.default is inspect.Parameter.empty, (
        "a default interval is a policy; this function must not carry one"
    )


# ── Fan-out to nobody must not look like delivery ────────────────────────


def test_no_doctor_on_duty_is_reported_not_silent(client, patient_factory, db, doctor):
    """A CRITICAL that reaches zero recipients is a fact somebody must see.

    The alert is not lost -- it stays owed, and the next doctor to connect gets
    it from the backfill. What must not happen is the fan-out reporting the same
    result whether it reached six people or none.
    """
    from app.services import alerts

    doctor.doctor.is_on_duty = False
    db.commit()

    entry = _triage(client, patient_factory, CRITICAL_PHRASE)
    outcome = alerts.recipients_for_broadcast(db)

    assert outcome.count == 0
    assert outcome.reached_nobody is True, (
        "fanning out to nobody reported the same result as delivering"
    )
    # Still owed: nobody received it, so nobody has acknowledged it.
    assert entry["queue_id"] in _owed(db, doctor.id)


def test_an_on_duty_doctor_is_a_recipient(client, patient_factory, db, doctor):
    from app.services import alerts

    doctor.doctor.is_on_duty = True
    db.commit()

    outcome = alerts.recipients_for_broadcast(db)
    assert outcome.count >= 1
    assert outcome.reached_nobody is False
