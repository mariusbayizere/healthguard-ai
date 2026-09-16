"""training/probe.py: a malfunction probe. NOT A GATE METRIC, anywhere, ever.

Why this is not a gate, and not accuracy:
  * the deployment gate is `training/evaluate.py` on a held-out set that meets
    EVAL_SET_SPEC. No such set exists, so no accuracy number may be produced (L6);
  * the probe answers a narrower question: is the served model grossly malfunctioning?
    Determinism, invariance to formatting, class collapse, label order, probability
    validity, length robustness. None of these needs a clinical judgement.

Any probe item that asserts an urgency is clinical content: it needs a source and a
validator (ENGINEERING_SPEC L5, §10.6). The shipped file is empty, exactly as the
red-flag lexicon is.

Every fixture here is synthetic and non-clinical.
"""

from __future__ import annotations

import pytest

np = pytest.importorskip("numpy", reason="the probe summarises with numpy")

from training import probe  # noqa: E402

TEXTS = [f"placeholder token{k} filler{k}" for k in range(60)]


def _fake(probabilities):
    """A classifier over a lookup: text -> (p_critical, p_urgent, p_routine)."""

    def classify(texts):
        return [probabilities(t) for t in texts]

    return classify


def _spread(text):
    """Keyed on the text's content, not its length: whitespace and case must not matter."""
    k = sum(ord(c) for c in text.strip().lower()) % 3
    base = [0.2, 0.2, 0.2]
    base[k] = 0.6
    return base


# ── The probe never produces a gate number ────────────────────────────────────
def test_every_finding_says_it_is_not_a_gate_metric():
    report = probe.run(_fake(_spread), TEXTS)
    assert probe.NOT_A_GATE in report.banner
    assert all(probe.NOT_A_GATE in line for line in report.render().splitlines()[:1])


def test_the_report_carries_no_accuracy_recall_or_precision():
    import re

    text = probe.run(_fake(_spread), TEXTS).render().lower()
    for word in ("accuracy", "recall", "precision", "f1", "score"):
        assert not re.search(rf"\b{word}\b", text), word


def test_the_gate_does_not_import_the_probe():
    """evaluate.py's gate path must not reach probe code."""
    from pathlib import Path

    gate = Path(probe.__file__).with_name("evaluate.py").read_text()
    assert "probe" not in gate


# ── The malfunction checks ────────────────────────────────────────────────────
def test_a_deterministic_model_passes_every_check():
    report = probe.run(_fake(_spread), TEXTS)
    assert report.failures == []
    assert report.ok


def test_a_model_that_is_not_deterministic_is_caught():
    state = {"n": 0}

    def wobble(text):
        state["n"] += 1
        return [0.5 + 0.001 * state["n"], 0.3, 0.2 - 0.001 * state["n"]]

    report = probe.run(_fake(wobble), TEXTS)
    assert any(f.startswith("determinism") for f in report.failures)


def test_a_model_that_changes_its_answer_on_whitespace_or_case_is_caught():
    def fragile(text):
        return (
            [0.7, 0.2, 0.1]
            if text.startswith(" ") or text[:1].isupper()
            else [0.1, 0.2, 0.7]
        )

    report = probe.run(_fake(fragile), TEXTS)
    assert any(f.startswith("formatting invariance") for f in report.failures)


def test_a_model_that_answers_one_class_for_everything_is_caught():
    report = probe.run(_fake(lambda t: [0.9, 0.05, 0.05]), TEXTS)
    assert any(f.startswith("class collapse") for f in report.failures)


def test_probabilities_that_are_not_a_distribution_are_caught():
    report = probe.run(_fake(lambda t: [0.9, 0.9, 0.9]), TEXTS)
    assert any(f.startswith("probability validity") for f in report.failures)


def test_a_nan_probability_is_caught():
    report = probe.run(_fake(lambda t: [float("nan"), 0.5, 0.5]), TEXTS)
    assert any(f.startswith("probability validity") for f in report.failures)


def test_a_model_whose_label_order_differs_from_the_dataset_is_caught():
    report = probe.run(
        _fake(_spread), TEXTS, id2label={0: "ROUTINE", 1: "URGENT", 2: "CRITICAL"}
    )
    assert any(f.startswith("label order") for f in report.failures)


def test_a_model_that_breaks_on_a_long_input_is_caught():
    def brittle(text):
        return [0.34, 0.33, 0.33] if len(text) < 400 else [float("inf"), 0.0, 0.0]

    report = probe.run(_fake(brittle), TEXTS)
    assert any(
        f.startswith("length robustness") or f.startswith("probability validity")
        for f in report.failures
    )


# ── Clinician-supplied items: empty by default, never a gate ─────────────────
def test_the_shipped_urgency_probe_file_is_empty(tmp_path):
    from pathlib import Path

    shipped = Path(probe.__file__).parents[1] / probe.URGENCY_PROBE_PATH
    rows = probe.load_urgency_probe(shipped)
    assert rows == []


def test_an_urgency_probe_item_without_a_source_and_validator_is_refused(tmp_path):
    path = tmp_path / "probe.csv"
    path.write_text(
        "item_id,text,expected_urgency,source,validated_by\n"
        "p1,placeholder alpha,CRITICAL,,PENDING\n"
    )
    with pytest.raises(probe.ProbeError, match="source"):
        probe.load_urgency_probe(path)


def test_a_validated_urgency_probe_item_is_accepted_but_still_not_a_gate(tmp_path):
    path = tmp_path / "probe.csv"
    path.write_text(
        "item_id,text,expected_urgency,source,validated_by\n"
        "p1,placeholder alpha,CRITICAL,MoH protocol p.4,C-001\n"
    )
    rows = probe.load_urgency_probe(path)
    assert len(rows) == 1
    report = probe.run(_fake(_spread), TEXTS, urgency_items=rows)
    rendered = report.render()
    assert probe.NOT_A_GATE in rendered
    assert "1 of 1" not in rendered  # no score is printed, ever


def test_the_report_states_the_mean_probability_per_class_and_the_highest_critical():
    """A collapse is far easier to read with the probability mass beside it: a model
    answering ROUTINE at p=0.35 is a different fault from one answering at p=0.99."""
    report = probe.run(_fake(lambda t: [0.05, 0.15, 0.80]), TEXTS)
    text = report.render()
    assert "mean probability" in text
    assert "0.05" in text and "0.80" in text
    assert "highest p(CRITICAL)" in text
