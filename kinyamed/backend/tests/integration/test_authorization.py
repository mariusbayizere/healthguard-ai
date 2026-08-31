"""Role-based access control.

The queue, patient list and analytics all expose other people's names, phone
numbers and symptoms. These tests are the guarantee that a patient account
cannot reach them.
"""

from __future__ import annotations

import pytest

PUBLIC_PATHS = [
    ("GET", "/health"),
    ("GET", "/ready"),
    ("GET", "/"),
]

PROTECTED_PATHS = [
    ("GET", "/api/v1/patients"),
    ("POST", "/api/v1/patients"),
    ("GET", "/api/v1/queue"),
    ("POST", "/api/v1/triage"),
    ("GET", "/api/v1/doctors"),
    ("POST", "/api/v1/doctors"),
    ("GET", "/api/v1/analytics/summary"),
    ("GET", "/api/v1/analytics/daily"),
    ("GET", "/api/v1/users"),
    ("POST", "/api/v1/users"),
]


@pytest.mark.parametrize(("method", "path"), PUBLIC_PATHS)
def test_probes_stay_public(anon_client, method: str, path: str):
    assert anon_client.request(method, path).status_code == 200


@pytest.mark.parametrize(("method", "path"), PROTECTED_PATHS)
def test_every_data_endpoint_requires_authentication(anon_client, method: str, path: str):
    response = anon_client.request(method, path, json={})
    assert response.status_code == 401, f"{method} {path} is reachable without a token"
    assert response.json()["error"]["code"] == "INVALID_TOKEN"


# ── Patient scope ────────────────────────────────────────────────────────
def test_patient_cannot_read_the_queue(patient_client_factory):
    client, _ = patient_client_factory()
    response = client.get("/api/v1/queue")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INSUFFICIENT_ROLE"


def test_patient_cannot_list_patients(patient_client_factory):
    client, _ = patient_client_factory()
    assert client.get("/api/v1/patients").status_code == 403


def test_patient_cannot_read_analytics(patient_client_factory):
    client, _ = patient_client_factory()
    assert client.get("/api/v1/analytics/summary").status_code == 403


def test_patient_cannot_manage_doctors(patient_client_factory):
    client, _ = patient_client_factory()
    assert client.post(
        "/api/v1/doctors", json={"name": "Fake", "email": "fake@kinyamed.rw"}
    ).status_code == 403


def test_patient_can_read_their_own_record(patient_client_factory):
    client, patient_id = patient_client_factory()
    assert client.get(f"/api/v1/patients/{patient_id}").status_code == 200


def test_patient_cannot_read_another_patients_record(patient_client_factory, client):
    other = client.post(
        "/api/v1/patients", json={"name": "Someone Else", "phone": "0788900001"}
    ).json()
    patient, _ = patient_client_factory()

    response = patient.get(f"/api/v1/patients/{other['id']}")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "PATIENT_SCOPE_VIOLATION"


def test_patient_cannot_triage_as_someone_else(patient_client_factory, client):
    other = client.post(
        "/api/v1/patients", json={"name": "Someone Else", "phone": "0788900002"}
    ).json()
    patient, _ = patient_client_factory()

    response = patient.post(
        "/api/v1/triage",
        json={"patient_id": other["id"], "symptoms_input": "mfite umuriro"},
    )
    assert response.status_code == 403


def test_patient_can_triage_themselves_and_see_only_their_own_place(
    patient_client_factory, client
):
    other = client.post(
        "/api/v1/patients", json={"name": "Other Patient", "phone": "0788900003"}
    ).json()
    client.post(
        "/api/v1/triage",
        json={"patient_id": other["id"], "symptoms_input": "mfite ububabare bw'igituza"},
    )

    patient, patient_id = patient_client_factory()
    submitted = patient.post(
        "/api/v1/triage", json={"patient_id": patient_id, "symptoms_input": "mfite umuriro"}
    )
    assert submitted.status_code == 201

    mine = patient.get("/api/v1/queue/me")
    assert mine.status_code == 200
    assert len(mine.json()) == 1
    assert mine.json()[0]["patient_id"] == patient_id


def test_patient_cannot_read_another_patients_triage(patient_client_factory, client):
    other = client.post(
        "/api/v1/patients", json={"name": "Other Patient", "phone": "0788900004"}
    ).json()
    triage = client.post(
        "/api/v1/triage", json={"patient_id": other["id"], "symptoms_input": "mfite umuriro"}
    ).json()

    patient, _ = patient_client_factory()
    assert patient.get(f"/api/v1/triage/{triage['triage_id']}").status_code == 403


def test_patient_cannot_read_another_patients_queue_entry(patient_client_factory, client):
    other = client.post(
        "/api/v1/patients", json={"name": "Other Patient", "phone": "0788900005"}
    ).json()
    client.post(
        "/api/v1/triage", json={"patient_id": other["id"], "symptoms_input": "mfite umuriro"}
    )
    entry = client.get("/api/v1/queue").json()["items"][0]

    patient, _ = patient_client_factory()
    assert patient.get(f"/api/v1/queue/{entry['id']}").status_code == 403


# ── Doctor scope ─────────────────────────────────────────────────────────
def test_doctor_can_work_the_queue(doctor_client, client):
    patient = client.post(
        "/api/v1/patients", json={"name": "Queue Patient", "phone": "0788900010"}
    ).json()
    client.post(
        "/api/v1/triage", json={"patient_id": patient["id"], "symptoms_input": "mfite umuriro"}
    )

    queue = doctor_client.get("/api/v1/queue")
    assert queue.status_code == 200
    entry = queue.json()["items"][0]
    assert doctor_client.patch(
        f"/api/v1/queue/{entry['id']}/status", json={"status": "IN_PROGRESS"}
    ).status_code == 200


def test_doctor_cannot_create_doctors_or_read_analytics(doctor_client):
    assert doctor_client.post(
        "/api/v1/doctors", json={"name": "New Dr", "email": "new@kinyamed.rw"}
    ).status_code == 403
    assert doctor_client.get("/api/v1/analytics/summary").status_code == 403
    assert doctor_client.get("/api/v1/users").status_code == 403


def test_doctor_cannot_delete_patients(doctor_client, client):
    patient = client.post(
        "/api/v1/patients", json={"name": "Delete Me", "phone": "0788900011"}
    ).json()
    assert doctor_client.delete(f"/api/v1/patients/{patient['id']}").status_code == 403


# ── Admin scope ──────────────────────────────────────────────────────────
def test_admin_can_create_a_clinician_account(client, db):
    doctor = client.post(
        "/api/v1/doctors", json={"name": "Dr Mukamana", "email": "mukamana@kinyamed.rw"}
    ).json()
    response = client.post(
        "/api/v1/users",
        json={
            "email": "mukamana.login@kinyamed.rw",
            "password": "clinician-passphrase",
            "full_name": "Dr Mukamana",
            "role": "DOCTOR",
            "doctor_id": doctor["id"],
        },
    )
    assert response.status_code == 201
    assert response.json()["role"] == "DOCTOR"
    assert response.json()["doctor_id"] == doctor["id"]


def test_deactivating_an_account_revokes_its_access(anon_client, client):
    created = client.post(
        "/api/v1/users",
        json={
            "email": "temp.staff@kinyamed.rw",
            "password": "temporary-passphrase",
            "full_name": "Temp Staff",
            "role": "DOCTOR",
        },
    ).json()

    login = anon_client.post(
        "/api/v1/auth/login",
        json={"email": "temp.staff@kinyamed.rw", "password": "temporary-passphrase"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert anon_client.get("/api/v1/queue", headers=headers).status_code == 200

    assert client.patch(f"/api/v1/users/{created['id']}/deactivate").status_code == 200

    # The access token is still within its 15-minute window, but the account is
    # checked on every request, so it stops working immediately.
    denied = anon_client.get("/api/v1/queue", headers=headers)
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "ACCOUNT_INACTIVE"


def test_role_link_consistency_is_enforced_by_the_database(db):
    """A doctor account must never point at a patient chart."""
    from sqlalchemy.exc import IntegrityError

    from app.models.patient import Patient
    from app.models.user import User, UserRole

    patient = Patient(name="Chart", phone="+250788900020")
    db.add(patient)
    db.commit()

    db.add(
        User(
            email="wrong.link@kinyamed.rw",
            hashed_password="x",
            full_name="Wrong Link",
            role=UserRole.DOCTOR,
            patient_id=patient.id,
        )
    )
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
