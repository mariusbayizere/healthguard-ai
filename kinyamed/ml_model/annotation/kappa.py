"""Cohen's kappa between two independent annotators, per language, with 95% intervals.

Computed on the labels as first given, BEFORE any adjudication (the protocol's rule:
a post-reconciliation kappa is not an agreement figure). Standard library only.

Categories are CRITICAL, URGENT, ROUTINE and UNCLASSIFIABLE; an UNCLASSIFIABLE label
is a disagreement with any urgency. Unweighted kappa is the primary figure because
§9.1 names Cohen's kappa; a linearly weighted kappa (urgency is ordered) is
reported beside it and never substituted for it.

A per-language kappa on fewer than `KAPPA_MINIMUM_ITEMS_PER_LANGUAGE` items is
refused, like every other metric in the gate.
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from training.eval_spec import KAPPA_MINIMUM_ITEMS_PER_LANGUAGE, KAPPA_TARGET

CATEGORIES = ("CRITICAL", "URGENT", "ROUTINE", "UNCLASSIFIABLE")
_ORDINAL = {"CRITICAL": 0, "URGENT": 1, "ROUTINE": 2}


def cohen_kappa(first: Sequence[str], second: Sequence[str]) -> float:
    if len(first) != len(second) or not first:
        raise ValueError("kappa needs two equal-length, non-empty label sequences")
    n = len(first)
    observed = sum(a == b for a, b in zip(first, second, strict=True)) / n
    c1, c2 = Counter(first), Counter(second)
    expected = sum(c1[k] * c2[k] for k in CATEGORIES) / (n * n)
    if expected == 1.0:
        return 1.0 if observed == 1.0 else 0.0
    return (observed - expected) / (1.0 - expected)


def linear_weighted_kappa(first: Sequence[str], second: Sequence[str]) -> float | None:
    """Over the three urgency classes only; None if any label is UNCLASSIFIABLE."""
    if any(x not in _ORDINAL for x in (*first, *second)):
        return None
    n, k = len(first), 3
    weight = lambda i, j: 1.0 - abs(i - j) / (k - 1)  # noqa: E731
    observed = (
        sum(
            weight(_ORDINAL[a], _ORDINAL[b]) for a, b in zip(first, second, strict=True)
        )
        / n
    )
    c1, c2 = Counter(_ORDINAL[a] for a in first), Counter(_ORDINAL[b] for b in second)
    expected = sum(weight(i, j) * c1[i] * c2[j] for i in range(k) for j in range(k)) / (
        n * n
    )
    return 1.0 if expected == 1.0 else (observed - expected) / (1.0 - expected)


@dataclass
class KappaRow:
    scope: str
    n: int
    verdict: str
    kappa: float | None = None
    ci: tuple[float, float] | None = None
    weighted: float | None = None


def _bootstrap(
    first: list[str], second: list[str], resamples: int, seed: int
) -> tuple[float, float]:
    rng = random.Random(seed)
    n = len(first)
    values = []
    for _ in range(resamples):
        idx = [rng.randrange(n) for _ in range(n)]
        values.append(cohen_kappa([first[i] for i in idx], [second[i] for i in idx]))
    values.sort()
    return values[int(0.025 * resamples)], values[
        min(resamples - 1, int(0.975 * resamples))
    ]


def kappa_report(
    pairs: Sequence[tuple[str, str, str]],
    *,
    resamples: int = 1000,
    seed: int = 20260914,
) -> list[KappaRow]:
    """pairs: (language, label from annotator 1, label from annotator 2)."""
    by_language: dict[str, list[tuple[str, str]]] = {}
    for language, a, b in pairs:
        by_language.setdefault(language, []).append((a, b))
    scopes = [
        ("all languages", [(a, b) for _, a, b in pairs]),
        *sorted(by_language.items()),
    ]
    rows = []
    for scope, labelled in scopes:
        n = len(labelled)
        if n < KAPPA_MINIMUM_ITEMS_PER_LANGUAGE:
            rows.append(
                KappaRow(
                    scope,
                    n,
                    f"INSUFFICIENT DATA (n={n}, need {KAPPA_MINIMUM_ITEMS_PER_LANGUAGE})",
                )
            )
            continue
        first, second = [a for a, _ in labelled], [b for _, b in labelled]
        kappa = cohen_kappa(first, second)
        lo, hi = _bootstrap(first, second, resamples, seed)
        if lo >= KAPPA_TARGET:
            verdict = "MET"
        elif hi < KAPPA_TARGET:
            verdict = "NOT MET"
        else:
            verdict = "NOT DEMONSTRATED"
        rows.append(
            KappaRow(
                scope, n, verdict, kappa, (lo, hi), linear_weighted_kappa(first, second)
            )
        )
    return rows


def render(rows: list[KappaRow]) -> str:
    lines = [
        f"Cohen's kappa, before adjudication (target >= {KAPPA_TARGET:g}, lower 95% bound)",
        "",
    ]
    for r in rows:
        if r.kappa is None:
            lines.append(f"  {r.scope:<22} {r.verdict}")
        else:
            weighted = "—" if r.weighted is None else f"{r.weighted:.3f}"
            lines.append(
                f"  {r.scope:<22} n={r.n:<5} kappa {r.kappa:.3f}  95% CI [{r.ci[0]:.3f}, {r.ci[1]:.3f}]  "
                f"linear-weighted {weighted}  {r.verdict}"
            )
    return "\n".join(lines)
