"""Decision thresholds tuned to CRITICAL safety, not to accuracy (CLAUDE.md FR-04-13).

THE RULE, applied to calibrated probabilities (training/calibration.py):

    CRITICAL  if p_critical >= t_critical
    URGENT    else if p_critical + p_urgent >= t_urgent
    ROUTINE   otherwise

It only ever escalates relative to its own thresholds: lowering t_critical can only
move a case up to CRITICAL, lowering t_urgent can only move ROUTINE up to URGENT.

THE CHOICE, on the CALIBRATION split only (never the test split):
  hard constraint 1  CRITICAL recall >= gate 5's threshold in EACH pure language
  hard constraint 2  CRITICAL -> ROUTINE rate < gate 7's threshold, pooled
  objective          lowest expected cost under the given cost matrix
  ties               the more escalating thresholds (lower t_critical, then t_urgent)

Accuracy appears nowhere. Both constraints can always be met by calling everything
CRITICAL, so the tuner never trades safety away; what safety costs in CRITICAL
precision or URGENT recall is REPORTED as a warning naming the gate that will then
fail on the test set. That is a model problem to fix by training, not by thresholds.

These are point estimates over calibration rows, used to pick two numbers. They are
not a gate result: only `training/evaluate.py` on the test split, with its
scenario-clustered intervals, says whether a gate is met. The targets are gate 5's
and 7's, which are themselves unsourced (STATE.md A30); the default cost matrix is
unsourced (H6). A clinical ruling on either is a config change.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field

import numpy as np
from training import eval_spec as spec

C, U, R = 0, 1, 2
GRID_STEPS = 101  # thresholds 0.00, 0.01, ..., 1.00


def _threshold(gate: str) -> float:
    value = spec.requirement(gate).threshold
    if value is None:
        raise RuntimeError(f"eval_spec gate {gate} has no threshold")
    return float(value)


CRITICAL_RECALL_TARGET = _threshold("5")
CRITICAL_TO_ROUTINE_TARGET = _threshold("7")
CRITICAL_PRECISION_TARGET = _threshold("4")
URGENT_RECALL_TARGET = _threshold("8")

NOTE = (
    "Point estimates on the calibration split, used only to choose thresholds; "
    "not a gate result. The test-split gate (training/evaluate.py) decides."
)


class ThresholdsRefused(ValueError):
    """The calibration data cannot support a threshold choice. Nothing is chosen."""


def decide(probs: np.ndarray, t_critical: float, t_urgent: float) -> np.ndarray:
    probs = np.asarray(probs, dtype=float)
    return np.where(
        probs[:, C] >= t_critical,
        C,
        np.where(probs[:, C] + probs[:, U] >= t_urgent, U, R),
    )


def grid() -> Iterator[tuple[float, float]]:
    values = [round(k / (GRID_STEPS - 1), 2) for k in range(GRID_STEPS)]
    for t_critical in values:
        for t_urgent in values:
            yield t_critical, t_urgent


def meets_recall(recall: float) -> bool:
    return recall >= CRITICAL_RECALL_TARGET  # gate 5 is "at least"


def meets_rate(rate: float) -> bool:
    return rate < CRITICAL_TO_ROUTINE_TARGET  # gate 7 is "below"


def expected_cost(
    decided: np.ndarray, labels: np.ndarray, cost_matrix: Sequence[Sequence[float]]
) -> float:
    costs = np.asarray(cost_matrix, dtype=float)
    return float(costs[np.asarray(labels), decided].mean())


def _critical_recall_by_language(
    decided: np.ndarray, labels: np.ndarray, languages: np.ndarray
) -> dict[str, float]:
    out = {}
    for language in spec.PURE_LANGUAGES:
        rows = (languages == language) & (labels == C)
        out[language] = (
            float((decided[rows] == C).mean()) if rows.any() else float("nan")
        )
    return out


def _critical_to_routine_rate(decided: np.ndarray, labels: np.ndarray) -> float:
    critical = labels == C
    return float((decided[critical] == R).mean())


def is_safe(decided: np.ndarray, labels: np.ndarray, languages: Sequence[str]) -> bool:
    labels = np.asarray(labels)
    recalls = _critical_recall_by_language(decided, labels, np.asarray(languages))
    return all(meets_recall(r) for r in recalls.values()) and meets_rate(
        _critical_to_routine_rate(decided, labels)
    )


@dataclass(frozen=True)
class Thresholds:
    critical: float
    urgent: float
    expected_cost: float = float("nan")
    recall_by_language: dict[str, float] = field(default_factory=dict)
    critical_to_routine_rate: float = float("nan")
    critical_precision: float = float("nan")
    urgent_recall: float = float("nan")
    cost_matrix: tuple[tuple[float, ...], ...] = ()
    warnings: tuple[str, ...] = ()

    @classmethod
    def bare(cls, critical: float, urgent: float) -> Thresholds:
        return cls(critical, urgent)

    def as_record(self) -> dict[str, object]:
        return {
            "rule": "CRITICAL if p_C >= critical; URGENT if p_C + p_U >= urgent; else ROUTINE",
            "critical": self.critical,
            "urgent": self.urgent,
            "expected_cost": self.expected_cost,
            "recall_by_language": self.recall_by_language,
            "critical_to_routine_rate": self.critical_to_routine_rate,
            "critical_precision": self.critical_precision,
            "urgent_recall": self.urgent_recall,
            "targets": {
                "gate 5 CRITICAL recall, each pure language, at least": CRITICAL_RECALL_TARGET,
                "gate 7 CRITICAL -> ROUTINE rate, below": CRITICAL_TO_ROUTINE_TARGET,
            },
            "cost_matrix": [list(row) for row in self.cost_matrix],
            "warnings": list(self.warnings),
            "note": NOTE,
        }


def _validate(probs: np.ndarray, labels: np.ndarray, languages: Sequence[str]) -> None:
    if probs.ndim != 2 or probs.shape[1] != 3 or len(probs) == 0:
        raise ValueError("need a non-empty (n, 3) probability array")
    if len(labels) != len(probs) or len(languages) != len(probs):
        raise ValueError("probabilities, labels and languages differ in length")
    if (
        (probs < 0).any()
        or (probs > 1).any()
        or (np.abs(probs.sum(axis=1) - 1) > 1e-4).any()
    ):
        raise ValueError("every row of probabilities must be a distribution")
    missing = [
        language
        for language in spec.PURE_LANGUAGES
        if not ((np.asarray(languages) == language) & (labels == C)).any()
    ]
    if missing:
        raise ThresholdsRefused(
            "no gold CRITICAL rows in the calibration split for "
            + ", ".join(missing)
            + ": CRITICAL recall cannot be constrained there"
        )


def tune(
    probs: np.ndarray,
    labels: Sequence[int] | np.ndarray,
    languages: Sequence[str],
    cost_matrix: Sequence[Sequence[float]],
) -> Thresholds:
    from training.cost_loss import validate_cost_matrix

    validate_cost_matrix(cost_matrix)
    probs = np.asarray(probs, dtype=float)
    labels = np.asarray(labels, dtype=int)
    _validate(probs, labels, languages)
    language_array = np.asarray(languages)

    # Exhaustive over the grid, vectorised over t_urgent. Recall depends on
    # t_critical alone and never rises with it, so the first t_critical that fails
    # the recall constraint ends the search.
    costs = np.asarray(cost_matrix, dtype=float)
    values = np.array(sorted({t for t, _ in grid()}))
    is_critical = labels == C
    at_least_urgent = (probs[:, C] + probs[:, U])[:, None] >= values[None, :]
    best: tuple[float, float, float] | None = None
    for t_critical in values:
        predicted_critical = probs[:, C] >= t_critical
        recalls = _critical_recall_by_language(
            np.where(predicted_critical, C, R), labels, language_array
        )
        if not all(meets_recall(r) for r in recalls.values()):
            break
        rest = ~predicted_critical[:, None]
        urgent = rest & at_least_urgent
        routine = rest & ~at_least_urgent
        rate = (routine & is_critical[:, None]).sum(axis=0) / is_critical.sum()
        total = (
            (predicted_critical * costs[labels, C]).sum()
            + (urgent * costs[labels, U][:, None]).sum(axis=0)
            + (routine * costs[labels, R][:, None]).sum(axis=0)
        ) / len(labels)
        feasible = np.flatnonzero([meets_rate(float(r)) for r in rate])
        if feasible.size == 0:
            continue
        k = feasible[np.argmin(total[feasible])]
        if best is None or total[k] < best[0] - 1e-12:
            best = (float(total[k]), float(t_critical), float(values[k]))
    if best is None:  # unreachable while the grid includes t_critical = 0
        raise ThresholdsRefused("no threshold pair meets both safety constraints")

    cost, t_critical, t_urgent = best
    decided = decide(probs, t_critical, t_urgent)
    predicted_critical = decided == C
    precision = (
        float((labels[predicted_critical] == C).mean())
        if predicted_critical.any()
        else float("nan")
    )
    urgent_rows = labels == U
    urgent_recall = (
        float((decided[urgent_rows] == U).mean()) if urgent_rows.any() else float("nan")
    )
    warnings = []
    if not precision >= CRITICAL_PRECISION_TARGET:
        warnings.append(
            "meeting the safety constraints puts CRITICAL precision below gate 4's "
            "threshold on the calibration split (a point estimate, no interval): "
            "expect gate 4 to fail on the test split"
        )
    if not urgent_recall >= URGENT_RECALL_TARGET:
        warnings.append(
            "URGENT recall at these thresholds is below gate 8's threshold on the "
            "calibration split (a point estimate, no interval): expect gate 8 to fail "
            "on the test split"
        )
    return Thresholds(
        critical=t_critical,
        urgent=t_urgent,
        expected_cost=cost,
        recall_by_language=_critical_recall_by_language(
            decided, labels, language_array
        ),
        critical_to_routine_rate=_critical_to_routine_rate(decided, labels),
        critical_precision=precision,
        urgent_recall=urgent_recall,
        cost_matrix=tuple(tuple(float(v) for v in row) for row in cost_matrix),
        warnings=tuple(warnings),
    )
