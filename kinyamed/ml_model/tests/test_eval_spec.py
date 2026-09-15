"""The evaluation-set specification: exact intervals, power, and the allocation."""

from __future__ import annotations

import os

import pytest
from training import eval_spec as spec


@pytest.mark.parametrize(
    ("x", "n", "lower", "upper"),
    [
        # Published Clopper-Pearson 95% intervals.
        (5, 10, 0.1871, 0.8129),
        (0, 10, 0.0, 0.3085),
        (10, 10, 0.6915, 1.0),
        (91, 100, 0.8360, 0.9580),
    ],
)
def test_clopper_pearson_matches_published_values(x, n, lower, upper) -> None:
    lo, hi = spec.clopper_pearson(x, n)
    assert lo == pytest.approx(lower, abs=5e-4)
    assert hi == pytest.approx(upper, abs=5e-4)


def test_zero_events_in_368_bounds_a_rate_below_one_percent() -> None:
    assert spec.clopper_pearson(0, 368)[1] < 0.01
    assert spec.clopper_pearson(0, 367)[1] >= 0.01


def test_an_observed_recall_of_exactly_the_threshold_never_clears_it() -> None:
    for n in (100, 400, 1000, 5000):
        lower, _ = spec.clopper_pearson(round(0.91 * n), n)
        assert lower < 0.91


def test_the_nine_sentence_set_cannot_distinguish_anything() -> None:
    """Four CRITICAL items, all correct, still leave the interval below 0.5."""
    assert spec.clopper_pearson(4, 4)[0] < 0.5


def test_power_rises_with_n_and_with_the_true_value() -> None:
    assert spec.power_at_least(365, 0.95, 0.91) >= 0.80
    assert spec.power_at_least(100, 0.95, 0.91) < 0.80
    assert spec.power_at_least(365, 0.97, 0.91) > spec.power_at_least(365, 0.95, 0.91)


# E8, ruled 2026-09-15: CRITICAL -> ROUTINE is gated per pure language, never
# pooled only, so each pure language needs its own 720 gold CRITICAL items.
def test_each_pure_language_has_at_least_800_critical_items() -> None:
    by_lang = {a.language: a for a in spec.TEST_ALLOCATION}
    for lang in spec.PURE_LANGUAGES:
        assert by_lang[lang].critical >= 800, lang


def test_the_allocation_check_covers_per_language_critical_to_routine(
    monkeypatch,
) -> None:
    """The old 400-per-language allocation passed the pooled check (1,600 >= 720)
    while every per-language gate 7 row was unmeasurable. The check must see that."""
    old = tuple(
        spec.Allocation(a.language, 400, a.urgent, a.routine)
        if a.language in spec.PURE_LANGUAGES
        else a
        for a in spec.TEST_ALLOCATION
    )
    monkeypatch.setattr(spec, "TEST_ALLOCATION", old)
    failures = spec.check_allocation_meets_requirements()
    for lang in spec.PURE_LANGUAGES:
        assert f"{lang} CRITICAL: 400 < 720 (gate 7, per language)" in failures


def test_the_open_per_language_urgent_and_routine_shortfall_is_named() -> None:
    """E8b, not decided: 300 URGENT and 300 ROUTINE per pure language are below the
    570 that per-language URGENT recall and weighted/macro F1 need. The check says
    so rather than passing a set the gate would refuse."""
    failures = set(spec.check_allocation_meets_requirements())
    expected = set()
    for lang in spec.PURE_LANGUAGES:
        expected.add(f"{lang} URGENT: 300 < 570 (gate 8, per language)")
        expected.add(f"{lang} smallest class: 300 < 570 (gates 2 and 3, per language)")
    assert failures == expected


def test_every_gate_metric_of_section_9_2_has_a_requirement() -> None:
    gates = {r.gate for r in spec.REQUIREMENTS}
    assert {str(i) for i in range(1, 16)} <= gates
    assert {"X-ECE", "X-LID-pure", "X-LID-mixed"} <= gates


def test_a_calibrated_model_on_a_small_set_fails_a_0_05_ece_gate_by_chance() -> None:
    """The reason ECE needs 2000 items, pinned."""
    mean_small, _ = spec.expected_ece_of_a_calibrated_model(300, trials=60)
    _, p95_large = spec.expected_ece_of_a_calibrated_model(2000, trials=60)
    assert mean_small > spec.ECE_THRESHOLD
    assert p95_large < spec.ECE_THRESHOLD


@pytest.mark.skipif(
    not os.environ.get("KINYAMED_SLOW"),
    reason="recomputes every minimum (about 3 minutes); set KINYAMED_SLOW=1",
)
def test_stored_minimums_are_the_derived_ones() -> None:
    derived = spec.derive_minimums()
    stored = {r.gate: r.minimum_n for r in spec.REQUIREMENTS if r.gate in derived}
    assert derived == stored
