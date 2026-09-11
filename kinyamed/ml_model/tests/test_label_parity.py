"""AUDIT 1.3 — the two packages agree about urgency ordering.

The ML package and the backend do not import each other, deliberately: the
dataset pipeline is pure standard library so CI can run it with nothing
installed. That independence means the label ordering has two definitions, and
two definitions of a clinical ordering is exactly the failure this project has
already paid for once with `MINIMUM_CRITICAL_RECALL`.

This test is the seam. It fails the moment they diverge, which is the only
guarantee available short of merging the packages.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from dataset.labels import CLASS_ORDER, LABEL_MAP

BACKEND_MODEL = (
    Path(__file__).resolve().parents[2]
    / "backend"
    / "app"
    / "models"
    / "triage_result.py"
)


def _backend_priority() -> dict[str, int]:
    """Read the backend's ordering WITHOUT importing it.

    Parsed rather than imported because the backend needs SQLAlchemy and a
    settings object, and this suite must keep running with nothing installed.
    """
    tree = ast.parse(BACKEND_MODEL.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        # The declaration is ANNOTATED (`_URGENCY_PRIORITY: dict[...] = {...}`),
        # which parses as AnnAssign rather than Assign. Handling only Assign is
        # how the first version of this test failed to find it -- and a parity
        # test that silently finds nothing would be worse than no test, so the
        # lookup raises rather than returning an empty mapping.
        if isinstance(node, ast.AnnAssign):
            target, value_node = node.target, node.value
        elif isinstance(node, ast.Assign):
            target, value_node = node.targets[0], node.value
        else:
            continue
        if isinstance(target, ast.Name) and target.id == "_URGENCY_PRIORITY":
            out: dict[str, int] = {}
            assert isinstance(value_node, ast.Dict)
            for key, value in zip(value_node.keys, value_node.values, strict=True):
                # UrgencyLevel.CRITICAL -> "CRITICAL"
                assert isinstance(key, ast.Attribute)
                assert isinstance(value, ast.Constant)
                out[key.attr] = int(value.value)
            return out
    raise AssertionError("_URGENCY_PRIORITY not found in the backend model")


@pytest.mark.skipif(not BACKEND_MODEL.exists(), reason="backend package absent")
def test_the_two_packages_order_urgency_identically() -> None:
    backend = _backend_priority()

    assert set(backend) == set(LABEL_MAP), (
        f"class names differ: backend {sorted(backend)} vs ML {sorted(LABEL_MAP)}"
    )

    # The integer bases differ on purpose -- the ML package is 0-indexed for
    # the model head, the backend is 1-indexed for a queue sort key. What must
    # match is the ORDER, not the values.
    ml_order = sorted(LABEL_MAP, key=lambda name: LABEL_MAP[name])
    backend_order = sorted(backend, key=lambda name: backend[name])
    assert ml_order == backend_order, (
        f"urgency ORDER differs. ML says {ml_order}, backend says {backend_order}. "
        "One of them will sort a patient queue wrongly."
    )
    assert ml_order == list(CLASS_ORDER)


def test_the_ml_inverse_cannot_drift_from_the_map() -> None:
    from dataset.labels import ID_TO_LABEL

    assert {v: k for k, v in LABEL_MAP.items()} == ID_TO_LABEL
