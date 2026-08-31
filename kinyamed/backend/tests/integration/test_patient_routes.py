"""Patient endpoint behaviour."""

from __future__ import annotations

import pytest


def test_create_returns_201_and_normalises_phone(client):
    response = client.post(
        "/api/v1/patients", json={"name": "  Uwimana  ", "phone": "0788 123 456", "gender": "FEMALE"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Uwimana"
    assert body["phone"] == "+250788123456"
    assert body["gender"] == "female"
    assert body["created_at"]


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "A", "phone": "0788123456"},
        {"name": "Uwimana", "phone": "12"},
        {"name": "Uwimana", "phone": "0788123456", "age": 900},
        {"name": "Uwimana", "phone": "0788123456", "age": -1},
        {"name": "   ", "phone": "0788123456"},
    ],
)
def test_invalid_payloads_are_rejected(client, payload):
    assert client.post("/api/v1/patients", json=payload).status_code == 422


def test_list_is_paginated(client, patient_factory):
    for index in range(5):
        patient_factory(name=f"Patient {index}")
    body = client.get("/api/v1/patients", params={"page_size": 2}).json()
    assert body["total"] == 5
    assert len(body["items"]) == 2
    assert body["page_size"] == 2


def test_list_rejects_an_unbounded_page_size(client):
    assert client.get("/api/v1/patients", params={"page_size": 10_000}).status_code == 422


def test_search_matches_name_or_phone(client, patient_factory):
    patient_factory(name="Mukamana", phone="0788999111")
    patient_factory(name="Habimana", phone="0788999222")
    body = client.get("/api/v1/patients", params={"search": "Mukamana"}).json()
    assert body["total"] == 1


def test_patch_updates_only_supplied_fields(client, patient_factory):
    patient = patient_factory(name="Original", age=30)
    response = client.patch(f"/api/v1/patients/{patient['id']}", json={"age": 31})
    assert response.status_code == 200
    assert response.json()["name"] == "Original", "omitted fields must be preserved"
    assert response.json()["age"] == 31


def test_missing_patient_returns_404(client):
    assert client.get("/api/v1/patients/999999").status_code == 404
    assert client.patch("/api/v1/patients/999999", json={"age": 5}).status_code == 404
    assert client.delete("/api/v1/patients/999999").status_code == 404


def test_delete_without_records_succeeds(client, patient_factory):
    patient = patient_factory()
    assert client.delete(f"/api/v1/patients/{patient['id']}").status_code == 204


def test_delete_with_clinical_records_is_refused_then_allowed_with_cascade(
    client, patient_factory
):
    """The old code raised an unhandled IntegrityError here (HTTP 500)."""
    patient = patient_factory()
    client.post(
        "/api/v1/triage", json={"patient_id": patient["id"], "symptoms_input": "mfite umuriro"}
    )

    refused = client.delete(f"/api/v1/patients/{patient['id']}")
    assert refused.status_code == 409
    assert "cascade=true" in refused.json()["error"]["message"]

    forced = client.delete(f"/api/v1/patients/{patient['id']}", params={"cascade": True})
    assert forced.status_code == 204
    assert client.get("/api/v1/queue").json()["total"] == 0, "records must cascade away"
