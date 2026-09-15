"""Temperature scaling on the calibration split, with ECE and a reliability diagram (FR-04-12).

One scalar temperature T divides the logits. It is fitted on the CALIBRATION split
only (EVAL_SET_SPEC §5, decision E4), by minimising negative log-likelihood, and
never touches the test split. Dividing by T never changes the predicted class, so
calibration cannot move an urgency on its own. Thresholds decide that
(training/thresholds.py).

ECE uses the deployment gate's own binning (`training/evaluate.py`), so the
pipeline and the gate can never report different numbers for the same predictions.
The interval resamples scenarios, not rows.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from training import eval_spec as spec

BINS = 15
T_MIN, T_MAX = 0.05, 20.0
CLASS_NAMES = ("CRITICAL", "URGENT", "ROUTINE")


def softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    exp = np.exp(shifted)
    return exp / exp.sum(axis=1, keepdims=True)


def nll(logits: np.ndarray, labels: np.ndarray) -> float:
    shifted = logits - logits.max(axis=1, keepdims=True)
    log_probs = shifted - np.log(np.exp(shifted).sum(axis=1, keepdims=True))
    return float(-log_probs[np.arange(len(labels)), labels].mean())


def fit_temperature(
    logits: np.ndarray, labels: np.ndarray, iterations: int = 200
) -> float:
    """The T in [0.05, 20] minimising NLL of softmax(logits / T), by golden-section on log T."""
    logits = np.asarray(logits, dtype=float)
    labels = np.asarray(labels, dtype=int)
    if (
        logits.ndim != 2
        or logits.shape[1] != 3
        or len(logits) == 0
        or len(labels) != len(logits)
    ):
        raise ValueError("need a non-empty (n, 3) logit array and n labels")
    ratio = (math.sqrt(5) - 1) / 2
    low, high = math.log(T_MIN), math.log(T_MAX)
    a, b = high - ratio * (high - low), low + ratio * (high - low)
    fa, fb = nll(logits / math.exp(a), labels), nll(logits / math.exp(b), labels)
    for _ in range(iterations):
        if fa < fb:
            high, b, fb = b, a, fa
            a = high - ratio * (high - low)
            fa = nll(logits / math.exp(a), labels)
        else:
            low, a, fa = a, b, fb
            b = low + ratio * (high - low)
            fb = nll(logits / math.exp(b), labels)
    return float(math.exp((low + high) / 2))


def _bin_sums(probs: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """Per bin: (count, sum confidence, sum correct), binned exactly as the gate bins."""
    confidence = probs.max(axis=1)
    correct = (probs.argmax(axis=1) == labels).astype(float)
    index = np.clip(np.ceil(confidence * BINS).astype(int) - 1, 0, BINS - 1)
    sums = np.zeros((BINS, 3))
    np.add.at(sums[:, 0], index, 1.0)
    np.add.at(sums[:, 1], index, confidence)
    np.add.at(sums[:, 2], index, correct)
    return sums


def _ece_from_bins(sums: np.ndarray) -> float:
    n = sums[:, 0].sum()
    if n == 0:
        return float("nan")
    filled = sums[:, 0] > 0
    gap = np.abs(sums[filled, 1] / sums[filled, 0] - sums[filled, 2] / sums[filled, 0])
    return float((sums[filled, 0] / n * gap).sum())


def ece(probs: np.ndarray, labels: np.ndarray) -> float:
    return _ece_from_bins(_bin_sums(np.asarray(probs), np.asarray(labels, dtype=int)))


@dataclass(frozen=True)
class Interval:
    point: float
    low: float
    high: float


def ece_with_interval(
    probs: np.ndarray,
    labels: np.ndarray,
    scenarios: Sequence[str],
    *,
    bootstrap: int = 1000,
    seed: int = 20260915,
) -> Interval:
    """ECE with a 95% interval that resamples scenarios, never rows."""
    probs = np.asarray(probs)
    labels = np.asarray(labels, dtype=int)
    keys = sorted(set(scenarios))
    index = {k: i for i, k in enumerate(keys)}
    cluster = np.array([index[s] for s in scenarios])
    per_cluster = np.zeros((len(keys), BINS, 3))
    for c in range(len(keys)):
        members = cluster == c
        per_cluster[c] = _bin_sums(probs[members], labels[members])
    rng = np.random.default_rng(seed)
    weights = rng.multinomial(
        len(keys), np.full(len(keys), 1 / len(keys)), size=bootstrap
    )
    samples = [_ece_from_bins(np.einsum("c,cij->ij", w, per_cluster)) for w in weights]
    return Interval(
        _ece_from_bins(per_cluster.sum(axis=0)),
        float(np.percentile(samples, 2.5)),
        float(np.percentile(samples, 97.5)),
    )


def reliability_svg(probs: np.ndarray, labels: np.ndarray) -> str:
    """The gate's reliability diagram, drawn for these predictions."""
    from training import evaluate as gate

    items = [
        gate.Item(
            f"i{k}",
            "unknown",
            int(labels[k]),
            f"s{k}",
            tuple(float(v) for v in probs[k]),
            None,
        )
        for k in range(len(labels))
    ]
    return gate.reliability_svg(items)


def calibration_split_shortfalls(
    labels: Sequence[int], languages: Sequence[str], scenarios: Sequence[str]
) -> list[str]:
    """Every language x class cell below EVAL_SET_SPEC's calibration allocation, counted in
    distinct scenarios. Empty when the split may be used to fit a temperature."""
    seen: dict[tuple[str, int], set[str]] = {}
    for label, language, scenario in zip(labels, languages, scenarios, strict=True):
        seen.setdefault((language, int(label)), set()).add(scenario)
    shortfalls = []
    for allocation in spec.CALIBRATION_ALLOCATION:
        for cls, need in enumerate(
            (allocation.critical, allocation.urgent, allocation.routine)
        ):
            have = len(seen.get((allocation.language, cls), set()))
            if have < need:
                shortfalls.append(
                    f"{allocation.language} {CLASS_NAMES[cls]}: {have} distinct scenarios, need {need}"
                )
    return shortfalls
