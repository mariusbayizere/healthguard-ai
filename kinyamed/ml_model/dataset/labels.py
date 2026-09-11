"""The label ordering, defined once for the ML package.

AUDIT 1.3. This existed in five independent copies across the repository:
`process_dataset.py`, `build_dataset.py`, `training/config.py`, a backend test
and the frontend. Two of those were added after the project had already been
bitten by a duplicated `MINIMUM_CRITICAL_RECALL`.

`dataset/` cannot import from `training/` -- the dataset pipeline is pure
standard library by design, which is what lets CI run it with nothing
installed -- so the constant lives at the bottom of the dependency graph where
both can reach it.

The backend has its own canonical definition in `UrgencyLevel.priority`,
because the two packages do not import each other. They are kept in step by
`tests/test_label_parity.py`, which fails if they diverge.
"""

from __future__ import annotations

#: Class name -> integer id, in clinical order. Most urgent first.
LABEL_MAP: dict[str, int] = {"CRITICAL": 0, "URGENT": 1, "ROUTINE": 2}

#: Inverse of LABEL_MAP, derived so the two cannot disagree.
ID_TO_LABEL: dict[int, str] = {v: k for k, v in LABEL_MAP.items()}

#: Ordered class names, most urgent first.
CLASS_ORDER: tuple[str, ...] = tuple(LABEL_MAP)

NUM_LABELS: int = len(LABEL_MAP)
