"""training/calibration.py: temperature scaling on the calibration split (docs/ENGINEERING_SPEC.md FR-04-12).

Synthetic data with a KNOWN miscalibration: labels are drawn from softmax(z), and the
"model" reports T_true * z. The fitted temperature must recover T_true. Nothing here
says anything about a real model.
"""

from __future__ import annotations

import pytest

# CI's dependency-free job collects every test file with only pytest installed.
np = pytest.importorskip("numpy", reason="calibration is numpy code")

from training import calibration as cal  # noqa: E402
from training import eval_spec as spec  # noqa: E402


def _synthetic(n: int, t_true: float, seed: int = 3):
    rng = np.random.default_rng(seed)
    z = rng.normal(0.0, 1.5, size=(n, 3))
    p = np.exp(z) / np.exp(z).sum(axis=1, keepdims=True)
    labels = np.array([rng.choice(3, p=row) for row in p])
    return z * t_true, labels


@pytest.mark.parametrize("t_true", [3.0, 0.5])
def test_the_fitted_temperature_recovers_a_known_miscalibration(t_true):
    logits, labels = _synthetic(6000, t_true)
    assert cal.fit_temperature(logits, labels) == pytest.approx(t_true, rel=0.08)


def test_calibration_lowers_ece_and_never_changes_the_predicted_class():
    logits, labels = _synthetic(6000, 3.0)
    t = cal.fit_temperature(logits, labels)
    before, after = cal.softmax(logits), cal.softmax(logits / t)
    assert cal.ece(after, labels) < cal.ece(before, labels) / 2
    assert (before.argmax(axis=1) == after.argmax(axis=1)).all()


def test_the_fit_is_the_minimum_of_the_negative_log_likelihood():
    logits, labels = _synthetic(3000, 2.0)
    t = cal.fit_temperature(logits, labels)
    grid = np.exp(np.linspace(np.log(0.05), np.log(20.0), 4001))
    best = grid[np.argmin([cal.nll(logits / g, labels) for g in grid])]
    assert cal.nll(logits / t, labels) <= cal.nll(logits / best, labels) + 1e-6


def test_ece_matches_the_deployment_gate_exactly():
    """One definition of ECE: the pipeline and the gate must never disagree."""
    from training import evaluate as gate

    logits, labels = _synthetic(2000, 2.0)
    probs = cal.softmax(logits)
    items = [
        gate.Item(
            f"i{k}",
            "kinyarwanda",
            int(labels[k]),
            f"s{k}",
            tuple(map(float, probs[k])),
            None,
        )
        for k in range(len(labels))
    ]
    _, bins, _ = gate._cluster_arrays(items)
    assert cal.ece(probs, labels) == pytest.approx(gate._ece(bins.sum(axis=0)))


def test_the_ece_interval_resamples_scenarios_not_rows():
    """40 source scenarios, each repeated as 50 near-identical rows (the n=9 gold set's
    shape). Treating the 2,000 rows as independent must give a narrower interval than
    resampling the 40 scenarios. Clustering independent rows would prove nothing."""
    logits, labels = _synthetic(40, 2.0)
    probs = np.repeat(cal.softmax(logits), 50, axis=0)
    labels = np.repeat(labels, 50)
    clustered = cal.ece_with_interval(
        probs, labels, [f"s{k // 50}" for k in range(2000)]
    )
    as_rows = cal.ece_with_interval(probs, labels, [f"r{k}" for k in range(2000)])
    assert clustered.low <= clustered.point <= clustered.high
    assert clustered.point == pytest.approx(as_rows.point)
    assert (clustered.high - clustered.low) > 3 * (as_rows.high - as_rows.low)


def test_the_reliability_diagram_accounts_for_every_item():
    import xml.etree.ElementTree as ET

    logits, labels = _synthetic(1500, 2.0)
    svg = ET.fromstring(cal.reliability_svg(cal.softmax(logits), labels))
    bars = [el for el in svg.iter() if el.get("class") == "bin"]
    assert sum(int(b.get("data-count")) for b in bars) == 1500


# ── The calibration split must meet its allocation ────────────────────────────
def _split(allocation):
    labels, languages, scenarios = [], [], []
    k = 0
    for a in allocation:
        for cls, count in ((0, a.critical), (1, a.urgent), (2, a.routine)):
            for _ in range(count):
                labels.append(cls)
                languages.append(a.language)
                scenarios.append(f"cal-{k}")
                k += 1
    return labels, languages, scenarios


def test_a_calibration_split_built_to_the_allocation_passes():
    assert cal.calibration_split_shortfalls(*_split(spec.CALIBRATION_ALLOCATION)) == []


def test_a_short_calibration_split_is_refused_with_every_shortfall_named():
    labels, languages, scenarios = _split(spec.CALIBRATION_ALLOCATION)
    keep = [k for k, lang in enumerate(languages) if lang != "swahili"]
    shortfalls = cal.calibration_split_shortfalls(
        [labels[k] for k in keep],
        [languages[k] for k in keep],
        [scenarios[k] for k in keep],
    )
    assert "swahili CRITICAL: 0 distinct scenarios, need 100" in shortfalls
    assert len(shortfalls) == 3


def test_repeated_rows_from_one_scenario_do_not_fill_the_allocation():
    labels, languages, scenarios = _split(spec.CALIBRATION_ALLOCATION)
    collapsed = [
        "one" if lang == "english" else s
        for lang, s in zip(languages, scenarios, strict=True)
    ]
    shortfalls = cal.calibration_split_shortfalls(labels, languages, collapsed)
    assert any(s.startswith("english CRITICAL: 1 distinct") for s in shortfalls)


def test_fitting_refuses_empty_or_misshaped_input():
    with pytest.raises(ValueError):
        cal.fit_temperature(np.zeros((0, 3)), np.zeros(0, dtype=int))
    with pytest.raises(ValueError):
        cal.fit_temperature(np.zeros((5, 2)), np.zeros(5, dtype=int))
