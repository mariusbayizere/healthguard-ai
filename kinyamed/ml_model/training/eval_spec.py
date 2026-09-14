#!/usr/bin/env python
"""The evaluation-set specification, as code: sizes, minimum cell counts, and the
exact statistics that justify them.

WHY THIS EXISTS
---------------
The only held-out set this project has is nine sentences (four CRITICAL). On it,
the phrase-cluster 95% interval for CRITICAL recall is 0.08 to 1.00: a safe model
and a dangerous one are indistinguishable. This module fixes, BEFORE any labels
exist, how large a real set must be for each gate metric to be a claim rather than
noise, and `training/evaluate.py` refuses to report any metric whose population is
below the minimum defined here.

ONE SOURCE OF TRUTH. `reports/EVAL_SET_SPEC.md` quotes the numbers this module
prints (`python training/eval_spec.py --report`), `evaluate.py` enforces them, and
`annotation/` builds the set to them. Change a number here and all three move.

THE DECISION RULE (a proposal, see EVAL_SET_SPEC.md §2)
-------------------------------------------------------
A threshold of the form "metric >= t" is MET only when the lower end of the
two-sided 95% interval is >= t; "metric < t" only when the upper end is < t. A
point estimate on the right side of t with an interval that crosses it is reported
as NOT DEMONSTRATED, not as a pass.

THE STATISTICS
--------------
Proportions (recall, precision, accuracy, rates) use the exact Clopper-Pearson
interval, computed here from the regularised incomplete beta function with the
standard library only. Power is exact: the probability, under an assumed true
value, of observing a count whose interval clears the threshold. Minimum sizes are
the smallest n at which power >= 0.80 holds for that n and the next 9 (binomial
power is saw-toothed in n; the first crossing alone can be followed by dips).

No clinical content lives here. Thresholds are CLAUDE.md §9.2's; the assumed true
values are design points stated beside each requirement, not measurements.
"""

from __future__ import annotations

import argparse
import math
import random
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

CONFIDENCE = 0.95
ALPHA_EACH_SIDE = (1 - CONFIDENCE) / 2  # 0.025: a two-sided 95% interval
TARGET_POWER = 0.80
POWER_STABLE_FOR = 10

PURE_LANGUAGES = ("kinyarwanda", "english", "french", "swahili")
# CLAUDE.md §4.4. Unordered pairs; the matrix language is recorded per item.
MIXED_LANGUAGES = (
    "kinyarwanda+english",
    "kinyarwanda+french",
    "kinyarwanda+swahili",
    "english+french",
    "english+swahili",
    "french+swahili",
)
LANGUAGES = PURE_LANGUAGES + MIXED_LANGUAGES
CLASSES = ("CRITICAL", "URGENT", "ROUTINE")
# An annotator may refuse a label. Such items go to adjudication and, if the
# adjudicator agrees, leave the gold set; they are counted and reported.
UNCLASSIFIABLE = "UNCLASSIFIABLE"


# ── Exact binomial machinery (standard library only) ─────────────────────────
def _betacf(a: float, b: float, x: float) -> float:
    """Continued fraction for the incomplete beta function (modified Lentz)."""
    tiny, eps = 1e-300, 3e-16
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 400):
        m2 = 2 * m
        for aa in (
            m * (b - m) * x / ((qam + m2) * (a + m2)),
            -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2)),
        ):
            d = 1.0 + aa * d
            d = 1.0 / (d if abs(d) > tiny else tiny)
            c = 1.0 + aa / c
            c = c if abs(c) > tiny else tiny
            h *= d * c
        if abs(d * c - 1.0) < eps:
            break
    return h


def betainc(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_front = (
        math.lgamma(a + b)
        - math.lgamma(a)
        - math.lgamma(b)
        + a * math.log(x)
        + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(log_front) * _betacf(a, b, x) / a
    return 1.0 - math.exp(log_front) * _betacf(b, a, 1.0 - x) / b


def prob_at_least(x: int, n: int, p: float) -> float:
    """P(X >= x) for X ~ Binomial(n, p)."""
    if x <= 0:
        return 1.0
    if x > n:
        return 0.0
    return betainc(x, n - x + 1, p)


def prob_at_most(x: int, n: int, p: float) -> float:
    """P(X <= x) for X ~ Binomial(n, p)."""
    return 1.0 - prob_at_least(x + 1, n, p)


def _bisect(condition: Callable[[float], bool]) -> float:
    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if condition(mid):
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2


def clopper_pearson(x: int, n: int) -> tuple[float, float]:
    """Exact two-sided 95% interval for x successes in n trials."""
    if n <= 0:
        raise ValueError("n must be positive")
    lower = (
        0.0 if x == 0 else _bisect(lambda p: prob_at_least(x, n, p) > ALPHA_EACH_SIDE)
    )
    upper = (
        1.0 if x == n else _bisect(lambda p: prob_at_most(x, n, p) < ALPHA_EACH_SIDE)
    )
    return lower, upper


def _first(n: int, predicate: Callable[[int], bool]) -> int:
    """Smallest x in [0, n] with predicate(x) true (predicate monotone), else n+1."""
    lo, hi = 0, n + 1
    while lo < hi:
        mid = (lo + hi) // 2
        if predicate(mid):
            hi = mid
        else:
            lo = mid + 1
    return lo


def power_at_least(n: int, true_value: float, threshold: float) -> float:
    """P(lower 95% bound >= threshold) when the true proportion is true_value."""
    x = _first(n, lambda m: clopper_pearson(m, n)[0] >= threshold)
    return 0.0 if x > n else prob_at_least(x, n, true_value)


def power_below(n: int, true_value: float, threshold: float) -> float:
    """P(upper 95% bound < threshold) when the true proportion is true_value."""
    first_failing = _first(n, lambda m: clopper_pearson(m, n)[1] >= threshold)
    return 0.0 if first_failing == 0 else prob_at_most(first_failing - 1, n, true_value)


def minimum_n(
    power: Callable[[int, float, float], float],
    true_value: float,
    threshold: float,
    *,
    start: int = 20,
    step: int = 5,
    stop: int = 50_000,
) -> int:
    """Smallest n (on a `step` grid) with power >= 0.80 for n and the next 9."""
    n = start
    while n < stop:
        if power(n, true_value, threshold) >= TARGET_POWER and all(
            power(m, true_value, threshold) >= TARGET_POWER
            for m in range(n + 1, n + POWER_STABLE_FOR)
        ):
            return n
        n += step
    raise ValueError("no n below the search limit reaches the target power")


def expected_ece_of_a_calibrated_model(
    n: int, *, bins: int = 15, trials: int = 300, seed: int = 7
) -> tuple[float, float]:
    """(mean, 95th percentile) ECE of a PERFECTLY calibrated model on n items.

    Pure sampling noise: confidences uniform on [1/3, 1], correctness drawn at
    exactly that confidence. Any ECE gate must sit well above this or it fails
    calibrated models by chance.
    """
    rng = random.Random(seed)
    values = []
    for _ in range(trials):
        confidence = [rng.uniform(1 / 3, 1) for _ in range(n)]
        correct = [rng.random() < c for c in confidence]
        values.append(expected_calibration_error(confidence, correct, bins=bins))
    values.sort()
    return sum(values) / trials, values[int(0.95 * trials)]


def expected_calibration_error(
    confidence: list[float], correct: list[bool], *, bins: int = 15
) -> float:
    """Equal-width-bin ECE. Bin b holds confidences in (b/bins, (b+1)/bins]."""
    n = len(confidence)
    if n == 0:
        raise ValueError("ECE of an empty set is undefined")
    total = 0.0
    for b in range(bins):
        members = [
            i
            for i, c in enumerate(confidence)
            if b / bins < c <= (b + 1) / bins or (b == 0 and c == 0.0)
        ]
        if members:
            mean_conf = sum(confidence[i] for i in members) / len(members)
            accuracy = sum(correct[i] for i in members) / len(members)
            total += len(members) / n * abs(mean_conf - accuracy)
    return total


# ── The requirements ──────────────────────────────────────────────────────────
Direction = Literal["at_least", "below"]


@dataclass(frozen=True)
class Requirement:
    """A gate metric and the smallest population on which it may be reported."""

    gate: str  # CLAUDE.md §9.2 number, or an X-gate
    metric: str
    threshold: float | None
    direction: Direction | None
    population: str  # what n counts
    minimum_n: int
    design_true_value: float | None
    rationale: str


ECE_THRESHOLD = 0.05
ECE_MINIMUM_N = 2000
LATENCY_MINIMUM_TIMED_REQUESTS = 1000

# Minimums derived by `derive_minimums()`; `--verify` recomputes them.
# Each is the power calculation named in its rationale.
REQUIREMENTS: tuple[Requirement, ...] = (
    Requirement(
        "1",
        "overall accuracy",
        0.82,
        "at_least",
        "all gold items",
        710,
        0.86,
        "Exact power, lower bound >= 0.82 with true 0.86.",
    ),
    Requirement(
        "2",
        "weighted F1",
        0.83,
        "at_least",
        "gold items of each class (pooled)",
        570,
        None,
        "No closed-form power for F1; bounded by the class populations of 5 and 8. "
        "Bootstrap interval reported.",
    ),
    Requirement(
        "3",
        "macro F1",
        0.80,
        "at_least",
        "gold items of each class (pooled)",
        570,
        None,
        "As 2.",
    ),
    Requirement(
        "4",
        "CRITICAL precision",
        0.88,
        "at_least",
        "items PREDICTED CRITICAL (pooled)",
        485,
        0.92,
        "Exact power, lower bound >= 0.88 with true 0.92. The denominator is set by "
        "the model, so this minimum can only be checked after inference.",
    ),
    Requirement(
        "5",
        "CRITICAL recall, each pure language",
        0.91,
        "at_least",
        "gold CRITICAL items in that language",
        365,
        0.95,
        "Exact power, lower bound >= 0.91 with true 0.95. At true 0.93 it is 1535; "
        "at true 0.97 it is 145. An observed recall of exactly 0.91 never clears.",
    ),
    Requirement(
        "6",
        "CRITICAL F1",
        0.89,
        "at_least",
        "gold CRITICAL items (pooled)",
        365,
        None,
        "Bounded by 4 and 5. Bootstrap interval reported.",
    ),
    Requirement(
        "7",
        "CRITICAL -> ROUTINE rate",
        0.01,
        "below",
        "gold CRITICAL items (pooled)",
        720,
        0.002,
        "Exact power, upper bound < 0.01 with a true rate of 0.2%. With zero observed "
        "events 368 suffice; at a true 0.5% it is 2470.",
    ),
    Requirement(
        "8",
        "URGENT recall",
        0.86,
        "at_least",
        "gold URGENT items (pooled)",
        570,
        0.90,
        "Exact power, lower bound >= 0.86 with true 0.90.",
    ),
    Requirement(
        "9",
        "Kinyarwanda accuracy",
        0.80,
        "at_least",
        "gold kinyarwanda items",
        780,
        0.84,
        "Exact power, lower bound >= 0.80 with true 0.84.",
    ),
    Requirement(
        "10",
        "English accuracy",
        0.86,
        "at_least",
        "gold english items",
        570,
        0.90,
        "Exact power, lower bound >= 0.86 with true 0.90.",
    ),
    Requirement(
        "11",
        "French accuracy",
        0.84,
        "at_least",
        "gold french items",
        640,
        0.88,
        "Exact power, lower bound >= 0.84 with true 0.88.",
    ),
    Requirement(
        "12",
        "Swahili accuracy",
        0.80,
        "at_least",
        "gold swahili items",
        780,
        0.84,
        "Exact power, lower bound >= 0.80 with true 0.84.",
    ),
    Requirement(
        "13",
        "mixed-language accuracy (pooled over the 6 pairs)",
        0.82,
        "at_least",
        "gold mixed items; and >= 100 in EACH pair",
        710,
        0.86,
        "Exact power on the pooled mixed items, lower bound >= 0.82 with true 0.86. "
        "The per-pair floor stops one pair standing in for six.",
    ),
    Requirement(
        "14",
        "inference latency p50 / p95",
        None,
        None,
        "timed batch-1 requests",
        LATENCY_MINIMUM_TIMED_REQUESTS,
        None,
        "A nearest-rank p95 over 1000 requests rests on its 50 slowest; fewer and a "
        "handful of scheduler stalls decide it.",
    ),
    Requirement(
        "15",
        "memory at 50 concurrent",
        None,
        None,
        "a 50-concurrent load run",
        1,
        None,
        "A measurement, not a sample: one run on the named target hardware (D5).",
    ),
    Requirement(
        "X-ECE",
        "expected calibration error (15 bins)",
        ECE_THRESHOLD,
        "below",
        "gold items with model confidences",
        ECE_MINIMUM_N,
        None,
        "Simulated (this module, seed 7): a perfectly calibrated model scores mean ECE "
        "0.061 at n=300 and p95 0.047 at n=1000, leaving no margin under a 0.05 gate; "
        "p95 is 0.033 at n=2000.",
    ),
    Requirement(
        "X-LID-pure",
        "language identification, pure languages",
        0.92,
        "at_least",
        "gold pure-language items",
        590,
        0.95,
        "Exact power, lower bound >= 0.92 with true 0.95.",
    ),
    Requirement(
        "X-LID-mixed",
        "language identification, mixed pairs",
        0.85,
        "at_least",
        "gold mixed items",
        380,
        0.90,
        "Exact power, lower bound >= 0.85 with true 0.90.",
    ),
)

# Cohen's kappa: the precision a per-language agreement claim needs.
KAPPA_TARGET = 0.80
KAPPA_MINIMUM_ITEMS_PER_LANGUAGE = 200


# ── The set these requirements imply ─────────────────────────────────────────
@dataclass(frozen=True)
class Allocation:
    language: str
    critical: int
    urgent: int
    routine: int

    @property
    def total(self) -> int:
        return self.critical + self.urgent + self.routine


# Per pure language: 400 CRITICAL clears 365 with ~9% for items adjudicated
# UNCLASSIFIABLE or excluded; 1000 in total clears the largest per-language
# accuracy minimum (780). Per mixed pair: 150 clears the per-pair floor of 100
# with the same margin, and 6 x 150 = 900 clears the pooled 710.
TEST_ALLOCATION: tuple[Allocation, ...] = tuple(
    Allocation(lang, 400, 300, 300) for lang in PURE_LANGUAGES
) + tuple(Allocation(lang, 60, 45, 45) for lang in MIXED_LANGUAGES)

# Fits ONE temperature parameter and nothing else; never scored. 300 per pure
# language keeps it from being dominated by one language.
CALIBRATION_ALLOCATION: tuple[Allocation, ...] = tuple(
    Allocation(lang, 100, 100, 100) for lang in PURE_LANGUAGES
) + tuple(Allocation(lang, 20, 15, 15) for lang in MIXED_LANGUAGES)

MIXED_PAIR_FLOOR = 100
UNCLASSIFIABLE_MARGIN = 0.09


def requirement(gate: str) -> Requirement:
    for req in REQUIREMENTS:
        if req.gate == gate:
            return req
    raise KeyError(gate)


def allocation_totals(allocation: tuple[Allocation, ...]) -> dict[str, int]:
    return {
        "items": sum(a.total for a in allocation),
        "CRITICAL": sum(a.critical for a in allocation),
        "URGENT": sum(a.urgent for a in allocation),
        "ROUTINE": sum(a.routine for a in allocation),
        "pure": sum(a.total for a in allocation if a.language in PURE_LANGUAGES),
        "mixed": sum(a.total for a in allocation if a.language in MIXED_LANGUAGES),
    }


def check_allocation_meets_requirements() -> list[str]:
    """Every minimum that the allocation fixes in advance, checked. Returns failures."""
    t = allocation_totals(TEST_ALLOCATION)
    by_lang = {a.language: a for a in TEST_ALLOCATION}
    failures = []

    def need(label: str, have: int, gate: str) -> None:
        if have < requirement(gate).minimum_n:
            failures.append(
                f"{label}: {have} < {requirement(gate).minimum_n} (gate {gate})"
            )

    need("all items", t["items"], "1")
    need("pooled URGENT", t["URGENT"], "8")
    need("pooled CRITICAL", t["CRITICAL"], "7")
    for lang in PURE_LANGUAGES:
        need(f"{lang} CRITICAL", by_lang[lang].critical, "5")
    need("kinyarwanda items", by_lang["kinyarwanda"].total, "9")
    need("english items", by_lang["english"].total, "10")
    need("french items", by_lang["french"].total, "11")
    need("swahili items", by_lang["swahili"].total, "12")
    need("mixed items", t["mixed"], "13")
    need("items with confidences", t["items"], "X-ECE")
    need("pure items (LID)", t["pure"], "X-LID-pure")
    need("mixed items (LID)", t["mixed"], "X-LID-mixed")
    for lang in MIXED_LANGUAGES:
        if by_lang[lang].total < MIXED_PAIR_FLOOR:
            failures.append(
                f"{lang}: {by_lang[lang].total} < {MIXED_PAIR_FLOOR} per pair"
            )
    for a in TEST_ALLOCATION:
        if a.language in PURE_LANGUAGES and a.total < KAPPA_MINIMUM_ITEMS_PER_LANGUAGE:
            failures.append(f"{a.language}: too few items for a kappa claim")
    return failures


def derive_minimums() -> dict[str, int]:
    """Recompute every power-derived minimum. Slow (about a minute and a half)."""
    derived: dict[str, int] = {}
    for req in REQUIREMENTS:
        if req.design_true_value is None or req.threshold is None:
            continue
        power = power_at_least if req.direction == "at_least" else power_below
        start = 300 if req.direction == "below" else 20
        derived[req.gate] = minimum_n(
            power, req.design_true_value, req.threshold, start=start
        )
    return derived


def _report() -> str:
    lines = [
        "| Gate | Metric | Threshold | Population (n counts) | Minimum n | Design true value |",
        "|---|---|---|---|---|---|",
    ]
    for r in REQUIREMENTS:
        th = (
            "—"
            if r.threshold is None
            else (
                f"≥ {r.threshold:g}"
                if r.direction == "at_least"
                else f"< {r.threshold:g}"
            )
        )
        tv = "—" if r.design_true_value is None else f"{r.design_true_value:g}"
        lines.append(
            f"| {r.gate} | {r.metric} | {th} | {r.population} | {r.minimum_n} | {tv} |"
        )
    lines.append("")
    lines.append("CP 95% interval at an observed recall of 0.91:")
    for n in (4, 50, 100, 200, 300, 400, 500, 1000):
        lo, hi = clopper_pearson(round(0.91 * n), n)
        lines.append(
            f"  n={n:>5}: [{lo:.3f}, {hi:.3f}]  half-width {(hi - lo) / 2:.3f}"
        )
    lines.append("")
    lines.append(
        "Power to show CRITICAL recall >= 0.91 (lower 95% bound), by true recall and n:"
    )
    for true in (0.93, 0.95, 0.97):
        row = "  ".join(
            f"n={n}: {power_at_least(n, true, 0.91):.2f}"
            for n in (100, 200, 365, 400, 800, 1535)
        )
        lines.append(f"  true {true}: {row}")
    lines.append("")
    lines.append(
        "Calibrated-model ECE from sampling noise alone (15 bins, 300 trials):"
    )
    for n in (300, 500, 1000, 2000, 4000):
        mean, p95 = expected_ece_of_a_calibrated_model(n)
        lines.append(f"  n={n:>5}: mean {mean:.4f}, p95 {p95:.4f}")
    t, c = allocation_totals(TEST_ALLOCATION), allocation_totals(CALIBRATION_ALLOCATION)
    lines.append("")
    lines.append(f"Test allocation: {t}")
    lines.append(f"Calibration allocation: {c}")
    failures = check_allocation_meets_requirements()
    lines.append(f"Allocation check: {failures if failures else 'PASS'}")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        action="store_true",
        help="print the tables quoted in EVAL_SET_SPEC.md",
    )
    parser.add_argument(
        "--verify", action="store_true", help="recompute every power-derived minimum"
    )
    args = parser.parse_args()
    if args.verify:
        derived = derive_minimums()
        stored = {r.gate: r.minimum_n for r in REQUIREMENTS if r.gate in derived}
        for gate, n in derived.items():
            print(f"gate {gate}: derived {n}, stored {stored[gate]}")
        return 0 if derived == stored else 1
    print(_report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
