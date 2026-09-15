"""scripts/benchmark_inference.py: the closed-loop runner and its statistics.

A fake classifier stands in for the model, so nothing here loads torch. The
measurements themselves come from running the script on a real checkpoint.
"""

from __future__ import annotations

import threading
import time

import pytest
from scripts import benchmark_inference as bench


class FakeClassifier:
    def __init__(self, cost_s: float = 0.001) -> None:
        self.cost_s = cost_s
        self.active = 0
        self.max_active = 0
        self._lock = threading.Lock()

    def classify(self, text: str) -> object:
        with self._lock:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        time.sleep(self.cost_s)
        with self._lock:
            self.active -= 1
        return text


def test_a_level_returns_one_latency_sample_per_request_at_the_stated_concurrency():
    fake = FakeClassifier(cost_s=0.005)
    samples, wall_s = bench.run_level(
        fake, [f"t{k}" for k in range(7)], concurrency=10, requests=120
    )
    assert len(samples) == 120
    assert all(s >= 5.0 for s in samples), "each sample includes the classify cost"
    assert fake.max_active == 10
    assert wall_s > 0


def test_percentiles_carry_bootstrap_intervals():
    summary = bench.summarise(list(range(1, 1001)))
    for key in ("p50", "p95", "p99"):
        point, low, high = summary[key]
        assert low <= point <= high
    assert summary["p50"][0] == 500
    assert summary["n"] == 1000


def test_too_few_samples_for_a_gate_are_marked_not_hidden():
    summary = bench.summarise([10.0] * 999)
    assert summary["gate_minimum_met"] is False
    assert bench.summarise([10.0] * 1000)["gate_minimum_met"] is True


def test_equivalence_counts_any_urgency_that_batching_changes():
    single = [[0.6, 0.3, 0.1], [0.2, 0.5, 0.3]]
    batched = [[0.6000001, 0.3, 0.0999999], [0.2, 0.3, 0.5]]
    result = bench.equivalence(single, batched)
    assert result["argmax_disagreements"] == 1
    assert result["max_abs_probability_difference"] == pytest.approx(0.2)
