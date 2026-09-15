"""training/cost_loss.py: a cost-sensitive objective (CLAUDE.md FR-04-13).

CRITICAL -> ROUTINE must cost far more than an adjacent error. Every test uses
synthetic labels; nothing here says anything about a real model.
"""

from __future__ import annotations

import pytest

torch = pytest.importorskip("torch", reason="the loss is a torch objective")

from training import cost_loss as cl  # noqa: E402

C, U, R = 0, 1, 2


def test_the_default_matrix_makes_critical_to_routine_the_most_expensive_error():
    m = cl.DEFAULT_COST_MATRIX
    assert all(m[k][k] == 0 for k in range(3))
    off_diagonal = [m[i][j] for i in range(3) for j in range(3) if i != j]
    assert m[C][R] == max(off_diagonal)
    assert all(m[C][R] > v for (i, j), v in cl.iter_off_diagonal(m) if (i, j) != (C, R))


@pytest.mark.parametrize(
    "matrix",
    [
        [[1, 1, 10], [1, 0, 1], [1, 1, 0]],  # non-zero diagonal
        [[0, 1, 10], [1, 0, -1], [1, 1, 0]],  # negative cost
        [[0, 5, 5], [1, 0, 1], [1, 1, 0]],  # CRITICAL->ROUTINE not strictly largest
        [[0, 1], [1, 0]],  # wrong shape
    ],
)
def test_an_unsafe_or_malformed_matrix_is_refused(matrix):
    with pytest.raises(ValueError):
        cl.CostSensitiveLoss(matrix)


def test_with_no_cost_weight_it_is_cross_entropy():
    logits = torch.tensor([[2.0, 0.5, -1.0], [0.1, 0.2, 0.3]])
    labels = torch.tensor([C, R])
    loss = cl.CostSensitiveLoss(cl.DEFAULT_COST_MATRIX, cost_weight=0.0)
    expected = torch.nn.functional.cross_entropy(logits, labels)
    assert torch.allclose(loss(logits, labels), expected)


def test_a_critical_case_predicted_routine_costs_more_than_predicted_urgent():
    """Same cross-entropy for the true class, different wrong-class mass."""
    loss = cl.CostSensitiveLoss(cl.DEFAULT_COST_MATRIX, cost_weight=1.0)
    toward_urgent = torch.log(torch.tensor([[0.2, 0.7, 0.1]]))
    toward_routine = torch.log(torch.tensor([[0.2, 0.1, 0.7]]))
    label = torch.tensor([C])
    assert loss(toward_routine, label) > loss(toward_urgent, label)


def test_training_on_synthetic_labels_reduces_critical_to_routine_errors():
    """A linear model on overlapping synthetic data, same seed and steps: the
    cost-sensitive objective leaves fewer CRITICAL rows predicted ROUTINE than plain
    cross-entropy does."""

    def train(cost_weight: float) -> int:
        generator = torch.Generator().manual_seed(7)
        n = 600
        labels = torch.randint(0, 3, (n,), generator=generator)
        centres = torch.tensor([[1.0, 0.0], [0.0, 0.0], [-1.0, 0.0]])
        features = centres[labels] + 0.9 * torch.randn(n, 2, generator=generator)
        torch.manual_seed(7)
        model = torch.nn.Linear(2, 3)
        optimiser = torch.optim.SGD(model.parameters(), lr=0.5)
        objective = cl.CostSensitiveLoss(
            cl.DEFAULT_COST_MATRIX, cost_weight=cost_weight
        )
        for _ in range(300):
            optimiser.zero_grad()
            objective(model(features), labels).backward()
            optimiser.step()
        predicted = model(features).argmax(dim=1)
        return int(((labels == C) & (predicted == R)).sum())

    plain, sensitive = train(0.0), train(2.0)
    assert sensitive < plain, (plain, sensitive)


def test_the_expected_cost_term_is_differentiable_and_finite():
    logits = torch.randn(8, 3, requires_grad=True)
    labels = torch.tensor([C, U, R, C, U, R, C, R])
    loss = cl.CostSensitiveLoss(cl.DEFAULT_COST_MATRIX, cost_weight=1.0)(logits, labels)
    loss.backward()
    assert torch.isfinite(loss) and logits.grad is not None


def test_the_loss_uses_the_dataset_label_order():
    """Silent killer #2 (label order): the cost matrix is indexed by these ids."""
    from dataset.labels import LABEL_MAP

    assert (LABEL_MAP["CRITICAL"], LABEL_MAP["URGENT"], LABEL_MAP["ROUTINE"]) == (
        cl.CRITICAL,
        cl.URGENT,
        cl.ROUTINE,
    )
