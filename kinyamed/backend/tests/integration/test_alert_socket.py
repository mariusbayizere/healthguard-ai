"""The alert socket: who may open one, and what they are owed on connect.

TWO PROPERTIES, both exercised through a real WebSocket rather than by calling
the service underneath it.

AUTHENTICATION. A doctor's queue is patient data. A socket that accepts any
connection is the same defect as an endpoint without RBAC, and it is easier to
miss, because nothing about a socket looks like a route decorator. The token is
verified on connect, the role is checked, and a withdrawn token is refused like
any other.

THE TOKEN IS SENT AS THE FIRST FRAME, NOT IN THE QUERY STRING. A bearer
credential in a URL lands in access logs, proxy logs and browser history; the
project already scrubs phones out of query strings for exactly that reason
(`core/pii.py`), and putting a fifteen-minute session token there would undo
the point. So the server accepts the socket, requires an auth frame, and closes
if one does not arrive.

THE RECONNECT PATH is the property the whole design exists for, and it is
tested as a sequence rather than as a query: connect, disconnect, a CRITICAL
arrives while nobody is listening, reconnect, and it must be there. Calling
`outstanding_for` directly would prove the query works and say nothing about
whether the socket uses it.
"""

from __future__ import annotations

import pytest

CRITICAL_PHRASE = "mfite ububabare bw'igituza"
ROUTINE_PHRASE = "umutwe urandya cyane"
SOCKET = "/api/v1/alerts/ws"


def _auth(socket, token: str) -> dict:
    """Send the opening auth frame and return the server's reply."""
    socket.send_json({"type": "auth", "token": token})
    return socket.receive_json()


def _token_for(client, user, password: str = "Correct-Horse9-battery") -> str:
    """A live access token for a user, via the normal login path."""
    response = client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
def doctor_user(db, user_factory):
    from app.models.doctor import Doctor
    from app.models.user import UserRole

    record = Doctor(name="Dr Socket", email="dr.socket@kinyamed.rw", is_on_duty=True)
    db.add(record)
    db.commit()
    return user_factory(UserRole.DOCTOR, doctor_id=record.id)


def _triage(client, patient_factory, phrase: str = CRITICAL_PHRASE) -> dict:
    patient = patient_factory()
    response = client.post(
        "/api/v1/triage", json={"patient_id": patient["id"], "symptoms_input": phrase}
    )
    assert response.status_code == 201, response.text
    return response.json()


# ── Authentication ───────────────────────────────────────────────────────


def test_a_doctor_may_open_a_socket(make_client, doctor_user):
    client = make_client()
    token = _token_for(client, doctor_user)
    with client.websocket_connect(SOCKET) as socket:
        assert _auth(socket, token)["type"] == "ready"


def test_a_patient_token_is_refused(make_client, user_factory, db):
    """Patient data is not a patient's to watch in aggregate."""
    from app.models.patient import Patient
    from app.models.user import UserRole
    from starlette.websockets import WebSocketDisconnect

    patient = Patient(name="Sock Patient", phone="+250788129001")
    db.add(patient)
    db.commit()
    user = user_factory(UserRole.PATIENT, patient_id=patient.id)

    client = make_client()
    token = _token_for(client, user)
    with (
        pytest.raises(WebSocketDisconnect) as closed,
        client.websocket_connect(SOCKET) as socket,
    ):
        _auth(socket, token)
    assert closed.value.code == 1008, (
        "a patient token was not refused with a policy close"
    )


def test_a_socket_with_no_auth_frame_is_closed(make_client):
    from starlette.websockets import WebSocketDisconnect

    client = make_client()
    with pytest.raises(WebSocketDisconnect), client.websocket_connect(SOCKET) as socket:
        socket.send_json({"type": "something-else"})
        socket.receive_json()


def test_a_garbage_token_is_refused(make_client):
    from starlette.websockets import WebSocketDisconnect

    client = make_client()
    with (
        pytest.raises(WebSocketDisconnect) as closed,
        client.websocket_connect(SOCKET) as socket,
    ):
        _auth(socket, "not-a-token")
    assert closed.value.code == 1008


def test_a_logged_out_token_is_refused(make_client, doctor_user, monkeypatch):
    """A withdrawn access token must not open a socket either.

    The blocklist closed the fifteen-minute window on HTTP; a socket that
    skipped the check would reopen it, and hold it open for as long as the
    connection lasts.
    """
    from app.core import token_blocklist
    from app.core.config import settings
    from starlette.websockets import WebSocketDisconnect

    monkeypatch.setattr(settings, "BLOCKLIST_ENABLED", True)
    token_blocklist.reset_client()
    if token_blocklist.get_client() is None:
        pytest.skip("Redis is not reachable")

    client = make_client()
    token = _token_for(client, doctor_user)
    client.headers["Authorization"] = f"Bearer {token}"
    assert client.post("/api/v1/auth/logout").status_code == 200

    with (
        pytest.raises(WebSocketDisconnect) as closed,
        client.websocket_connect(SOCKET) as socket,
    ):
        _auth(socket, token)
    assert closed.value.code == 1008
    token_blocklist.reset_client()


def test_a_deactivated_doctor_is_refused(make_client, doctor_user, client, db):
    from starlette.websockets import WebSocketDisconnect

    socket_client = make_client()
    token = _token_for(socket_client, doctor_user)
    assert client.patch(f"/api/v1/users/{doctor_user.id}/deactivate").status_code == 200

    with (
        pytest.raises(WebSocketDisconnect) as closed,
        socket_client.websocket_connect(SOCKET) as socket,
    ):
        _auth(socket, token)
    assert closed.value.code == 1008


# ── The reconnect path, end to end ───────────────────────────────────────


def test_a_critical_arriving_while_disconnected_is_delivered_on_reconnect(
    make_client, client, patient_factory, doctor_user
):
    """The property the whole design exists for.

    Proven as a sequence through a real socket: if the connect handler ever
    stops consulting the backfill, this fails even though the backfill query
    itself still passes its own tests.
    """
    socket_client = make_client()
    token = _token_for(socket_client, doctor_user)

    # 1. Connected, nothing outstanding.
    with socket_client.websocket_connect(SOCKET) as socket:
        ready = _auth(socket, token)
        assert ready["type"] == "ready"
        assert ready["outstanding"] == [], "started with unexpected alerts"

    # 2. Disconnected. A CRITICAL arrives with nobody listening.
    entry = _triage(client, patient_factory, CRITICAL_PHRASE)

    # 3. Reconnected: it must be there.
    with socket_client.websocket_connect(SOCKET) as socket:
        ready = _auth(socket, token)
        delivered = [alert["queue_id"] for alert in ready["outstanding"]]
        assert entry["queue_id"] in delivered, (
            "a CRITICAL that arrived during a disconnection was never delivered"
        )


def test_acknowledging_stops_it_arriving_on_the_next_connect(
    make_client, client, patient_factory, doctor_user, db
):
    socket_client = make_client()
    token = _token_for(socket_client, doctor_user)
    entry = _triage(client, patient_factory, CRITICAL_PHRASE)

    with socket_client.websocket_connect(SOCKET) as socket:
        _auth(socket, token)
        socket.send_json({"type": "ack", "queue_id": entry["queue_id"]})
        assert socket.receive_json()["type"] == "acked"

    with socket_client.websocket_connect(SOCKET) as socket:
        ready = _auth(socket, token)
        assert entry["queue_id"] not in [a["queue_id"] for a in ready["outstanding"]]


def test_a_routine_arrival_is_not_delivered(
    make_client, client, patient_factory, doctor_user
):
    socket_client = make_client()
    token = _token_for(socket_client, doctor_user)
    entry = _triage(client, patient_factory, ROUTINE_PHRASE)

    with socket_client.websocket_connect(SOCKET) as socket:
        ready = _auth(socket, token)
        assert entry["queue_id"] not in [a["queue_id"] for a in ready["outstanding"]]


def test_the_backfill_carries_no_symptom_text(
    make_client, client, patient_factory, doctor_user
):
    """An alert says who and how urgent, never what they wrote.

    The queue board shows a preview; this frame is a notification and does not
    need one, and a socket payload is one more place for a patient's own words
    about their body to end up (L11).
    """
    socket_client = make_client()
    token = _token_for(socket_client, doctor_user)
    _triage(client, patient_factory, CRITICAL_PHRASE)

    with socket_client.websocket_connect(SOCKET) as socket:
        ready = _auth(socket, token)
    assert CRITICAL_PHRASE not in str(ready)


def test_the_backfill_masks_the_patient_phone(
    make_client, client, patient_factory, doctor_user
):
    socket_client = make_client()
    token = _token_for(socket_client, doctor_user)
    _triage(client, patient_factory, CRITICAL_PHRASE)

    with socket_client.websocket_connect(SOCKET) as socket:
        ready = _auth(socket, token)
    import re

    assert not re.search(r"(?<![\w*+])\+?\d(?:[ \-]?\d){8,14}(?!\w)", str(ready)), (
        "an unmasked phone-shaped number reached the socket payload"
    )
