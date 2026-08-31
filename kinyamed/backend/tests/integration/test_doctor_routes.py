"""Doctor endpoint behaviour."""

from __future__ import annotations


def test_duplicate_email_is_rejected(client, doctor_factory):
    doctor = doctor_factory()
    response = client.post(
        "/api/v1/doctors", json={"name": "Someone Else", "email": doctor["email"]}
    )
    assert response.status_code == 409


def test_email_is_validated_and_normalised(client):
    assert client.post("/api/v1/doctors", json={"name": "Dr X", "email": "not-an-email"}).status_code == 422
    created = client.post("/api/v1/doctors", json={"name": "Dr X", "email": " DR.X@Kinyamed.RW "})
    assert created.status_code == 201
    assert created.json()["email"] == "dr.x@kinyamed.rw"


def test_patch_to_a_taken_email_returns_409(client, doctor_factory):
    first = doctor_factory()
    second = doctor_factory()
    response = client.patch(f"/api/v1/doctors/{second['id']}", json={"email": first["email"]})
    assert response.status_code == 409, "the old code raised an unhandled IntegrityError here"


def test_patch_preserves_omitted_fields(client, doctor_factory):
    doctor = doctor_factory(name="Dr Original", specialty="Paediatrics")
    response = client.patch(f"/api/v1/doctors/{doctor['id']}", json={"is_on_duty": False})
    assert response.json()["specialty"] == "Paediatrics"
    assert response.json()["name"] == "Dr Original"


def test_on_duty_route_is_not_shadowed_by_the_id_route(client, doctor_factory):
    doctor_factory(is_on_duty=True)
    doctor_factory(name="Off Duty", is_on_duty=False)
    body = client.get("/api/v1/doctors/on-duty").json()
    assert len(body) == 1


def test_toggle_duty_returns_the_doctor(client, doctor_factory):
    doctor = doctor_factory(is_on_duty=True)
    response = client.patch(f"/api/v1/doctors/{doctor['id']}/toggle-duty")
    assert response.status_code == 200
    assert response.json()["is_on_duty"] is False


def test_doctor_with_consultations_cannot_be_deleted(client, doctor_factory, patient_factory, db):
    from app.models.consultation import Consultation

    doctor = doctor_factory()
    patient = patient_factory()
    client.post("/api/v1/triage", json={"patient_id": patient["id"], "symptoms_input": "mfite umuriro"})
    entry = client.get("/api/v1/queue").json()["items"][0]
    client.patch(f"/api/v1/queue/{entry['id']}/assign-doctor", json={"doctor_id": doctor["id"]})

    db.add(Consultation(queue_entry_id=entry["id"], doctor_id=doctor["id"], notes="seen"))
    db.commit()

    response = client.delete(f"/api/v1/doctors/{doctor['id']}")
    assert response.status_code == 409


def test_deleting_a_doctor_unassigns_rather_than_removes_waiting_patients(
    client, doctor_factory, patient_factory
):
    doctor = doctor_factory()
    patient = patient_factory()
    client.post("/api/v1/triage", json={"patient_id": patient["id"], "symptoms_input": "mfite umuriro"})
    entry = client.get("/api/v1/queue").json()["items"][0]
    client.patch(f"/api/v1/queue/{entry['id']}/assign-doctor", json={"doctor_id": doctor["id"]})

    assert client.delete(f"/api/v1/doctors/{doctor['id']}").status_code == 204
    assert client.get(f"/api/v1/queue/{entry['id']}").json()["doctor_id"] is None


def test_doctor_list_total_reflects_the_filter(client, doctor_factory):
    """Regression: a filtered count must count rows, not collapse to 1."""
    doctor_factory(name="On A", is_on_duty=True)
    doctor_factory(name="On B", is_on_duty=True)
    doctor_factory(name="Off C", is_on_duty=False)

    assert client.get("/api/v1/doctors").json()["total"] == 3
    assert client.get("/api/v1/doctors", params={"on_duty": True}).json()["total"] == 2
    assert client.get("/api/v1/doctors", params={"on_duty": False}).json()["total"] == 1
