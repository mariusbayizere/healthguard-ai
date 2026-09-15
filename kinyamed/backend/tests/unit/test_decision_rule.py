"""The service serves the decision rule the model was calibrated and gated with, or refuses
to start.

The training pipeline (ml_model/training/pipeline.py) records a temperature and
decision thresholds in `<model dir>/kinyamed_training.json`, beside `max_length`. The
gate scores that thresholded decision. A service that read only `max_length` would
serve the argmax of uncalibrated probabilities: a decision nobody measured. So the
recorded rule is applied exactly, and a record the service cannot apply exactly is a
configuration error that stops start-up, the same contract as `max_length`.

A model that records neither (v2d, whose metadata predates calibration) is served by
argmax, which is also what the gate scores when predictions carry no decision.

No weights are loaded here.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from app.models.triage_result import UrgencyLevel
from app.services import model_classifier as mc

KINYAMED = Path(__file__).resolve().parents[3]
CASES = KINYAMED / "ml_model/tests/fixtures/decision_rule_cases.json"
PIPELINE_METADATA = KINYAMED / "ml_model/tests/fixtures/pipeline_training_metadata.json"

RULE_TEXT = "CRITICAL if p_C >= critical; URGENT if p_C + p_U >= urgent; else ROUTINE"


def _model_dir(tmp_path, metadata: dict) -> Path:
    directory = tmp_path / "model"
    directory.mkdir()
    (directory / mc.TRAINING_METADATA).write_text(json.dumps(metadata))
    return directory


def _calibrated(**overrides) -> dict:
    metadata = {
        "max_length": 96,
        "temperature": 1.7,
        "thresholds": {"rule": RULE_TEXT, "critical": 0.2, "urgent": 0.55},
        "labels": ["CRITICAL", "URGENT", "ROUTINE"],
    }
    metadata.update(overrides)
    return metadata


# ── Reading the recorded rule ─────────────────────────────────────────────────
def test_a_model_recording_no_calibration_is_served_by_argmax(tmp_path):
    directory = _model_dir(
        tmp_path,
        {
            "max_length": 96,
            "source": "run.json",
            "recorded_at": "2026-09-15T12:43:27+00:00",
        },
    )
    rule = mc.read_decision_rule(directory)
    assert rule.temperature == 1.0 and rule.thresholds is None
    assert "argmax" in rule.describe()


def test_a_calibrated_model_records_its_temperature_and_thresholds(tmp_path):
    rule = mc.read_decision_rule(_model_dir(tmp_path, _calibrated()))
    assert rule.temperature == 1.7
    assert rule.thresholds == (0.2, 0.55)
    assert "1.7" in rule.describe() and "0.2" in rule.describe()


def test_the_pipelines_own_metadata_is_accepted(tmp_path):
    """The fixture is the exact shape training/pipeline.py writes (tested on that side)."""
    recorded = json.loads(PIPELINE_METADATA.read_text())
    rule = mc.read_decision_rule(_model_dir(tmp_path, recorded))
    assert rule.temperature == recorded["temperature"]
    assert rule.thresholds == (
        recorded["thresholds"]["critical"],
        recorded["thresholds"]["urgent"],
    )


@pytest.mark.parametrize(
    ("metadata", "named"),
    [
        (_calibrated(thresholds=None) | {"thresholds": None}, "thresholds"),
        ({"max_length": 96, "temperature": 1.3}, "thresholds"),
        (
            {
                "max_length": 96,
                "thresholds": {"rule": RULE_TEXT, "critical": 0.2, "urgent": 0.5},
            },
            "temperature",
        ),
        (_calibrated(temperature=0), "temperature"),
        (_calibrated(temperature=-1.0), "temperature"),
        (_calibrated(temperature="1.7"), "temperature"),
        (_calibrated(temperature=True), "temperature"),
        (_calibrated(temperature=float("inf")), "temperature"),
        (
            _calibrated(thresholds={"rule": RULE_TEXT, "critical": 1.5, "urgent": 0.5}),
            "critical",
        ),
        (
            _calibrated(
                thresholds={"rule": RULE_TEXT, "critical": 0.2, "urgent": -0.1}
            ),
            "urgent",
        ),
        (_calibrated(thresholds={"rule": RULE_TEXT, "urgent": 0.5}), "critical"),
        (
            _calibrated(
                thresholds={
                    "rule": "CRITICAL if p_C > critical",
                    "critical": 0.2,
                    "urgent": 0.5,
                }
            ),
            "rule",
        ),
        (_calibrated(labels=["ROUTINE", "URGENT", "CRITICAL"]), "labels"),
        (_calibrated(decision_margin=0.1), "decision_margin"),
    ],
)
def test_a_rule_the_service_cannot_apply_exactly_is_refused(tmp_path, metadata, named):
    directory = _model_dir(tmp_path, metadata)
    with pytest.raises(mc.ModelConfigurationError, match=named):
        mc.read_decision_rule(directory)


def test_a_non_finite_temperature_written_as_json_nan_is_refused(tmp_path):
    directory = tmp_path / "model"
    directory.mkdir()
    (directory / mc.TRAINING_METADATA).write_text(
        '{"max_length": 96, "temperature": NaN, "thresholds": '
        f'{{"rule": "{RULE_TEXT}", "critical": 0.2, "urgent": 0.5}}}}'
    )
    with pytest.raises(mc.ModelConfigurationError, match="temperature"):
        mc.read_decision_rule(directory)


# ── Applying it ───────────────────────────────────────────────────────────────
def test_the_service_computes_the_same_probabilities_and_decisions_as_the_pipeline():
    """Golden cases computed by training/calibration.py and training/thresholds.py and
    checked against them on the ML side. Both implementations must agree on every one."""
    cases = json.loads(CASES.read_text())["cases"]
    assert len(cases) >= 6
    for case in cases:
        rule = mc.DecisionRule(
            temperature=case["temperature"],
            thresholds=None
            if case["thresholds"] is None
            else tuple(case["thresholds"]),
        )
        probs = mc.calibrated_probabilities([case["logits"]], rule.temperature)[0]
        assert probs == pytest.approx(case["probabilities"], abs=1e-12), case["name"]
        assert rule.decide(probs) == case["decision"], case["name"]


def test_the_cases_include_one_where_the_thresholds_overturn_the_argmax():
    cases = json.loads(CASES.read_text())["cases"]
    assert any(
        c["thresholds"] is not None
        and c["decision"] != max(range(3), key=lambda k: c["probabilities"][k])
        for c in cases
    )


def test_calibrated_probabilities_are_a_distribution_and_stable_for_large_logits():
    (probs,) = mc.calibrated_probabilities([[1000.0, 0.0, -1000.0]], 0.5)
    assert math.isclose(sum(probs), 1.0) and all(0.0 <= p <= 1.0 for p in probs)


class _Engine:
    """Returns fixed probabilities; stands in for BatchedInference."""

    def __init__(self, probs):
        self.probs = probs

    def infer(self, text):
        return self.probs


def test_classify_applies_the_thresholds_not_the_argmax():
    rule = mc.DecisionRule(temperature=1.0, thresholds=(0.2, 0.55))
    classifier = mc.ModelClassifier.with_engine(_Engine([0.25, 0.15, 0.60]), rule=rule)
    result = classifier.classify("x")
    assert result.urgency is UrgencyLevel.CRITICAL


def test_the_confidence_is_the_probability_of_the_class_served():
    """Not the maximum: a CRITICAL served at p=0.25 must look like the low-confidence
    decision it is, so the review threshold still flags it (L4)."""
    rule = mc.DecisionRule(temperature=1.0, thresholds=(0.2, 0.55))
    classifier = mc.ModelClassifier.with_engine(_Engine([0.25, 0.15, 0.60]), rule=rule)
    assert classifier.classify("x").confidence == pytest.approx(0.25)


def test_with_no_recorded_rule_classify_is_still_argmax():
    classifier = mc.ModelClassifier.with_engine(_Engine([0.25, 0.15, 0.60]))
    result = classifier.classify("x")
    assert result.urgency is UrgencyLevel.ROUTINE
    assert result.confidence == pytest.approx(0.60)


def test_the_model_forward_applies_the_recorded_temperature():
    """The served forward pass itself, with a fake tokenizer and model, not a re-implementation."""
    torch = pytest.importorskip("torch")

    class _Output:
        def __init__(self, logits):
            self.logits = logits

    classifier = mc.ModelClassifier.__new__(mc.ModelClassifier)
    classifier._torch = torch
    classifier._max_length = 8
    classifier._rule = mc.DecisionRule(temperature=2.0, thresholds=None)
    classifier._tokenizer = lambda texts, **kwargs: {}
    classifier._model = lambda **kwargs: _Output(torch.tensor([[2.0, 0.0, -2.0]]))
    (probs,) = classifier._forward_batch(["x"])
    assert probs == pytest.approx(
        mc.calibrated_probabilities([[2.0, 0.0, -2.0]], 2.0)[0]
    )
    assert probs != pytest.approx(
        mc.calibrated_probabilities([[2.0, 0.0, -2.0]], 1.0)[0]
    )


# ── Start-up ──────────────────────────────────────────────────────────────────
def test_build_classifier_raises_on_an_unappliable_rule(tmp_path, monkeypatch):
    directory = _model_dir(tmp_path, {"max_length": 96, "temperature": 1.3})
    monkeypatch.setattr(mc.settings, "TRIAGE_MODEL_PATH", str(directory), raising=False)
    monkeypatch.setattr(mc.settings, "MODEL_MAX_LENGTH", None, raising=False)
    with pytest.raises(mc.ModelConfigurationError, match="thresholds"):
        mc.build_classifier()


def test_the_service_refuses_to_start_on_an_unappliable_rule(tmp_path, monkeypatch):
    import main
    from app.services import triage_service
    from fastapi.testclient import TestClient

    directory = _model_dir(tmp_path, _calibrated(temperature=-1.0))
    monkeypatch.setattr(mc.settings, "TRIAGE_MODEL_PATH", str(directory), raising=False)
    monkeypatch.setattr(mc.settings, "MODEL_MAX_LENGTH", None, raising=False)
    triage_service.get_classifier.cache_clear()
    try:
        with pytest.raises(mc.ModelConfigurationError), TestClient(main.app):
            pass
    finally:
        triage_service.get_classifier.cache_clear()
