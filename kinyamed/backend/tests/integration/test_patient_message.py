"""The patient is never told, by this system, that their condition can wait.

The model (accuracy 0.7065, ECE 0.18, evaluated on nine sentences) may order a
queue a clinician reviews. It is not fit to advise a patient. So the message a
patient receives is the same receipt for every urgency class: their report was
received, their place in the queue, and a generic escalation line.

These tests hold that at the API boundary, for every urgency the model can emit.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

import pytest

# One scripted phrase per urgency class (see ScriptedClassifier in conftest).
BY_URGENCY = {
    "CRITICAL": "mfite ububabare bw'igituza",
    "URGENT": "mfite umuriro mwinshi",
    "ROUTINE": "ndumva nkeneye kubonana na muganga",
}

ESCALATION = (
    "If you feel worse or this is an emergency, go to the health centre immediately."
)

# Words that tell a patient they may wait, are fine, or should book later. The
# receipt must contain none of them, in any urgency class.
#
# THIS LIST IS ENGLISH AND IS NOT SUFFICIENT ON ITS OWN. Before this change it
# passed against the Kinyarwanda "make an appointment" template, because that
# sentence contains no English word. No Kinyarwanda word list is added here:
# choosing which Kinyarwanda words reassure is a speaker's judgement (L16). The
# two structural tests below carry the weight in every language: the message is
# identical for every urgency, and no authored urgency template reaches it.
REASSURING = (
    "safe",
    "wait",
    "appointment",
    "not urgent",
    "routine",
    "no need",
    "nothing to worry",
    "don't worry",
    "later",
    "when convenient",
    "can be handled",
    "soon",
    "fine",
)

REVIEW_DIR = Path(__file__).resolve().parents[3] / "ml_model" / "review"


def _authored_response_templates() -> list[str]:
    """Every urgency-specific response a speaker authored, app and SMS channels."""
    texts: list[str] = []
    for path in sorted(REVIEW_DIR.glob("speaker_brief_*_responses.csv")):
        with path.open(encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                phrasing = (row.get("your_phrasing") or "").strip()
                if phrasing:
                    texts.append(phrasing)
    return texts


def _triage(client, patient_factory, text: str) -> dict:
    patient = patient_factory()
    response = client.post(
        "/api/v1/triage", json={"patient_id": patient["id"], "symptoms_input": text}
    )
    assert response.status_code == 201, response.text
    return response.json()


def _without_numbers(message: str) -> str:
    return re.sub(r"\d+", "#", message)


@pytest.mark.parametrize("urgency", sorted(BY_URGENCY))
def test_no_patient_message_reassures_or_advises_waiting(
    client, patient_factory, urgency: str
):
    body = _triage(client, patient_factory, BY_URGENCY[urgency])
    assert body["urgency_level"] == urgency, "the fixture did not produce this class"

    message = body["patient_response"].lower()
    for phrase in REASSURING:
        assert phrase not in message, f"{phrase!r} reached a {urgency} patient"


@pytest.mark.parametrize("urgency", sorted(BY_URGENCY))
def test_the_patient_message_never_names_an_urgency(
    client, patient_factory, urgency: str
):
    message = _triage(client, patient_factory, BY_URGENCY[urgency])["patient_response"]
    for level in ("CRITICAL", "URGENT", "ROUTINE"):
        assert level.lower() not in message.lower()


def test_the_patient_message_is_identical_for_every_urgency(client, patient_factory):
    """Structural: a message that does not vary cannot carry the model's advice."""
    messages = {
        urgency: _without_numbers(
            _triage(client, patient_factory, text)["patient_response"]
        )
        for urgency, text in BY_URGENCY.items()
    }
    assert len(set(messages.values())) == 1, messages


@pytest.mark.parametrize("urgency", sorted(BY_URGENCY))
def test_the_patient_message_is_a_receipt_with_the_escalation_line(
    client, patient_factory, urgency: str
):
    body = _triage(client, patient_factory, BY_URGENCY[urgency])
    message = body["patient_response"]
    assert message.startswith("Your report has been received.")
    assert str(body["queue_number"]) in message
    assert str(body["queue_position"]) in message
    assert message.endswith(ESCALATION)


def test_no_authored_urgency_template_reaches_the_patient(client, patient_factory):
    templates = _authored_response_templates()
    assert templates, "expected the speaker briefs to hold authored templates"
    for text in BY_URGENCY.values():
        message = _triage(client, patient_factory, text)["patient_response"]
        for template in templates:
            stem = template.split("{")[0].strip()
            assert stem not in message, f"authored template reached a patient: {stem!r}"


def test_machine_drafted_advice_is_neither_returned_nor_stored(
    client, patient_factory, db
):
    from app.models.triage_result import TriageResult

    body = _triage(client, patient_factory, BY_URGENCY["ROUTINE"])
    for retired in (
        "ai_response_rw",
        "possible_conditions",
        "response_pending",
        "response_pending_reason",
    ):
        assert retired not in body, f"{retired} is still in the response"

    row = db.get(TriageResult, body["triage_id"])
    assert row.ai_response_rw is None
    assert row.possible_conditions is None


def test_the_read_path_returns_the_same_receipt(client, patient_factory):
    created = _triage(client, patient_factory, BY_URGENCY["CRITICAL"])
    fetched = client.get(f"/api/v1/triage/{created['triage_id']}").json()
    assert _without_numbers(fetched["patient_response"]) == _without_numbers(
        created["patient_response"]
    )
    assert fetched["patient_response"].endswith(ESCALATION)


def test_the_sms_carries_the_same_receipt(client, patient_factory, monkeypatch):
    """The SMS is a patient-facing path too, and must say exactly what the app says."""
    from app.routes.v1 import triage as triage_route

    sent: list[str] = []
    monkeypatch.setattr(
        triage_route,
        "send_sms_in_background",
        lambda patient_id, phone, message: sent.append(message),
    )
    body = _triage(client, patient_factory, BY_URGENCY["ROUTINE"])
    assert sent == [body["patient_response"]]


def test_the_urgency_is_labelled_a_clinician_hint(client, patient_factory):
    body = _triage(client, patient_factory, BY_URGENCY["CRITICAL"])
    assert body["urgency_level"] == "CRITICAL"
    assert body["confidence_score"] is not None
    notice = body["clinician_hint_notice"].lower()
    assert "clinician" in notice
    assert "not advice for the patient" in notice


def test_the_receipt_cannot_depend_on_urgency():
    """Structural: the function that writes the patient message is not given the urgency."""
    import inspect

    from app.services.patient_message import patient_receipt

    assert set(inspect.signature(patient_receipt).parameters) == {
        "queue_number",
        "queue_position",
    }
