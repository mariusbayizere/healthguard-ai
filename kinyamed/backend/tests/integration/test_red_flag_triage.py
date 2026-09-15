"""The red-flag layer wired into triage (docs/ENGINEERING_SPEC.md L2).

Every term here is FICTIONAL ("zorblax fever", "quenthari"). The shipped lexicon
is empty; these tests prove the mechanism, not any clinical content.
"""

from __future__ import annotations

import csv
import itertools
import random
from pathlib import Path

import pytest
from sqlalchemy import text

FICTIONAL = "zorblax fever"
URGENCIES = ("CRITICAL", "URGENT", "ROUTINE")
PRIORITY = {"CRITICAL": 1, "URGENT": 2, "ROUTINE": 3}


def _lexicon_file(tmp_path: Path, rows: list[dict[str, str]]) -> Path:
    from app.services import red_flags as rf

    path = tmp_path / "red_flags.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, rf.COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    **dict.fromkeys(rf.COLUMNS, ""),
                    "red_flag": "true",
                    "source": "fixture: fictional, not clinical",
                    "validated_by": "FIXTURE",
                    "date": "2026-09-15",
                    **row,
                }
            )
    return path


@pytest.fixture
def triage(client, patient_factory):
    """Submit text with a scripted model answer and an optional fixture lexicon."""
    import main
    from app.models.triage_result import UrgencyLevel
    from app.routes.v1.triage import get_red_flag_lexicon, get_triage_classifier
    from app.services.triage_service import Classification

    script: dict[str, tuple[str, float]] = {}
    calls: list[str] = []

    class _Scripted:
        def classify(self, text: str) -> Classification:
            calls.append("model")
            urgency, confidence = script[text]
            return Classification(urgency=UrgencyLevel(urgency), confidence=confidence)

    main.app.dependency_overrides[get_triage_classifier] = lambda: _Scripted()
    counter = itertools.count()

    def _triage(text_: str, model: str, confidence: float = 0.9, lexicon=None):
        if lexicon is not None:

            class _Spy:
                is_empty = lexicon.is_empty

                def match(self, t: str):
                    calls.append("rules")
                    return lexicon.match(t)

            main.app.dependency_overrides[get_red_flag_lexicon] = lambda: _Spy()
        script[text_] = (model, confidence)
        patient = patient_factory(name=f"Patient {next(counter)}")
        response = client.post(
            "/api/v1/triage",
            json={"patient_id": patient["id"], "symptoms_input": text_},
        )
        return response

    _triage.calls = calls
    return _triage


def _stored(db, triage_id: int):
    return db.execute(
        text(
            "SELECT urgency_level::text, model_urgency_raw::text, rules_layer_triggered, "
            "rules_layer_reason FROM triage_results WHERE id = :id"
        ),
        {"id": triage_id},
    ).one()


# ── Empty lexicon: exactly today's behaviour ──────────────────────────────────
@pytest.mark.parametrize("model", URGENCIES)
@pytest.mark.parametrize("confidence", [0.95, 0.598])
def test_with_the_shipped_empty_lexicon_triage_is_unchanged(
    db, triage, model, confidence
):
    response = triage(
        f"{FICTIONAL} and more, case {model} {confidence}", model, confidence
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["urgency_level"] == model
    assert _stored(db, body["triage_id"]) == (model, model, False, None)


# ── A match escalates, and only escalates ─────────────────────────────────────
@pytest.mark.parametrize("model", URGENCIES)
def test_a_fictional_red_flag_forces_critical_and_is_recorded(
    db, triage, tmp_path, model
):
    from app.services import red_flags as rf

    lexicon = rf.load_lexicon(
        _lexicon_file(tmp_path, [{"concept_id": "FAKE01", "en": FICTIONAL}])
    )
    response = triage(
        f"I have {FICTIONAL} since morning ({model})", model, lexicon=lexicon
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["urgency_level"] == "CRITICAL"
    # Recorded as triggered even when the model already said CRITICAL: the layer
    # matched, and the audit trail says so.
    assert _stored(db, body["triage_id"]) == (
        "CRITICAL",
        model,
        True,
        "red_flag:FAKE01",
    )


def test_the_rules_layer_runs_before_the_model(triage, tmp_path):
    from app.services import red_flags as rf

    lexicon = rf.load_lexicon(
        _lexicon_file(tmp_path, [{"concept_id": "FAKE01", "en": FICTIONAL}])
    )
    triage.calls.clear()
    assert (
        triage(f"{FICTIONAL} order check", "ROUTINE", lexicon=lexicon).status_code
        == 201
    )
    assert triage.calls == ["rules", "model"]


def test_a_red_flag_does_not_bypass_fail_closed(db, client, patient_factory, tmp_path):
    """With no model the request is still a 503 and nothing is written: enqueueing a
    CRITICAL from rules alone, without the model, is a clinical decision (H6)."""
    import main
    from app.routes.v1.triage import get_red_flag_lexicon, get_triage_classifier
    from app.services import red_flags as rf

    lexicon = rf.load_lexicon(
        _lexicon_file(tmp_path, [{"concept_id": "FAKE01", "en": FICTIONAL}])
    )
    main.app.dependency_overrides[get_triage_classifier] = lambda: None
    main.app.dependency_overrides[get_red_flag_lexicon] = lambda: lexicon
    patient = patient_factory(name="No Model")
    response = client.post(
        "/api/v1/triage",
        json={"patient_id": patient["id"], "symptoms_input": FICTIONAL},
    )
    assert response.status_code == 503
    assert db.execute(text("SELECT count(*) FROM triage_results")).scalar_one() == 0


def test_the_escalated_case_sorts_in_the_critical_band(client, triage, tmp_path):
    from app.services import red_flags as rf

    lexicon = rf.load_lexicon(
        _lexicon_file(tmp_path, [{"concept_id": "FAKE01", "en": FICTIONAL}])
    )
    triage("plain urgent case", "URGENT", lexicon=lexicon)
    escalated = triage(f"{FICTIONAL} late arrival", "ROUTINE", lexicon=lexicon).json()
    rows = client.get("/api/v1/queue", params={"page_size": 50}).json()["items"]
    assert rows[0]["queue_number"] == escalated["queue_number"]
    assert rows[0]["band"] == "CRITICAL"


# ── Property: adding terms can only raise urgency ─────────────────────────────
def test_property_adding_any_term_never_lowers_urgency():
    """Seeded random lexicons of fictional pseudo-words, random texts and random
    model answers. For every case: the final urgency is at least as urgent as the
    model's, and a lexicon that is a superset of another never yields a lower one."""
    from app.models.triage_result import UrgencyLevel
    from app.services import red_flags as rf

    rng = random.Random(20260915)
    syllables = ["zor", "blax", "quen", "tha", "ri", "vel", "li", "mor", "ka", "dun"]

    def word() -> str:
        return "".join(rng.choice(syllables) for _ in range(rng.randint(2, 3)))

    def lexicon_of(terms: list[tuple[str, str]]) -> rf.RedFlagLexicon:
        return rf.RedFlagLexicon(
            tuple((concept, rf._pattern([term])) for concept, term in terms)
        )

    for case in range(3000):
        vocabulary = [word() for _ in range(12)]
        base = [(f"C{k}", rng.choice(vocabulary)) for k in range(rng.randint(0, 3))]
        extra = [(f"X{k}", rng.choice(vocabulary)) for k in range(rng.randint(1, 3))]
        text_ = " ".join(rng.choice(vocabulary) for _ in range(rng.randint(1, 10)))
        model = rng.choice(list(UrgencyLevel))

        small = rf.apply(model, lexicon_of(base).match(text_))
        large = rf.apply(model, lexicon_of(base + extra).match(text_))
        assert small.urgency.priority <= model.priority, case
        assert large.urgency.priority <= small.urgency.priority, case
        assert small.model_urgency is model and large.model_urgency is model
        assert large.triggered or not small.triggered, case


# ── Start-up refuses an invalid lexicon ───────────────────────────────────────
def test_the_service_refuses_to_start_with_an_invalid_lexicon(tmp_path, monkeypatch):
    import main
    from app.core.config import settings
    from app.services import red_flags as rf
    from fastapi.testclient import TestClient

    bad = _lexicon_file(
        tmp_path, [{"concept_id": "FAKE01", "en": FICTIONAL, "validated_by": ""}]
    )
    monkeypatch.setattr(settings, "RED_FLAG_LEXICON_PATH", str(bad))
    rf.get_lexicon.cache_clear()
    try:
        with (
            pytest.raises(rf.RedFlagLexiconError, match="validated_by"),
            TestClient(main.app),
        ):
            pass
    finally:
        rf.get_lexicon.cache_clear()
