"""docs/ENGINEERING_SPEC.md §13 PII leak test: logs and API error bodies carry no phone or full name.

Drives the paths that have leaked or could: patient creation, self-registration,
triage (which composes an SMS), the queue, a phone search, validation and
conflict errors, a password reset delivered by SMS, and a database constraint
error whose driver message quotes the row. Everything written to stdout and
stderr is captured and scanned, and so is every error body.

Kafka payloads: covered as of 2026-09-17 by test_alert_publish.py, which asserts
the alert topic carries no symptom text, no phone and no name. CSV exports: this
service still has no export endpoint; when one is added it must join this scan.
"""

from __future__ import annotations

import re

PHONE_LOCAL = "0788555123"
PHONE_E164 = "+250788555123"
NAME = "Mukandayisenga Josiane"
EMAIL = "josiane.mukandayisenga@example.rw"

# In LOGS, any phone-shaped digit run is a failure, not only the fixture's: a
# log must not carry anyone's number. Same shape as the masker (a run of 9-15
# digits not glued to letters), so tokens and UUIDs are not false alarms.
PHONE_SHAPED = re.compile(r"(?<![\w*+])(?<!\d\.)\+?\d(?:[ \-]?\d){8,14}(?!\w)(?!\.\d)")
FIXTURE_PII = ("788555123", "788555124", "0788 555 123", NAME, "Mukandayisenga", EMAIL)


def _scan(text: str) -> list[str]:
    """Fixture PII anywhere, plus any phone-shaped number."""
    return [n for n in FIXTURE_PII if n in text] + PHONE_SHAPED.findall(text)


def _scan_body(text: str) -> list[str]:
    """Error bodies: fixture PII only. Validation messages legitimately cite
    format examples ("e.g. 0788123456"), which are not anyone's number."""
    return [n for n in FIXTURE_PII if n in text]


def test_no_phone_or_name_leaks_into_logs_or_error_bodies(
    make_client, admin_user, patient_factory, capsys
):
    from tests.conftest import _authenticated

    staff = _authenticated(make_client(), admin_user)
    anon = make_client()
    error_bodies: list[str] = []

    # Patient chart created by staff, then triaged (SMS composed with the phone).
    created = staff.post("/api/v1/patients", json={"name": NAME, "phone": PHONE_LOCAL})
    assert created.status_code == 201, created.text
    patient = created.json()
    triaged = staff.post(
        "/api/v1/triage",
        json={"patient_id": patient["id"], "symptoms_input": "mfite umuriro"},
    )
    assert triaged.status_code == 201, triaged.text
    assert staff.get("/api/v1/queue").status_code == 200
    assert (
        staff.get("/api/v1/patients", params={"search": PHONE_LOCAL}).status_code == 200
    )

    # Self-registration, and a password reset delivered to that phone by SMS.
    registered = anon.post(
        "/api/v1/auth/register",
        json={
            "email": EMAIL,
            "password": "A-Long-Enough-Password9",
            "confirm_password": "A-Long-Enough-Password9",
            "first_name": NAME.split()[0],
            "last_name": NAME.split()[1],
            "phone": "0788555124",
        },
    )
    assert registered.status_code == 201, registered.text
    anon.post("/api/v1/auth/password-reset/request", json={"email": EMAIL})

    # Errors that could echo input back: a bad phone, a duplicate email.
    for response in (
        staff.post("/api/v1/patients", json={"name": NAME, "phone": "07885551239999"}),
        anon.post(
            "/api/v1/auth/register",
            json={
                "email": EMAIL,
                "password": "A-Long-Enough-Password9",
                "confirm_password": "A-Long-Enough-Password9",
                "first_name": NAME.split()[0],
                "last_name": NAME.split()[1],
                "phone": PHONE_LOCAL,
            },
        ),
    ):
        assert response.status_code >= 400
        error_bodies.append(response.text)

    captured = capsys.readouterr()
    log_problems = _scan(captured.out + captured.err)
    body_problems = [p for body in error_bodies for p in _scan_body(body)]

    assert log_problems == [], f"PII in logs: {log_problems}"
    assert body_problems == [], f"PII in API error bodies: {body_problems}"
    assert captured.out, "nothing was logged, so this scan proved nothing"


def test_api_responses_mask_phones(client, patient_factory):
    """Masked everywhere except the stored column."""
    patient = patient_factory(name="Uwimana", phone=PHONE_LOCAL)
    assert patient["phone"] == "+**********23"
    client.post(
        "/api/v1/triage",
        json={"patient_id": patient["id"], "symptoms_input": "mfite umuriro"},
    )
    row = client.get("/api/v1/queue").json()["items"][0]
    assert row["patient_phone"] == "+**********23"
    listed = client.get("/api/v1/patients").json()["items"][0]
    assert listed["phone"] == "+**********23"


def test_the_stored_phone_is_still_e164(client, patient_factory, db):
    from app.models.patient import Patient

    patient = patient_factory(name="Uwimana", phone=PHONE_LOCAL)
    assert db.get(Patient, patient["id"]).phone == PHONE_E164


def test_a_database_error_does_not_log_the_offending_row(capsys):
    """IntegrityError messages quote the row; the handler must not log them."""
    from app.core.exceptions import register_exception_handlers
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from sqlalchemy.exc import IntegrityError

    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise IntegrityError(
            "INSERT INTO patients ...",
            {},
            Exception(f"Failing row contains ({NAME}, {PHONE_E164})."),
        )

    response = TestClient(app).get("/boom")
    assert response.status_code == 409
    captured = capsys.readouterr()
    assert _scan(captured.out + captured.err + response.text) == []


def test_a_validation_error_never_echoes_the_submitted_value(anon_client):
    """A 422 must describe the rule, not repeat the input.

    Pydantic carries the offending value in its error objects, and a handler
    that serialises them wholesale turns every rejected registration into a
    disclosure: the phone, the name and the password the caller just typed,
    reflected back in the response body and thence into any log that records
    error bodies. The handler strips it today; this keeps it stripped.
    """
    rejected = anon_client.post(
        "/api/v1/auth/register",
        json={
            "email": "leak@kinyamed.rw",
            "password": "weakpassword",
            "confirm_password": "weakpassword",  # fails composition, triggers a 422
            "first_name": NAME.split()[0],
            "last_name": NAME.split()[1],
            "phone": PHONE_LOCAL,
        },
    )
    assert rejected.status_code == 422, rejected.text

    body = rejected.text
    assert PHONE_LOCAL not in body, "a rejected registration echoed the phone number"
    assert NAME not in body, "a rejected registration echoed the patient's name"
    assert "weakpassword" not in body, "a rejected registration echoed the password"
    assert '"input"' not in body, (
        "the handler is serialising Pydantic's input field; it will leak the "
        "next value somebody submits"
    )
