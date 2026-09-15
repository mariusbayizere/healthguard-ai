"""training/thresholds.py: decision thresholds tuned to CRITICAL safety, not accuracy
(CLAUDE.md FR-04-13).

The two hard constraints are the safety gates, read from eval_spec (5: CRITICAL recall
in each pure language; 7: CRITICAL -> ROUTINE rate, pooled). Among thresholds that
meet both, the tuner minimises expected cost. Accuracy is never the objective.
Synthetic probabilities only; nothing here describes a real model.
"""

from __future__ import annotations

import numpy as np
import pytest
from training import eval_spec as spec
from training import thresholds as th

COSTS = ((0.0, 1.0, 10.0), (1.0, 0.0, 1.0), (1.0, 1.0, 0.0))  # cost_loss default
C, U, R = 0, 1, 2


def _synthetic(per_class: int = 300, seed: int = 5):
    """Every pure language; CRITICAL rows often put most mass on URGENT or ROUTINE,
    so argmax misses CRITICAL cases a lower CRITICAL threshold would catch."""
    rng = np.random.default_rng(seed)
    probs, labels, languages = [], [], []
    alphas = {C: (2.2, 1.6, 1.0), U: (0.6, 2.5, 1.2), R: (0.25, 1.0, 3.0)}
    for language in spec.PURE_LANGUAGES:
        for cls in (C, U, R):
            probs.append(rng.dirichlet(alphas[cls], size=per_class))
            labels += [cls] * per_class
            languages += [language] * per_class
    return np.vstack(probs), np.array(labels), languages


def _accuracy(probs, labels, t):
    return float((th.decide(probs, t.critical, t.urgent) == labels).mean())


# ── The decision rule ─────────────────────────────────────────────────────────
def test_the_decision_rule_escalates_in_order():
    probs = np.array(
        [
            [0.30, 0.10, 0.60],  # p_C >= 0.3        -> CRITICAL
            [0.20, 0.50, 0.30],  # p_C + p_U >= 0.6  -> URGENT
            [0.20, 0.30, 0.50],  # neither           -> ROUTINE
            [0.29, 0.31, 0.40],  # p_C + p_U = 0.60 exactly -> URGENT (inclusive)
        ]
    )
    assert th.decide(probs, 0.3, 0.6).tolist() == [C, U, R, U]


def test_lowering_the_critical_threshold_never_lowers_critical_recall():
    probs, labels, _ = _synthetic()
    critical = labels == C
    recalls = [
        float((th.decide(probs[critical], t, 0.5) == C).mean())
        for t in np.linspace(1.0, 0.0, 21)
    ]
    assert recalls == sorted(recalls)


def test_the_targets_are_the_gate_thresholds_not_local_copies():
    assert spec.requirement("5").threshold == th.CRITICAL_RECALL_TARGET
    assert spec.requirement("7").threshold == th.CRITICAL_TO_ROUTINE_TARGET


def test_recall_exactly_at_target_is_safe_but_a_rate_exactly_at_target_is_not():
    """Gate 5 is 'at least'; gate 7 is 'below'."""
    assert th.meets_recall(spec.requirement("5").threshold)
    assert not th.meets_rate(spec.requirement("7").threshold)


# ── Tuning ────────────────────────────────────────────────────────────────────
def test_tuned_thresholds_meet_both_safety_constraints_in_every_pure_language():
    probs, labels, languages = _synthetic()
    tuned = th.tune(probs, labels, languages, COSTS)
    decided = th.decide(probs, tuned.critical, tuned.urgent)
    for language in spec.PURE_LANGUAGES:
        rows = (np.array(languages) == language) & (labels == C)
        assert (decided[rows] == C).mean() >= th.CRITICAL_RECALL_TARGET, language
    assert ((decided == R) & (labels == C)).sum() / (labels == C).sum() < 0.01
    assert tuned.recall_by_language.keys() == set(spec.PURE_LANGUAGES)


def test_the_tuner_does_not_maximise_accuracy():
    probs, labels, languages = _synthetic()
    argmax_recall = float((probs[labels == C].argmax(axis=1) == C).mean())
    assert argmax_recall < th.CRITICAL_RECALL_TARGET, (
        "precondition: argmax must be unsafe on this data or the test shows nothing"
    )
    tuned = th.tune(probs, labels, languages, COSTS)
    most_accurate = max(
        (th.Thresholds.bare(c, u) for c, u in th.grid()),
        key=lambda t: _accuracy(probs, labels, t),
    )
    assert _accuracy(probs, labels, tuned) < _accuracy(probs, labels, most_accurate)


def test_among_safe_thresholds_it_picks_the_lowest_expected_cost():
    probs, labels, languages = _synthetic(per_class=120, seed=9)
    tuned = th.tune(probs, labels, languages, COSTS)
    safe_costs = [
        th.expected_cost(th.decide(probs, c, u), labels, COSTS)
        for c, u in th.grid()
        if th.is_safe(th.decide(probs, c, u), labels, languages)
    ]
    assert tuned.expected_cost == pytest.approx(min(safe_costs))


def test_a_pure_language_without_critical_items_is_refused():
    probs, labels, languages = _synthetic(per_class=50)
    keep = [
        k
        for k in range(len(labels))
        if not (languages[k] == "french" and labels[k] == C)
    ]
    with pytest.raises(th.ThresholdsRefused, match="french"):
        th.tune(probs[keep], labels[keep], [languages[k] for k in keep], COSTS)


def test_the_precision_given_up_for_safety_is_reported_not_hidden():
    """When catching CRITICAL cases costs CRITICAL precision below gate 4, say so:
    the thresholds stay safe, and gate 4 will fail on the test set."""
    probs, labels, languages = _synthetic()
    tuned = th.tune(probs, labels, languages, COSTS)
    assert tuned.critical_precision < spec.requirement("4").threshold
    assert any("gate 4" in w for w in tuned.warnings)


def test_every_result_says_it_is_not_a_gate_measurement():
    probs, labels, languages = _synthetic(per_class=60)
    record = th.tune(probs, labels, languages, COSTS).as_record()
    assert "not a gate result" in record["note"]
    assert {"critical", "urgent", "cost_matrix", "recall_by_language"} <= record.keys()


def test_probabilities_that_are_not_distributions_are_refused():
    probs, labels, languages = _synthetic(per_class=10)
    with pytest.raises(ValueError):
        th.tune(probs * 2, labels, languages, COSTS)


def test_an_unsafe_cost_matrix_is_refused():
    probs, labels, languages = _synthetic(per_class=10)
    with pytest.raises(ValueError):
        th.tune(probs, labels, languages, ((0, 5, 5), (1, 0, 1), (1, 1, 0)))


# ── The gate must score the decision that will serve ──────────────────────────
def test_the_gate_scores_a_thresholded_decision_when_one_is_given(tmp_path):
    from training import evaluate as gate

    gold = tmp_path / "gold.csv"
    gold.write_text("item_id,language,gold_label,scenario_id\na,english,CRITICAL,s1\n")
    predictions = tmp_path / "pred.csv"
    predictions.write_text(
        "item_id,p_critical,p_urgent,p_routine,predicted_label\na,0.3,0.1,0.6,CRITICAL\n"
    )
    items, _ = gate.load_items(gold, gate.load_predictions(predictions))
    assert items[0].pred == C
    assert items[0].argmax == R


def test_without_a_decision_the_gate_still_scores_argmax(tmp_path):
    from training import evaluate as gate

    item = gate.Item("a", "english", C, "s1", (0.3, 0.1, 0.6), None)
    assert item.pred == item.argmax == R


def test_the_gate_refuses_an_unknown_decision_label(tmp_path):
    from training import evaluate as gate

    gold = tmp_path / "gold.csv"
    gold.write_text("item_id,language,gold_label,scenario_id\na,english,CRITICAL,s1\n")
    predictions = tmp_path / "pred.csv"
    predictions.write_text(
        "item_id,p_critical,p_urgent,p_routine,predicted_label\na,0.3,0.1,0.6,SEVERE\n"
    )
    with pytest.raises(gate.InputError, match="SEVERE"):
        gate.load_items(gold, gate.load_predictions(predictions))


def test_ece_is_computed_on_the_argmax_even_under_a_thresholded_decision():
    """Calibration is a property of the probabilities, not of the decision rule."""
    from training import evaluate as gate

    plain = gate.Item("a", "english", R, "s1", (0.3, 0.1, 0.6), None)
    decided = gate.Item("a", "english", R, "s1", (0.3, 0.1, 0.6), None, C)
    _, bins_plain, _ = gate._cluster_arrays([plain])
    _, bins_decided, _ = gate._cluster_arrays([decided])
    assert (bins_plain == bins_decided).all()
