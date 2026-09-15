"""Cost-sensitive training objective (docs/ENGINEERING_SPEC.md FR-04-13).

    loss = cross_entropy(logits, y) + cost_weight * E_p[ cost[y, predicted] ]

The second term is the expected misclassification cost under the model's own
softmax. It punishes probability mass on dangerous wrong classes, and above all on
ROUTINE for a CRITICAL case, far more than mass on an adjacent class.

THE DEFAULT COSTS ARE AN UNSOURCED ENGINEERING DEFAULT, not a clinical ruling. The
only property enforced here is the one docs/ENGINEERING_SPEC.md L3 states: CRITICAL -> ROUTINE is
strictly the most expensive error. The relative weights await the lead clinician
(STATE.md H6, A30), and are configurable so a ruling is a config change.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence

import torch

CRITICAL, URGENT, ROUTINE = 0, 1, 2  # dataset/labels.py LABEL_MAP order

# Rows: true class. Columns: predicted class. Order CRITICAL, URGENT, ROUTINE.
# UNSOURCED DEFAULT (H6): an adjacent error costs 1, CRITICAL -> ROUTINE costs 10,
# and over-triage ROUTINE -> CRITICAL costs 1.
DEFAULT_COST_MATRIX: tuple[tuple[float, float, float], ...] = (
    (0.0, 1.0, 10.0),
    (1.0, 0.0, 1.0),
    (1.0, 1.0, 0.0),
)


def iter_off_diagonal(
    matrix: Sequence[Sequence[float]],
) -> Iterator[tuple[tuple[int, int], float]]:
    for i, row in enumerate(matrix):
        for j, value in enumerate(row):
            if i != j:
                yield (i, j), float(value)


def validate_cost_matrix(matrix: Sequence[Sequence[float]]) -> None:
    """Refuse a matrix that is malformed or does not rank CRITICAL -> ROUTINE worst."""
    if len(matrix) != 3 or any(len(row) != 3 for row in matrix):
        raise ValueError("cost matrix must be 3 x 3 (CRITICAL, URGENT, ROUTINE)")
    if any(float(matrix[k][k]) != 0.0 for k in range(3)):
        raise ValueError("a correct prediction must cost 0 (diagonal)")
    if any(value < 0 for _, value in iter_off_diagonal(matrix)):
        raise ValueError("costs must be non-negative")
    worst = float(matrix[CRITICAL][ROUTINE])
    others = [
        v for (i, j), v in iter_off_diagonal(matrix) if (i, j) != (CRITICAL, ROUTINE)
    ]
    if not all(worst > v for v in others):
        raise ValueError(
            "CRITICAL -> ROUTINE must be strictly the most expensive error (docs/ENGINEERING_SPEC.md L3)"
        )


class CostSensitiveLoss(torch.nn.Module):
    """Cross-entropy plus `cost_weight` times the expected misclassification cost."""

    def __init__(
        self,
        cost_matrix: Sequence[Sequence[float]] = DEFAULT_COST_MATRIX,
        *,
        cost_weight: float = 1.0,
        class_weights: torch.Tensor | None = None,
    ) -> None:
        super().__init__()
        validate_cost_matrix(cost_matrix)
        if cost_weight < 0:
            raise ValueError("cost_weight must be non-negative")
        self.register_buffer(
            "cost", torch.tensor([[float(v) for v in row] for row in cost_matrix])
        )
        self.cost_weight = float(cost_weight)
        self.class_weights = class_weights

    def forward(self, logits: torch.Tensor, labels: torch.Tensor) -> torch.Tensor:
        cross_entropy = torch.nn.functional.cross_entropy(
            logits, labels, weight=self.class_weights
        )
        if self.cost_weight == 0.0:
            return cross_entropy
        probabilities = torch.softmax(logits, dim=-1)
        expected_cost = (probabilities * self.cost[labels]).sum(dim=-1).mean()
        return cross_entropy + self.cost_weight * expected_cost
