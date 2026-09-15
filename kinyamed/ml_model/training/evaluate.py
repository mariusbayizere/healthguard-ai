#!/usr/bin/env python
"""The deployment gate: all 15 metrics of CLAUDE.md §9.2, with 95% intervals, per
language, plus calibration and language identification — and a refusal to report
any metric on too little data.

    python training/evaluate.py --gold eval/gold_test.csv --predictions preds.csv \
        --latency training/latency_v2d.json --memory memory.json --out reports/gate

    python training/evaluate.py --gold eval/gold_test.csv --model ~/kinyamed-runs/model_v2d

REFUSAL IS THE POINT
--------------------
Every metric has a population (what its n counts) and a minimum n from
`training/eval_spec.py`. Below it the report prints

    INSUFFICIENT DATA (n=X, need Y)

and no number. A recall computed on four sentences is not a weak result; it is
not a result, and printing it invites someone to quote it.

VERDICTS
--------
MET               the whole 95% interval is on the passing side of the threshold
NOT MET           the whole interval is on the failing side
NOT DEMONSTRATED  the interval contains the threshold
INSUFFICIENT DATA below the specification's minimum n
NOT MEASURED      the input needed was not supplied (latency, memory, LID)

For proportions the deciding bound is the more conservative of the exact
Clopper-Pearson and the cluster-bootstrap interval. F1 and ECE have bootstrap
intervals only. The process exits 0 only if every gate is MET, so CI can block on it.

INPUTS
------
--gold          frozen gold CSV built by `annotation build-gold`: item_id, text,
                language, gold_label, scenario_id, split. Only split=test is scored.
--predictions   item_id, p_critical, p_urgent, p_routine[, detected_language]
--model         run the model instead (needs torch and transformers)

The previous evaluate.py (frozen-manifest holdout evaluation and the paper tables)
lives in `training/holdout_eval.py` and must be run by that name: this entry point
refuses `--writeup`, `--manifest` and `--model` without `--gold`, because that report
applies no minimum-n refusal. Its names are re-exported for existing importers.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from training import eval_spec as spec

# Legacy names, re-exported unchanged: train_holdout.py imports the old 3-condition
# gate, and tests import load_manifest, from `training.evaluate`.
from training.holdout_eval import (  # noqa: F401
    CLASS_ORDER,
    CRITICAL_PRECISION_MARGIN,
    MINIMUM_CRITICAL_RECALL,
    MINIMUM_MACRO_F1,
    load_manifest,
    triage_gate,
)

CLASSES = spec.CLASSES
C, U, R = 0, 1, 2
BINS = 15
DEFAULT_BOOTSTRAP = 2000
LATENCY_P50_MS = 150.0
LATENCY_P95_MS = 200.0
MEMORY_LIMIT_MB = 2048.0

VERDICT_MET = "MET"
VERDICT_NOT_MET = "NOT MET"
VERDICT_UNDEMONSTRATED = "NOT DEMONSTRATED"


class InputError(ValueError):
    """The inputs cannot be scored as given. Nothing is reported."""


# ── Inputs ────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class Item:
    item_id: str
    language: str
    gold: int
    scenario: str
    probs: tuple[float, float, float]
    detected_language: str | None
    # The served decision when it is not the argmax (training/thresholds.py). Every
    # classification metric scores this; calibration (ECE) always scores the argmax.
    decision: int | None = None

    @property
    def argmax(self) -> int:
        # Ties resolve to the more urgent class.
        best = max(self.probs)
        return self.probs.index(best)

    @property
    def pred(self) -> int:
        return self.argmax if self.decision is None else self.decision

    @property
    def confidence(self) -> float:
        return max(self.probs)


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_items(
    gold_path: Path, predictions: dict[str, dict[str, str]]
) -> tuple[list[Item], dict]:
    """Join gold and predictions, validating both. Returns (items, exclusions)."""
    rows = _read_csv(gold_path)
    required = {"item_id", "language", "gold_label", "scenario_id"}
    if not rows or not required <= rows[0].keys():
        raise InputError(f"{gold_path} needs columns {sorted(required)}")
    items: list[Item] = []
    seen: set[str] = set()
    excluded = {"unclassifiable": 0, "not_test_split": 0}
    for row in rows:
        item_id = row["item_id"].strip()
        if item_id in seen:
            raise InputError(f"duplicate item_id {item_id!r} in gold")
        seen.add(item_id)
        if row.get("split", "test").strip() != "test":
            excluded["not_test_split"] += 1
            continue
        label = row["gold_label"].strip()
        if label == spec.UNCLASSIFIABLE:
            excluded["unclassifiable"] += 1
            continue
        if label not in CLASSES:
            raise InputError(
                f"item {item_id}: gold_label {label!r} is not one of {CLASSES}"
            )
        scenario = (row.get("scenario_id") or "").strip()
        if not scenario:
            raise InputError(
                f"item {item_id}: no scenario_id. Every item carries one (D7 protocol "
                "§2.3); without it each row would count as an independent scenario"
            )
        language = row["language"].strip()
        if language not in spec.LANGUAGES:
            raise InputError(
                f"item {item_id}: language {language!r} is not in the spec"
            )
        if item_id not in predictions:
            raise InputError(f"no prediction for gold item {item_id!r}")
        p = predictions[item_id]
        try:
            probs = (
                float(p["p_critical"]),
                float(p["p_urgent"]),
                float(p["p_routine"]),
            )
        except (KeyError, ValueError) as error:
            raise InputError(
                f"item {item_id}: unreadable probabilities ({error})"
            ) from error
        if any(not 0.0 <= v <= 1.0 for v in probs) or abs(sum(probs) - 1.0) > 1e-4:
            raise InputError(
                f"item {item_id}: probabilities {probs} are not a distribution"
            )
        detected = (p.get("detected_language") or "").strip() or None
        decided = (p.get("predicted_label") or "").strip()
        if decided and decided not in CLASSES:
            raise InputError(
                f"item {item_id}: predicted_label {decided!r} is not one of {CLASSES}"
            )
        items.append(
            Item(
                item_id=item_id,
                language=language,
                gold=CLASSES.index(label),
                scenario=scenario,
                probs=probs,
                detected_language=detected,
                decision=CLASSES.index(decided) if decided else None,
            )
        )
    return items, excluded


def load_predictions(path: Path) -> dict[str, dict[str, str]]:
    rows = _read_csv(path)
    if (
        not rows
        or not {"item_id", "p_critical", "p_urgent", "p_routine"} <= rows[0].keys()
    ):
        raise InputError(f"{path} needs item_id, p_critical, p_urgent, p_routine")
    return {row["item_id"].strip(): row for row in rows}


# ── Counting, per scenario, so the bootstrap resamples scenarios ──────────────
# Per scenario: a 10-language x 3 x 3 confusion tensor, 15 ECE bins x
# (count, sum confidence, sum correct), and per-language LID (n, correct).
N_LANG = len(spec.LANGUAGES)


def _cluster_arrays(items: list[Item]):
    import numpy as np

    scenarios = sorted({i.scenario for i in items})
    index = {s: k for k, s in enumerate(scenarios)}
    confusion = np.zeros((len(scenarios), N_LANG, 3, 3), dtype=np.int64)
    ece = np.zeros((len(scenarios), BINS, 3), dtype=np.float64)
    lid = np.zeros((len(scenarios), N_LANG, 2), dtype=np.int64)
    for item in items:
        k, lang = index[item.scenario], spec.LANGUAGES.index(item.language)
        confusion[k, lang, item.gold, item.pred] += 1
        b = min(BINS - 1, max(0, math.ceil(item.confidence * BINS) - 1))
        ece[k, b] += (1.0, item.confidence, float(item.argmax == item.gold))
        if item.detected_language is not None:
            lid[k, lang, 0] += 1
            lid[k, lang, 1] += int(
                _same_language(item.detected_language, item.language)
            )
    return confusion, ece, lid


def _same_language(detected: str, gold: str) -> bool:
    """Pure: exact name. Mixed: the same unordered pair (the generic 'mixed' is wrong)."""
    if "+" in gold:
        return set(detected.split("+")) == set(gold.split("+"))
    return detected == gold


# ── Metric definitions over a (languages x 3 x 3) confusion array ─────────────
PURE_IDX = [spec.LANGUAGES.index(lang) for lang in spec.PURE_LANGUAGES]
MIXED_IDX = [spec.LANGUAGES.index(lang) for lang in spec.MIXED_LANGUAGES]


def _f1(cm, cls: int) -> float:
    tp = cm[cls, cls]
    predicted, actual = cm[:, cls].sum(), cm[cls, :].sum()
    if tp == 0:
        return 0.0
    precision, recall = tp / predicted, tp / actual
    return float(2 * precision * recall / (precision + recall))


def _ece(bins) -> float:
    n = bins[:, 0].sum()
    if n == 0:
        return float("nan")
    total = 0.0
    for count, sum_conf, sum_correct in bins:
        if count:
            total += count / n * abs(sum_conf / count - sum_correct / count)
    return float(total)


@dataclass
class MetricSpec:
    gate: str
    name: str
    # (x, n) for proportion metrics, else None; always returns the population n.
    counts: object
    value: object  # confusion/ece/lid arrays -> float
    minimum_n: int
    threshold: float | None
    direction: str | None
    extra_floor: object = None  # returns a failure string or None
    # Distinct scenarios in the population, from per-scenario arrays. Defaults to
    # scenarios contributing at least one item to `counts`' n.
    scenarios: object = None


def _metric_specs() -> list[MetricSpec]:
    req = spec.requirement
    out: list[MetricSpec] = []

    def prop(gate, name, xn, minimum=None, extra_floor=None):
        r = req(gate)
        out.append(
            MetricSpec(
                gate,
                name,
                xn,
                lambda arrays, xn=xn: _ratio(*xn(*arrays)),
                minimum if minimum is not None else r.minimum_n,
                r.threshold,
                r.direction,
                extra_floor,
            )
        )

    def pooled(cm):
        return cm.sum(axis=0)

    prop(
        "1",
        "overall accuracy",
        lambda cm, e, lid: (int(pooled(cm).trace()), int(pooled(cm).sum())),
    )

    def f1_metric(gate, name, fn, min_population, classes=(C, U, R)):
        r = req(gate)
        out.append(
            MetricSpec(
                gate,
                name,
                lambda cm, e, lid, fn=min_population: (None, fn(cm)),
                lambda arrays, fn=fn: fn(pooled(arrays[0])),
                r.minimum_n,
                r.threshold,
                r.direction,
                scenarios=lambda clusters, classes=classes: min(
                    _scenarios_with_gold(clusters, cls) for cls in classes
                ),
            )
        )

    def weighted_f1(cm):
        support = cm.sum(axis=1)
        return float(sum(_f1(cm, k) * support[k] for k in range(3)) / support.sum())

    smallest_class = lambda cm: int(pooled(cm).sum(axis=1).min())  # noqa: E731
    f1_metric("2", "weighted F1", weighted_f1, smallest_class)
    f1_metric(
        "3",
        "macro F1",
        lambda cm: sum(_f1(cm, k) for k in range(3)) / 3,
        smallest_class,
    )
    prop(
        "4",
        "CRITICAL precision",
        lambda cm, e, lid: (int(pooled(cm)[C, C]), int(pooled(cm)[:, C].sum())),
    )
    for lang in spec.PURE_LANGUAGES:
        k = spec.LANGUAGES.index(lang)
        prop(
            "5",
            f"CRITICAL recall [{lang}]",
            lambda cm, e, lid, k=k: (int(cm[k, C, C]), int(cm[k, C, :].sum())),
        )
    f1_metric(
        "6",
        "CRITICAL F1",
        lambda cm: _f1(cm, C),
        lambda cm: int(pooled(cm)[C, :].sum()),
        classes=(C,),
    )
    prop(
        "7",
        "CRITICAL -> ROUTINE rate",
        lambda cm, e, lid: (int(pooled(cm)[C, R]), int(pooled(cm)[C, :].sum())),
    )
    prop(
        "8",
        "URGENT recall",
        lambda cm, e, lid: (int(pooled(cm)[U, U]), int(pooled(cm)[U, :].sum())),
    )
    for gate, lang in (
        ("9", "kinyarwanda"),
        ("10", "english"),
        ("11", "french"),
        ("12", "swahili"),
    ):
        k = spec.LANGUAGES.index(lang)
        prop(
            gate,
            f"accuracy [{lang}]",
            lambda cm, e, lid, k=k: (int(cm[k].trace()), int(cm[k].sum())),
        )

    def pair_floor(arrays):
        cm = arrays[0]
        short = [
            f"{spec.LANGUAGES[k]} n={int(cm[k].sum())}"
            for k in MIXED_IDX
            if cm[k].sum() < spec.MIXED_PAIR_FLOOR
        ]
        return (
            f"per-pair floor {spec.MIXED_PAIR_FLOOR}: {', '.join(short)}"
            if short
            else None
        )

    prop(
        "13",
        "mixed-language accuracy (pooled)",
        lambda cm, e, lid: (
            int(sum(cm[k].trace() for k in MIXED_IDX)),
            int(sum(cm[k].sum() for k in MIXED_IDX)),
        ),
        extra_floor=pair_floor,
    )
    # CLAUDE.md §16: every metric, per language. Gates 5 and 9-12 are already per
    # language; these are the pooled gates again for each pure language, with the
    # pooled gate's own threshold and minimum n. Mixed pairs are covered by gate 13
    # and its per-pair floor.
    for lang in spec.PURE_LANGUAGES:
        k = spec.LANGUAGES.index(lang)

        def lang_f1(gate, name, fn, classes, k=k, lang=lang):
            r = req(gate)
            out.append(
                MetricSpec(
                    gate,
                    f"{name} [{lang}]",
                    lambda cm, e, lid, k=k, classes=classes: (
                        None,
                        int(min(cm[k, cls, :].sum() for cls in classes)),
                    ),
                    lambda arrays, fn=fn, k=k: fn(arrays[0][k]),
                    r.minimum_n,
                    r.threshold,
                    r.direction,
                    scenarios=lambda clusters, k=k, classes=classes: min(
                        _scenarios_with_gold(clusters, cls, [k]) for cls in classes
                    ),
                )
            )

        lang_f1("2", "weighted F1", weighted_f1, (C, U, R))
        lang_f1(
            "3", "macro F1", lambda cm: sum(_f1(cm, c) for c in range(3)) / 3, (C, U, R)
        )
        prop(
            "4",
            f"CRITICAL precision [{lang}]",
            lambda cm, e, lid, k=k: (int(cm[k, C, C]), int(cm[k, :, C].sum())),
        )
        lang_f1("6", "CRITICAL F1", lambda cm: _f1(cm, C), (C,))
        prop(
            "7",
            f"CRITICAL -> ROUTINE rate [{lang}]",
            lambda cm, e, lid, k=k: (int(cm[k, C, R]), int(cm[k, C, :].sum())),
        )
        prop(
            "8",
            f"URGENT recall [{lang}]",
            lambda cm, e, lid, k=k: (int(cm[k, U, U]), int(cm[k, U, :].sum())),
        )

    r = req("X-ECE")
    out.append(
        MetricSpec(
            "X-ECE",
            "expected calibration error",
            lambda cm, e, lid: (None, int(e[:, 0].sum())),
            lambda arrays: _ece(arrays[1]),
            r.minimum_n,
            r.threshold,
            r.direction,
        )
    )
    prop(
        "X-LID-pure",
        "language identification [pure]",
        lambda cm, e, lid: (
            int(sum(lid[k, 1] for k in PURE_IDX)),
            int(sum(lid[k, 0] for k in PURE_IDX)),
        ),
    )
    prop(
        "X-LID-mixed",
        "language identification [mixed pairs]",
        lambda cm, e, lid: (
            int(sum(lid[k, 1] for k in MIXED_IDX)),
            int(sum(lid[k, 0] for k in MIXED_IDX)),
        ),
    )
    return out


def _scenarios_with_gold(clusters, cls: int, languages=None) -> int:
    """Scenarios with at least one gold item of `cls` (in `languages`, default all)."""
    confusion = clusters[0]
    if languages is not None:
        confusion = confusion[:, languages]
    return int((confusion[..., cls, :].sum(axis=(1, 2)) > 0).sum())


def _population_scenarios(metric: MetricSpec, clusters) -> int:
    """Distinct scenarios in a metric's population: the unit its minimum was powered for."""
    if metric.scenarios is not None:
        return int(metric.scenarios(clusters))
    confusion, ece_bins, lid = clusters
    return sum(
        1
        for k in range(confusion.shape[0])
        if metric.counts(confusion[k], ece_bins[k], lid[k])[1] > 0
    )


def _ratio(x: int, n: int) -> float:
    return x / n if n else float("nan")


# ── Evaluation ────────────────────────────────────────────────────────────────
@dataclass
class Row:
    gate: str
    metric: str
    n: int
    minimum_n: int
    threshold: str
    verdict: str
    point: float | None = None
    ci_exact: tuple[float, float] | None = None
    ci_bootstrap: tuple[float, float] | None = None
    note: str | None = None


def _threshold_text(threshold, direction) -> str:
    if threshold is None:
        return "—"
    return f">= {threshold:g}" if direction == "at_least" else f"< {threshold:g}"


def _verdict(lower: float, upper: float, threshold: float, direction: str) -> str:
    if direction == "at_least":
        if lower >= threshold:
            return VERDICT_MET
        return VERDICT_NOT_MET if upper < threshold else VERDICT_UNDEMONSTRATED
    if upper < threshold:
        return VERDICT_MET
    return VERDICT_NOT_MET if lower >= threshold else VERDICT_UNDEMONSTRATED


def insufficient(n: int, need: int, rows: int | None = None) -> str:
    """The refusal. When rows repeat source sentences, both counts are printed: the
    minimum is on distinct source sentences (scenario_id), not rows."""
    if rows is not None and rows > n:
        return (
            f"INSUFFICIENT DATA ({rows:,} rows from {n:,} distinct source "
            f"{'sentence' if n == 1 else 'sentences'}; "
            f"need {need:,} distinct)"
        )
    return f"INSUFFICIENT DATA (n={n}, need {need})"


def _population(m: MetricSpec, point_arrays, clusters, one_item_per_scenario: bool):
    """(x, rows in the population, distinct source sentences in the population)."""
    x, n_items = m.counts(*point_arrays)
    n = (
        n_items
        if one_item_per_scenario
        else min(n_items, _population_scenarios(m, clusters))
    )
    return x, n_items, n


def evaluate(
    items: list[Item], *, bootstrap: int = DEFAULT_BOOTSTRAP, seed: int = 20260914
) -> list[Row]:
    """Every data-derived gate row. Scenarios are the bootstrap's resampling unit."""
    import numpy as np

    confusion, ece_bins, lid = _cluster_arrays(items)
    point_arrays = (confusion.sum(axis=0), ece_bins.sum(axis=0), lid.sum(axis=0))
    has_lid = any(i.detected_language is not None for i in items)

    # All resamples at once: scenario multiplicities, then aggregated arrays.
    n_clusters = confusion.shape[0]
    rng = np.random.default_rng(seed)
    weights = rng.multinomial(
        n_clusters, np.full(n_clusters, 1.0 / n_clusters), size=bootstrap
    )
    boot_confusion = np.einsum("bc,clij->blij", weights, confusion)
    boot_ece = np.einsum("bc,cij->bij", weights, ece_bins)
    boot_lid = np.einsum("bc,clj->blj", weights, lid)

    clusters = (confusion, ece_bins, lid)
    # One item per scenario (the spec's test split): scenarios and items coincide.
    one_item_per_scenario = confusion.sum(axis=(1, 2, 3)).max(initial=0) <= 1
    rows: list[Row] = []
    for m in _metric_specs():
        # The minimum is on independent scenarios, not rows: 2,000 rows built from
        # four sentences are four observations (EVAL_SET_SPEC §8).
        x, n_items, n = _population(m, point_arrays, clusters, one_item_per_scenario)
        th = _threshold_text(m.threshold, m.direction)
        if m.gate.startswith("X-LID") and not has_lid:
            rows.append(
                Row(
                    m.gate,
                    m.name,
                    0,
                    m.minimum_n,
                    th,
                    "NOT MEASURED (no detected_language column)",
                )
            )
            continue
        if n < m.minimum_n:
            rows.append(
                Row(
                    m.gate,
                    m.name,
                    n,
                    m.minimum_n,
                    th,
                    insufficient(n, m.minimum_n, n_items),
                )
            )
            continue
        if n < n_items:
            rows_note = f"{n_items} items in {n} scenarios"
        else:
            rows_note = None
        floor = m.extra_floor(point_arrays) if m.extra_floor else None
        if floor:
            rows.append(
                Row(m.gate, m.name, n, m.minimum_n, th, f"INSUFFICIENT DATA ({floor})")
            )
            continue
        point = float(m.value(point_arrays))
        samples = [
            value
            for b in range(bootstrap)
            if not math.isnan(
                value := float(m.value((boot_confusion[b], boot_ece[b], boot_lid[b])))
            )
        ]
        boot = (float(np.percentile(samples, 2.5)), float(np.percentile(samples, 97.5)))
        exact = spec.clopper_pearson(x, n) if x is not None else None
        lower, upper = (
            (min(exact[0], boot[0]), max(exact[1], boot[1])) if exact else boot
        )
        rows.append(
            Row(
                m.gate,
                m.name,
                n,
                m.minimum_n,
                th,
                _verdict(lower, upper, m.threshold, m.direction),
                point,
                exact,
                boot,
                rows_note,
            )
        )
    return rows


def _percentile_ci(
    samples, q: float, bootstrap: int = DEFAULT_BOOTSTRAP, seed: int = 20260915
) -> tuple[float, float, float]:
    """Nearest-rank percentile and its 95% bootstrap interval, resampling requests."""
    import numpy as np

    data = np.asarray(samples, dtype=float)
    rng = np.random.default_rng(seed)
    resampled = rng.choice(data, size=(bootstrap, data.size), replace=True)
    estimates = np.percentile(resampled, q, axis=1, method="inverted_cdf")
    point = float(np.percentile(data, q, method="inverted_cdf"))
    return (
        point,
        float(np.percentile(estimates, 2.5)),
        float(np.percentile(estimates, 97.5)),
    )


def _hardware_problem(record: dict, target: dict | None) -> str | None:
    """Why a hardware measurement cannot decide its gate, or None if it can."""
    if target is None:
        return "no target hardware named, STATE.md H15"
    measured = str(record.get("machine", {}).get("cpu", "")).strip()
    wanted = str(target.get("cpu", "")).strip()
    if not wanted:
        return "target hardware file names no cpu, STATE.md H15"
    if measured != wanted:
        return (
            f"measured on {measured or 'an unrecorded machine'!r}, target is {wanted!r}"
        )
    return None


PREDICTED_POPULATION_GATE = "4"
SUFFICIENT = "SUFFICIENT"


def gold_only_items(gold_path: Path) -> tuple[list[Item], dict]:
    """The gold set with each item 'predicted' as its own label, only to count
    populations. No metric may be computed from these items."""
    placeholder: dict[str, dict[str, str]] = {}
    for row in _read_csv(gold_path):
        label = (row.get("gold_label") or "").strip()
        if label in CLASSES:
            probs = ["0", "0", "0"]
            probs[CLASSES.index(label)] = "1"
            placeholder[row["item_id"].strip()] = {
                "p_critical": probs[0],
                "p_urgent": probs[1],
                "p_routine": probs[2],
                "detected_language": row.get("language", ""),
            }
    return load_items(gold_path, placeholder)


def check_gold_rows(items: list[Item]) -> list[Row]:
    """Whether each gate cell CAN be measured on this gold set, before any inference.

    Counts only. CRITICAL precision's population is the model's own CRITICAL
    predictions, so it is reported as unknown rather than guessed.
    """
    import numpy as np

    confusion, ece_bins, lid = _cluster_arrays(items)
    point_arrays = (confusion.sum(axis=0), ece_bins.sum(axis=0), lid.sum(axis=0))
    clusters = (confusion, ece_bins, lid)
    one_item_per_scenario = bool(np.all(confusion.sum(axis=(1, 2, 3)) <= 1))
    rows: list[Row] = []
    for m in _metric_specs():
        th = _threshold_text(m.threshold, m.direction)
        if m.gate == PREDICTED_POPULATION_GATE:
            rows.append(
                Row(
                    m.gate,
                    m.name,
                    0,
                    m.minimum_n,
                    th,
                    "NOT KNOWN (population is the model's CRITICAL predictions; "
                    "known only after inference)",
                )
            )
            continue
        _, n_items, n = _population(m, point_arrays, clusters, one_item_per_scenario)
        if n < m.minimum_n:
            verdict = insufficient(n, m.minimum_n, n_items)
        else:
            floor = m.extra_floor(point_arrays) if m.extra_floor else None
            verdict = (
                f"INSUFFICIENT DATA ({floor})"
                if floor
                else f"{SUFFICIENT} ({n:,} distinct; need {m.minimum_n:,})"
            )
        rows.append(Row(m.gate, m.name, n, m.minimum_n, th, verdict))
    return rows


def render_check(rows: list[Row], items: list[Item]) -> str:
    distinct = len({i.scenario for i in items})
    lines = [
        f"Gold set: {len(items):,} rows from {distinct:,} distinct source sentences "
        "(scenario_id). Counts only; nothing is measured.",
        "",
        f"{'Gate':<12} {'Metric':<40} {'Threshold':<16} Can it be measured?",
    ]
    lines += [
        f"{r.gate:<12} {r.metric:<40} {r.threshold:<16} {r.verdict}" for r in rows
    ]
    measurable = sum(r.verdict.startswith(SUFFICIENT) for r in rows)
    lines.append("")
    lines.append(
        f"{measurable} of {len(rows)} gate cells can be measured."
        if measurable
        else "No gate cell can be measured on this gold set. Inference would produce "
        "only refusals."
    )
    return "\n".join(lines)


def measurement_rows(
    latency: Path | None, memory: Path | None, target_hardware: Path | None = None
) -> list[Row]:
    """Gates 14 and 15. Neither is MET off the named target machine (FR-04-05, D5).

    Latency needs per-request samples: p50 and p95 are printed with bootstrap
    intervals, and MET needs both upper bounds under their thresholds. Memory is one
    measurement at 50 concurrent (EVAL_SET_SPEC gate 15), labelled as such.
    """
    rows = []
    req14, req15 = spec.requirement("14"), spec.requirement("15")
    target = json.loads(target_hardware.read_text()) if target_hardware else None
    th14 = f"< {LATENCY_P50_MS:g} / < {LATENCY_P95_MS:g}"
    name14 = "inference latency p50 / p95 (ms)"
    if latency is None:
        rows.append(
            Row(
                "14",
                name14,
                0,
                req14.minimum_n,
                th14,
                "NOT MEASURED (no --latency file)",
            )
        )
    else:
        record = json.loads(latency.read_text())
        samples = record.get("samples_ms")
        if not samples:
            rows.append(
                Row(
                    "14",
                    name14,
                    0,
                    req14.minimum_n,
                    th14,
                    "NOT MEASURED (latency file has no per-request samples_ms; a "
                    "percentile without its interval is not reported)",
                )
            )
        elif len(samples) < req14.minimum_n:
            rows.append(
                Row(
                    "14",
                    name14,
                    len(samples),
                    req14.minimum_n,
                    th14,
                    insufficient(len(samples), req14.minimum_n),
                )
            )
        else:
            p50 = _percentile_ci(samples, 50)
            p95 = _percentile_ci(samples, 95)
            note = (
                f"p50 {p50[0]:.1f} ms [{p50[1]:.1f}, {p50[2]:.1f}]; "
                f"p95 {p95[0]:.1f} ms [{p95[1]:.1f}, {p95[2]:.1f}]; "
                f"machine {record.get('machine', {}).get('cpu', 'unrecorded')}"
            )
            verdicts = (
                _verdict(p50[1], p50[2], LATENCY_P50_MS, "below"),
                _verdict(p95[1], p95[2], LATENCY_P95_MS, "below"),
            )
            if VERDICT_NOT_MET in verdicts:
                verdict = VERDICT_NOT_MET
            elif all(v == VERDICT_MET for v in verdicts):
                verdict = VERDICT_MET
            else:
                verdict = VERDICT_UNDEMONSTRATED
            problem = _hardware_problem(record, target)
            if problem and verdict == VERDICT_MET:
                verdict = f"{VERDICT_UNDEMONSTRATED} ({problem})"
            elif problem:
                verdict = f"{verdict} ({problem})"
            rows.append(
                Row(
                    "14",
                    name14,
                    len(samples),
                    req14.minimum_n,
                    th14,
                    verdict,
                    note=note,
                )
            )

    th15 = f"< {MEMORY_LIMIT_MB:g}"
    name15 = "memory at 50 concurrent (MB)"
    if memory is None:
        rows.append(
            Row(
                "15",
                name15,
                0,
                req15.minimum_n,
                th15,
                "NOT MEASURED (no --memory file)",
            )
        )
    else:
        record = json.loads(memory.read_text())
        peak, conc = record.get("peak_rss_mb"), record.get("concurrency")
        if peak is None or conc != 50:
            rows.append(
                Row(
                    "15",
                    name15,
                    0,
                    req15.minimum_n,
                    th15,
                    "NOT MEASURED (memory file needs peak_rss_mb at concurrency 50)",
                )
            )
        else:
            verdict = VERDICT_MET if peak < MEMORY_LIMIT_MB else VERDICT_NOT_MET
            problem = _hardware_problem(record, target)
            if problem and verdict == VERDICT_MET:
                verdict = f"{VERDICT_UNDEMONSTRATED} ({problem})"
            elif problem:
                verdict = f"{verdict} ({problem})"
            rows.append(
                Row(
                    "15",
                    name15,
                    1,
                    req15.minimum_n,
                    th15,
                    verdict,
                    note=f"peak RSS {float(peak):.0f} MB, one measurement at 50 concurrent "
                    "(a measurement, not a sample: no interval applies)",
                )
            )
    return rows


RED_FLAG_GATE = "X-REDFLAG"
RED_FLAG_METRIC = "red-flag safety suite"


def red_flag_row(report: Path | None) -> Row:
    """CLAUDE.md L2 and §16: the escalate-only red-flag suite must pass every case.

    A fixed regression suite, not a sample, so it has a count and no interval.
    Whether the suite's cases are clinically adequate is not something this row can
    judge; that needs validated terms (STATE.md H10).
    """
    threshold = "100% of cases"
    if report is None:
        return Row(
            RED_FLAG_GATE,
            RED_FLAG_METRIC,
            0,
            1,
            threshold,
            "NOT MEASURED (no --red-flag-report)",
        )
    try:
        record = json.loads(report.read_text())
        cases, passed = int(record["cases"]), int(record["passed"])
        digest = str(record["suite_sha256"])
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise InputError(
            f"{report}: unreadable red-flag report ({error}); needs suite_sha256, cases, passed"
        ) from error
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise InputError(f"{report}: suite_sha256 must be a 64-character hex digest")
    if not 0 <= passed <= cases:
        raise InputError(
            f"{report}: passed={passed} is not between 0 and cases={cases}"
        )
    if cases == 0:
        return Row(
            RED_FLAG_GATE,
            RED_FLAG_METRIC,
            0,
            1,
            threshold,
            "NOT MEASURED (the suite has no cases; no validated terms, STATE.md H10)",
        )
    return Row(
        RED_FLAG_GATE,
        RED_FLAG_METRIC,
        cases,
        1,
        threshold,
        VERDICT_MET if passed == cases else VERDICT_NOT_MET,
        note=f"{passed} of {cases} cases passed; suite {digest[:12]}",
    )


# ── Reports ───────────────────────────────────────────────────────────────────
def _fmt(v: float | None) -> str:
    return "—" if v is None else f"{v:.4f}"


def render_text(
    rows: list[Row], excluded: dict, scored: int, scenarios: int | None = None
) -> str:
    lines = [f"Scored items: {scored}  (excluded: {excluded})"]
    if scenarios is not None and scenarios < scored:
        lines.append(
            f"WARNING: {scored} items in {scenarios} scenarios. EVAL_SET_SPEC §8 allows one "
            "test item per scenario; every n below counts scenarios, not items."
        )
    lines += [
        "",
        f"{'Gate':<12} {'Metric':<40} {'Threshold':<16} {'Point':>7}  {'95% CI exact':<17} {'95% CI bootstrap':<17} Verdict",
    ]
    for r in rows:
        if r.point is None and r.note is None:
            lines.append(
                f"{r.gate:<12} {r.metric:<40} {r.threshold:<16} {'':>7}  {'':<17} {'':<17} {r.verdict}"
            )
            continue
        exact = (
            "—" if r.ci_exact is None else f"[{r.ci_exact[0]:.3f}, {r.ci_exact[1]:.3f}]"
        )
        boot = (
            "—"
            if r.ci_bootstrap is None
            else f"[{r.ci_bootstrap[0]:.3f}, {r.ci_bootstrap[1]:.3f}]"
        )
        lines.append(
            f"{r.gate:<12} {r.metric:<40} {r.threshold:<16} {_fmt(r.point):>7}  {exact:<17} {boot:<17} {r.verdict}"
            + (f"  ({r.note})" if r.note else "")
        )
    met = sum(r.verdict == VERDICT_MET for r in rows)
    lines += [
        "",
        f"{met} of {len(rows)} gate rows MET. Deployment {'PERMITTED' if met == len(rows) else 'BLOCKED'}.",
    ]
    return "\n".join(lines)


def reliability_svg(items: list[Item]) -> str:
    """Reliability diagram: per-bin accuracy against mean confidence, with counts."""
    size, pad = 420, 48
    plot = size - 2 * pad
    bins = [[0, 0.0, 0.0] for _ in range(BINS)]
    for i in items:
        b = min(BINS - 1, max(0, math.ceil(i.confidence * BINS) - 1))
        bins[b][0] += 1
        bins[b][1] += i.confidence
        bins[b][2] += float(i.argmax == i.gold)

    def sx(v: float) -> float:
        return pad + v * plot

    def sy(v: float) -> float:
        return size - pad - v * plot

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}" font-family="sans-serif" font-size="11">',
        f'<rect width="{size}" height="{size}" fill="white"/>',
        f'<line x1="{sx(0)}" y1="{sy(0)}" x2="{sx(1)}" y2="{sy(1)}" stroke="#888" stroke-dasharray="4 3"/>',
        f'<line x1="{sx(0)}" y1="{sy(0)}" x2="{sx(1)}" y2="{sy(0)}" stroke="black"/>',
        f'<line x1="{sx(0)}" y1="{sy(0)}" x2="{sx(0)}" y2="{sy(1)}" stroke="black"/>',
        f'<text x="{size / 2}" y="{size - 12}" text-anchor="middle">mean confidence in bin</text>',
        f'<text x="14" y="{size / 2}" text-anchor="middle" transform="rotate(-90 14 {size / 2})">accuracy in bin</text>',
        f'<text x="{size / 2}" y="20" text-anchor="middle">Reliability ({len(items)} items, {BINS} bins; dashed = perfect)</text>',
    ]
    width = plot / BINS
    for b, (count, sum_conf, sum_correct) in enumerate(bins):
        if not count:
            continue
        acc = sum_correct / count
        x = pad + b * width
        parts.append(
            f'<rect class="bin" data-count="{count}" data-accuracy="{acc:.4f}" data-confidence="{sum_conf / count:.4f}" '
            f'x="{x + 1:.1f}" y="{sy(acc):.1f}" width="{width - 2:.1f}" height="{sy(0) - sy(acc):.1f}" fill="#3b6ea5"/>'
        )
        parts.append(
            f'<circle cx="{sx(sum_conf / count):.1f}" cy="{sy(acc):.1f}" r="2.5" fill="#b33"/>'
        )
    parts.append("</svg>")
    return "\n".join(parts)


def predict_with_model(
    model_dir: Path, gold_path: Path, max_length: int, batch_size: int
) -> dict[str, dict[str, str]]:
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tok_dir = model_dir / "tokenizer"
    tokenizer = AutoTokenizer.from_pretrained(
        str(tok_dir if tok_dir.exists() else model_dir)
    )
    model = AutoModelForSequenceClassification.from_pretrained(str(model_dir)).eval()
    id2label = model.config.id2label
    order = tuple(str(id2label[k]) for k in sorted(id2label))
    if order != CLASSES:
        raise InputError(
            f"model id2label {order} is not {CLASSES}; refusing to score a relabelled head"
        )
    rows = [r for r in _read_csv(gold_path) if r.get("split", "test").strip() == "test"]
    out: dict[str, dict[str, str]] = {}
    with torch.no_grad():
        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]
            enc = tokenizer(
                [r["text"] for r in batch],
                return_tensors="pt",
                truncation=True,
                max_length=max_length,
                padding=True,
            )
            probs = torch.softmax(model(**enc).logits.float(), dim=-1).tolist()
            for r, p in zip(batch, probs, strict=True):
                out[r["item_id"].strip()] = {
                    "item_id": r["item_id"],
                    "p_critical": str(p[0]),
                    "p_urgent": str(p[1]),
                    "p_routine": str(p[2]),
                }
    return out


@dataclass
class Report:
    rows: list[Row]
    excluded: dict
    scored: int
    inputs: dict = field(default_factory=dict)


def run_gate(args: argparse.Namespace) -> int:
    if args.check_gold or args.model is not None:
        try:
            gold_items, _ = gold_only_items(args.gold)
        except InputError as error:
            print(f"REFUSED: {error}", file=sys.stderr)
            return 2
        check = check_gold_rows(gold_items)
        measurable = any(r.verdict.startswith(SUFFICIENT) for r in check)
        if args.check_gold:
            print(render_check(check, gold_items))
            return 0 if measurable else 2
        if not measurable:
            print(render_check(check, gold_items))
            print(
                "REFUSED before inference: no gate cell can be measured on this gold "
                "set, so the model was not loaded. Run --check-gold to see the counts.",
                file=sys.stderr,
            )
            return 2
    if args.predictions is None and args.model is None:
        raise SystemExit("give --predictions or --model")
    try:
        predictions = (
            load_predictions(args.predictions)
            if args.predictions is not None
            else predict_with_model(
                args.model, args.gold, args.max_length, args.batch_size
            )
        )
        items, excluded = load_items(args.gold, predictions)
        red_flags = red_flag_row(args.red_flag_report)
    except InputError as error:
        print(f"REFUSED: {error}", file=sys.stderr)
        return 2
    rows = (
        evaluate(items, bootstrap=args.bootstrap, seed=args.seed)
        + measurement_rows(args.latency, args.memory, args.target_hardware)
        + [red_flags]
    )
    rows.sort(key=lambda r: (int(r.gate) if r.gate.isdigit() else 100, r.gate))
    text = render_text(rows, excluded, len(items), len({i.scenario for i in items}))
    print(text)
    if args.out:
        args.out.mkdir(parents=True, exist_ok=True)
        report = Report(
            rows,
            excluded,
            len(items),
            {
                "gold": str(args.gold),
                "predictions": str(args.predictions),
                "model": str(args.model),
                "bootstrap": args.bootstrap,
                "seed": args.seed,
            },
        )
        (args.out / "gate_report.json").write_text(json.dumps(asdict(report), indent=2))
        (args.out / "gate_report.txt").write_text(text + "\n")
        ece_row = next(r for r in rows if r.gate == "X-ECE")
        if ece_row.point is not None:
            (args.out / "reliability.svg").write_text(reliability_svg(items))
        else:
            (args.out / "reliability.NOT_DRAWN.txt").write_text(
                f"Not drawn: {ece_row.verdict}. A reliability diagram on too few items shows noise.\n"
            )
    return 0 if all(r.verdict == VERDICT_MET for r in rows) else 1


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if any(flag in argv for flag in ("--writeup", "--manifest")) or (
        "--model" in argv and "--gold" not in argv
    ):
        # These used to be forwarded to holdout_eval, which prints metrics on the
        # nine-sentence holdout with no minimum-n refusal. The gate never does.
        print(
            "REFUSED: training/evaluate.py is the deployment gate and needs --gold.\n"
            "--writeup, --manifest and --model without --gold belong to the historical "
            "holdout report, which is not a deployment gate. Run it explicitly:\n"
            "    python training/holdout_eval.py " + " ".join(argv),
            file=sys.stderr,
        )
        raise SystemExit(2)

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument(
        "--check-gold",
        action="store_true",
        help="count every gate population from the gold file alone, print which cells "
        "can be measured, and exit (0 if any can, 2 if none); runs no model",
    )
    parser.add_argument("--predictions", type=Path)
    parser.add_argument("--model", type=Path)
    parser.add_argument("--latency", type=Path, help="JSON from training/latency.py")
    parser.add_argument(
        "--memory", type=Path, help='JSON {"peak_rss_mb": float, "concurrency": 50}'
    )
    parser.add_argument(
        "--target-hardware",
        type=Path,
        help='JSON {"cpu": "..."} naming the deployment machine (STATE.md H15)',
    )
    parser.add_argument(
        "--red-flag-report",
        type=Path,
        help="JSON from the red-flag suite runner: suite_sha256, cases, passed",
    )
    parser.add_argument("--bootstrap", type=int, default=DEFAULT_BOOTSTRAP)
    parser.add_argument("--seed", type=int, default=20260914)
    parser.add_argument("--max-length", type=int, default=128)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--out", type=Path)
    return run_gate(parser.parse_args(argv))


if __name__ == "__main__":
    raise SystemExit(main())
