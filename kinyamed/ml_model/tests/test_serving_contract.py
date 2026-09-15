"""The decision rule the pipeline tunes is the rule the service serves.

Two committed fixtures are the contract between packages that do not import each
other (as tests/test_label_parity.py is for label order):

  fixtures/decision_rule_cases.json         logits, temperature, thresholds -> the
                                            calibrated probabilities and the decision
  fixtures/pipeline_training_metadata.json  the exact shape of kinyamed_training.json

This side proves the fixtures are what training/calibration.py, training/thresholds.py
and training/pipeline.py produce. backend/tests/unit/test_decision_rule.py proves the
service reproduces the same probabilities and decisions and accepts the metadata.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# CI's dependency-free job collects every test file with only pytest installed.
np = pytest.importorskip("numpy", reason="the decision rule is numpy code")
pytest.importorskip("torch", reason="training.pipeline imports the cost-sensitive loss")

from training import calibration as cal  # noqa: E402
from training import pipeline as pl  # noqa: E402
from training import thresholds as th  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CASES = FIXTURES / "decision_rule_cases.json"
METADATA = FIXTURES / "pipeline_training_metadata.json"
BACKEND = (
    Path(__file__).resolve().parents[2] / "backend/app/services/model_classifier.py"
)


def _decision(probs, thresholds):
    if thresholds is None:
        return int(np.argmax(probs))  # the gate's argmax: ties to the more urgent class
    return int(th.decide(np.array([probs]), *thresholds)[0])


def test_every_golden_case_is_what_the_ml_implementation_computes():
    for case in json.loads(CASES.read_text())["cases"]:
        logits = np.array([case["logits"]], dtype=float)
        probs = cal.softmax(logits / case["temperature"])[0]
        assert probs.tolist() == pytest.approx(case["probabilities"], abs=1e-12), case[
            "name"
        ]
        assert _decision(probs, case["thresholds"]) == case["decision"], case["name"]


def test_the_golden_cases_exercise_every_branch():
    cases = json.loads(CASES.read_text())["cases"]
    decisions = {(c["thresholds"] is None, c["decision"]) for c in cases}
    assert {(False, 0), (False, 1), (False, 2), (True, 0), (True, 2)} <= decisions
    overturned = [
        c
        for c in cases
        if c["thresholds"] is not None
        and c["decision"] != int(np.argmax(c["probabilities"]))
    ]
    assert overturned, "no case where the thresholds change the argmax decision"
    by_temperature = [
        c
        for c in cases
        if c["thresholds"] is not None
        and c["temperature"] != 1.0
        and _decision(cal.softmax(np.array([c["logits"]]))[0], c["thresholds"])
        != c["decision"]
    ]
    assert by_temperature, "no case where the temperature changes the decision"


def test_the_metadata_fixture_is_the_shape_the_pipeline_writes(tmp_path):
    written = pl.training_metadata(
        max_length=96,
        temperature=1.25,
        tuned=th.Thresholds(critical=0.2, urgent=0.55),
        config=pl.DEFAULT_CONFIG,
        seed=42,
    )
    fixture = json.loads(METADATA.read_text())
    assert set(written) == set(fixture)
    assert set(written["thresholds"]) == set(fixture["thresholds"])
    assert written["thresholds"]["rule"] == fixture["thresholds"]["rule"]
    assert written["labels"] == fixture["labels"]


def test_the_backend_names_the_same_rule_text():
    rule = pl.training_metadata(
        max_length=96,
        temperature=1.0,
        tuned=th.Thresholds(critical=0.5, urgent=0.5),
        config=pl.DEFAULT_CONFIG,
        seed=1,
    )["thresholds"]["rule"]
    import ast

    tree = ast.parse(BACKEND.read_text())
    values = [
        node.value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(getattr(t, "id", None) == "THRESHOLD_RULE" for t in node.targets)
        and isinstance(node.value, ast.Constant)
    ]
    assert values == [rule]
