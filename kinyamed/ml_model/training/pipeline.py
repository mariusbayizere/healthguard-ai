#!/usr/bin/env python
"""The training pipeline, ready to run once the evaluation set exists.

    cd kinyamed/ml_model
    python -m training.pipeline --train <train.csv> \\
        --gold-test <gold_test.csv> --gold-calibration <gold_calibration.csv> \\
        --config training/configs/pipeline_default.json --seed 42 --out <run dir>

Each step gates the next, and nothing later runs when an earlier step refuses:

  1. EVAL SETS. The test split must make every gate cell that can be checked before
     inference SUFFICIENT under EVAL_SET_SPEC (gate 4's population is the model's own
     predictions and cannot be). The calibration split must meet its allocation in
     distinct scenarios. Otherwise REFUSE, before the training corpus is even read.
     On today's only held-out set (n=9 source sentences) this is where it stops.
  2. LEAKAGE (L8). Train, calibration and test must share no normalised text, no
     scenario_id, and no near-duplicate at word-3-gram Jaccard >= 0.85 (CLAUDE.md
     §3.6). Otherwise REFUSE before training.
  3. TRAIN with the cost-sensitive objective (training/cost_loss.py).
  4. CALIBRATE: one temperature, fitted on the calibration split only.
  5. THRESHOLDS tuned to CRITICAL safety on the calibration split only
     (training/thresholds.py).
  6. WRITE the model metadata the service reads (max_length, temperature,
     thresholds), test-split predictions carrying the thresholded decision for the
     gate, and the run manifest (training/run_manifest.py).

The pipeline prints no metric. `training/evaluate.py` scores the test predictions,
with scenario-clustered intervals, and is the only thing that reports.

Exit codes: 0 completed, 1 failed (recorded), 2 refused (recorded).
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import zlib
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import numpy as np

ML_ROOT = Path(__file__).resolve().parent.parent
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from dataset.atomicio import atomic_write, atomic_write_json  # noqa: E402
from dataset.labels import ID_TO_LABEL, LABEL_MAP  # noqa: E402
from training import calibration as cal  # noqa: E402
from training import eval_spec as spec  # noqa: E402
from training import thresholds as th  # noqa: E402
from training.cost_loss import DEFAULT_COST_MATRIX, validate_cost_matrix  # noqa: E402
from training.run_manifest import RunManifest, _git  # noqa: E402

TRAINING_METADATA = "kinyamed_training.json"  # read by the backend at start-up
MANIFEST_NAME = "run_manifest.json"
TEST_PREDICTIONS = "predictions_test.csv"
THRESHOLDS_NAME = "thresholds.json"
RELIABILITY_NAME = "reliability_calibration.svg"
NEAR_DUPLICATE_JACCARD = 0.85  # CLAUDE.md §3.6
SHINGLE_WORDS = 3
MINHASH_PERMUTATIONS = 64
MINHASH_BANDS = 16

# Engineering defaults, not clinical values. base_model, max_length, learning_rate,
# weight_decay, warmup_ratio, batch_size, epochs and threads are the v2d run's
# (training/run_records/last_run_v2d_freeze8_lr1e-5.json). The cost matrix is
# cost_loss's UNSOURCED default (STATE.md H6).
DEFAULT_CONFIG: dict[str, Any] = {
    "base_model": "Davlan/afro-xlmr-mini",
    "max_length": 96,
    "epochs": 1,
    "batch_size": 16,
    "learning_rate": 1e-5,
    "weight_decay": 0.01,
    "warmup_ratio": 0.06,
    "threads": 2,
    "cost_weight": 1.0,
    "cost_matrix": [list(row) for row in DEFAULT_COST_MATRIX],
    "predict_batch_size": 64,
}


class Trainer(Protocol):
    def train(
        self,
        train_rows: Sequence[Mapping[str, str]],
        config: Mapping[str, Any],
        seed: int,
        out_dir: Path,
    ) -> Path: ...


class Predictor(Protocol):
    def logits(
        self, model_dir: Path, texts: Sequence[str], max_length: int, batch_size: int
    ) -> np.ndarray: ...


# ── Inputs ────────────────────────────────────────────────────────────────────
def _read_rows(path: Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def validate_config(config: Mapping[str, Any]) -> list[str]:
    problems = []
    max_length = config.get("max_length")
    if (
        not isinstance(max_length, int)
        or isinstance(max_length, bool)
        or max_length <= 0
    ):
        problems.append("config: max_length must be a positive integer")
    if not isinstance(config.get("base_model"), str):
        problems.append("config: base_model must name a model")
    try:
        validate_cost_matrix(config.get("cost_matrix") or [])
    except (ValueError, TypeError) as error:
        problems.append(f"config: cost_matrix: {error}")
    if not float(config.get("cost_weight", -1)) >= 0:
        problems.append("config: cost_weight must be non-negative")
    return problems


# ── 1. Eval sets ──────────────────────────────────────────────────────────────
def check_test_split(path: Path) -> tuple[list[str], str]:
    """Reasons to refuse, and the gate's own count table to print."""
    from training import evaluate as gate

    if not Path(path).is_file():
        return [f"test split: {path} does not exist"], ""
    try:
        items, _ = gate.gold_only_items(Path(path))
    except gate.InputError as error:
        return [f"test split: {error}"], ""
    rows = gate.check_gold_rows(items)
    reasons = [
        f"test split, gate {r.gate} {r.metric}: {r.verdict}"
        for r in rows
        if r.gate != gate.PREDICTED_POPULATION_GATE
        and not r.verdict.startswith(gate.SUFFICIENT)
    ]
    return reasons, gate.render_check(rows, items)


@dataclass(frozen=True)
class Split:
    item_ids: list[str]
    texts: list[str]
    labels: list[int]
    languages: list[str]
    scenarios: list[str]


def load_calibration(path: Path) -> tuple[Split | None, list[str]]:
    if not Path(path).is_file():
        return None, [
            f"calibration split: {path} does not exist (EVAL_SET_SPEC: the temperature "
            "and thresholds are fitted on a calibration split, never on the test split)"
        ]
    rows = _read_rows(path)
    required = {"item_id", "text", "language", "gold_label", "scenario_id", "split"}
    if not rows or not required <= rows[0].keys():
        return None, [f"calibration split: {path} needs columns {sorted(required)}"]
    problems = []
    split = Split([], [], [], [], [])
    for row in rows:
        if row["split"].strip() != "calibration":
            problems.append(
                f"calibration split: item {row['item_id']} is marked {row['split']!r}"
            )
            continue
        label = row["gold_label"].strip()
        if label == spec.UNCLASSIFIABLE:
            continue
        if label not in spec.CLASSES or row["language"].strip() not in spec.LANGUAGES:
            problems.append(f"calibration split: item {row['item_id']} is unreadable")
            continue
        split.item_ids.append(row["item_id"].strip())
        split.texts.append(row["text"])
        split.labels.append(spec.CLASSES.index(label))
        split.languages.append(row["language"].strip())
        split.scenarios.append(row["scenario_id"].strip())
    if problems:
        return None, problems[:10]
    shortfalls = cal.calibration_split_shortfalls(
        split.labels, split.languages, split.scenarios
    )
    return split, [f"calibration split: {s}" for s in shortfalls]


# ── 2. Leakage ────────────────────────────────────────────────────────────────
def normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _shingles(text: str) -> frozenset[str]:
    words = normalise(text).split(" ")
    if len(words) < SHINGLE_WORDS:
        return frozenset({" ".join(words)})
    return frozenset(
        " ".join(words[i : i + SHINGLE_WORDS])
        for i in range(len(words) - SHINGLE_WORDS + 1)
    )


def _signature(shingles: frozenset[str], a: np.ndarray, b: np.ndarray) -> np.ndarray:
    prime = np.uint64((1 << 61) - 1)
    values = np.fromiter(
        (zlib.crc32(s.encode()) for s in shingles), dtype=np.uint64, count=len(shingles)
    )
    return ((np.outer(values, a) + b) % prime).min(axis=0)


@dataclass
class LeakageResult:
    exact: int = 0
    scenario: int = 0
    near_duplicate: int = 0
    by_pair: dict[str, dict[str, int]] = field(default_factory=dict)
    examples: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return self.exact == 0 and self.scenario == 0 and self.near_duplicate == 0

    def reasons(self) -> list[str]:
        out = []
        for pair, counts in self.by_pair.items():
            if counts["exact"]:
                out.append(
                    f"leakage: {counts['exact']} exact text overlap(s) between {pair}"
                )
            if counts["scenario"]:
                out.append(
                    f"leakage: {counts['scenario']} shared scenario_id(s) between {pair}"
                )
            if counts["near_duplicate"]:
                out.append(
                    f"leakage: {counts['near_duplicate']} near-duplicate(s) at Jaccard >= "
                    f"{NEAR_DUPLICATE_JACCARD} between {pair}"
                )
        return out

    def as_record(self) -> dict[str, Any]:
        return {
            "clean": self.clean,
            "exact": self.exact,
            "scenario": self.scenario,
            "near_duplicate": self.near_duplicate,
            "by_pair": self.by_pair,
            "jaccard_threshold": NEAR_DUPLICATE_JACCARD,
            "shingle_words": SHINGLE_WORDS,
        }


def _compare(
    reference: Sequence[tuple[str, str]], probe: Sequence[tuple[str, str]], seed: int
) -> tuple[dict[str, int], list[str]]:
    """How many `probe` items leak from `reference`: exact text, scenario, near-dup."""
    ref_texts = {normalise(t) for t, _ in reference}
    ref_scenarios = {s for _, s in reference if s}
    counts = {"exact": 0, "scenario": 0, "near_duplicate": 0}
    examples = []
    for text, scenario in probe:
        if normalise(text) in ref_texts:
            counts["exact"] += 1
            examples.append(f"exact: {normalise(text)[:60]!r}")
        if scenario and scenario in ref_scenarios:
            counts["scenario"] += 1
            examples.append(f"scenario: {scenario!r}")

    rng = np.random.default_rng(seed)
    a = rng.integers(1, (1 << 61) - 1, size=MINHASH_PERMUTATIONS, dtype=np.uint64)
    b = rng.integers(0, (1 << 61) - 1, size=MINHASH_PERMUTATIONS, dtype=np.uint64)
    per_band = MINHASH_PERMUTATIONS // MINHASH_BANDS
    unique_ref = sorted(ref_texts)
    ref_shingles = [_shingles(t) for t in unique_ref]
    buckets: list[dict[bytes, list[int]]] = [{} for _ in range(MINHASH_BANDS)]
    for index, shingles in enumerate(ref_shingles):
        signature = _signature(shingles, a, b)
        for band in range(MINHASH_BANDS):
            key = signature[band * per_band : (band + 1) * per_band].tobytes()
            buckets[band].setdefault(key, []).append(index)
    for text, _ in probe:
        norm = normalise(text)
        if norm in ref_texts:
            continue  # counted as exact
        shingles = _shingles(norm)
        signature = _signature(shingles, a, b)
        candidates: set[int] = set()
        for band in range(MINHASH_BANDS):
            key = signature[band * per_band : (band + 1) * per_band].tobytes()
            candidates.update(buckets[band].get(key, ()))
        for index in candidates:
            other = ref_shingles[index]
            if len(shingles & other) / len(shingles | other) >= NEAR_DUPLICATE_JACCARD:
                counts["near_duplicate"] += 1
                examples.append(f"near-duplicate: {norm[:60]!r}")
                break
    return counts, examples


def leakage_check(
    *,
    train: Sequence[tuple[str, str]],
    held_out: Mapping[str, Sequence[tuple[str, str]]],
    seed: int = 20260915,
) -> LeakageResult:
    """Exact, scenario and near-duplicate overlap for every pair of splits."""
    splits: dict[str, Sequence[tuple[str, str]]] = {"train": train, **held_out}
    names = list(splits)
    result = LeakageResult()
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            counts, examples = _compare(splits[left], splits[right], seed)
            result.by_pair[f"{left} and {right}"] = counts
            result.exact += counts["exact"]
            result.scenario += counts["scenario"]
            result.near_duplicate += counts["near_duplicate"]
            result.examples += examples[:5]
    return result


# ── 3. The real trainer and predictor ─────────────────────────────────────────
class TransformersTrainer:
    """Fine-tune a sequence classifier with the cost-sensitive loss. Seeded end to end:
    the same seed, data and config give the same weights on the same machine."""

    def train(
        self,
        train_rows: Sequence[Mapping[str, str]],
        config: Mapping[str, Any],
        seed: int,
        out_dir: Path,
    ) -> Path:
        import random

        import torch
        import transformers
        from training.cost_loss import CostSensitiveLoss

        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
        transformers.set_seed(seed)
        if config.get("threads"):
            torch.set_num_threads(int(config["threads"]))

        tokenizer = transformers.AutoTokenizer.from_pretrained(config["base_model"])
        model = transformers.AutoModelForSequenceClassification.from_pretrained(
            config["base_model"],
            num_labels=len(LABEL_MAP),
            id2label=ID_TO_LABEL,
            label2id=LABEL_MAP,
        )
        texts = [row["text"] for row in train_rows]
        labels = torch.tensor([LABEL_MAP[row["label"]] for row in train_rows])
        encoded = tokenizer(
            texts, truncation=True, max_length=int(config["max_length"]), padding=False
        )
        objective = CostSensitiveLoss(
            config["cost_matrix"], cost_weight=float(config["cost_weight"])
        )
        optimiser = torch.optim.AdamW(
            [p for p in model.parameters() if p.requires_grad],
            lr=float(config["learning_rate"]),
            weight_decay=float(config["weight_decay"]),
        )
        batch_size = int(config["batch_size"])
        steps = int(config["epochs"]) * -(-len(texts) // batch_size)
        schedule = transformers.get_linear_schedule_with_warmup(
            optimiser, int(float(config.get("warmup_ratio", 0.0)) * steps), steps
        )
        generator = torch.Generator().manual_seed(seed)
        model.train()
        for _ in range(int(config["epochs"])):
            order = torch.randperm(len(texts), generator=generator).tolist()
            for start in range(0, len(order), batch_size):
                batch = order[start : start + batch_size]
                inputs = tokenizer.pad(
                    {
                        "input_ids": [encoded["input_ids"][k] for k in batch],
                        "attention_mask": [encoded["attention_mask"][k] for k in batch],
                    },
                    return_tensors="pt",
                )
                optimiser.zero_grad()
                loss = objective(model(**inputs).logits, labels[batch])
                loss.backward()
                optimiser.step()
                schedule.step()
        out_dir.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(out_dir)
        tokenizer.save_pretrained(out_dir)
        return out_dir


class TransformersPredictor:
    def logits(
        self, model_dir: Path, texts: Sequence[str], max_length: int, batch_size: int
    ) -> np.ndarray:
        import torch
        import transformers

        tokenizer = transformers.AutoTokenizer.from_pretrained(model_dir)
        model = transformers.AutoModelForSequenceClassification.from_pretrained(
            model_dir
        )
        if model.config.id2label != ID_TO_LABEL:
            raise RuntimeError(
                f"model label order {model.config.id2label} is not {ID_TO_LABEL}"
            )
        model.eval()
        out = []
        with torch.no_grad():
            for start in range(0, len(texts), batch_size):
                inputs = tokenizer(
                    list(texts[start : start + batch_size]),
                    truncation=True,
                    max_length=max_length,
                    padding=True,
                    return_tensors="pt",
                )
                out.append(model(**inputs).logits.double().numpy())
        return np.vstack(out) if out else np.zeros((0, 3))


# ── The run ───────────────────────────────────────────────────────────────────
def _write_predictions(
    path: Path, item_ids: Iterable[str], probs: np.ndarray, decided: np.ndarray
) -> None:
    with atomic_write(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["item_id", "p_critical", "p_urgent", "p_routine", "predicted_label"]
        )
        for item_id, p, d in zip(item_ids, probs, decided, strict=True):
            writer.writerow(
                [
                    item_id,
                    repr(float(p[0])),
                    repr(float(p[1])),
                    repr(float(p[2])),
                    spec.CLASSES[int(d)],
                ]
            )


def _refuse(
    run: RunManifest, out: Path, reasons: Sequence[str], leakage_ran: bool
) -> int:
    for reason in reasons:
        print(f"REFUSED: {reason}", file=sys.stderr)
    if not leakage_ran:
        print(
            "leakage check: NOT RUN (refused before the training corpus was read)",
            file=sys.stderr,
        )
    print("Nothing was trained.", file=sys.stderr)
    run.refuse(reasons).write(out / MANIFEST_NAME)
    return 2


def run_pipeline(
    *,
    train_path: Path,
    gold_test: Path,
    gold_calibration: Path,
    config_path: Path,
    seed: int,
    out: Path,
    repo: Path,
    trainer: Trainer,
    predictor: Predictor,
) -> int:
    if out.exists() and any(out.iterdir()):
        print(
            f"REFUSED: {out} is not empty; a run never overwrites another",
            file=sys.stderr,
        )
        return 2
    out.mkdir(parents=True, exist_ok=True)
    config = json.loads(Path(config_path).read_text(encoding="utf-8"))
    inputs = {"config": Path(config_path)}
    inputs.update(
        {
            k: p
            for k, p in (
                ("gold_test", gold_test),
                ("gold_calibration", gold_calibration),
            )
            if Path(p).is_file()
        }
    )
    run = RunManifest.start(repo=repo, seed=seed, config=config, inputs=inputs)

    # 0-1. Config and eval sets, before the corpus is read.
    reasons = validate_config(config)
    test_reasons, table = check_test_split(gold_test)
    if table and test_reasons:
        print(table, file=sys.stderr)
    calibration, calibration_reasons = load_calibration(gold_calibration)
    reasons += test_reasons + calibration_reasons
    if reasons:
        return _refuse(run, out, reasons, leakage_ran=False)
    assert calibration is not None
    print("eval sets: the test split and calibration split meet EVAL_SET_SPEC")

    # 2. Leakage.
    if not Path(train_path).is_file():
        return _refuse(
            run,
            out,
            [f"training corpus {train_path} does not exist"],
            leakage_ran=False,
        )
    run.add_input("train", Path(train_path))
    train_rows = _read_rows(train_path)
    bad = [
        k
        for k, r in enumerate(train_rows)
        if r.get("label") not in LABEL_MAP or not r.get("text")
    ]
    if bad:
        return _refuse(
            run,
            out,
            [f"training corpus: {len(bad)} row(s) without a text or a valid label"],
            leakage_ran=False,
        )
    test_rows = [
        r for r in _read_rows(gold_test) if r.get("split", "test").strip() == "test"
    ]
    leakage = leakage_check(
        train=[(r["text"], (r.get("scenario_id") or "").strip()) for r in train_rows],
        held_out={
            "calibration": list(
                zip(calibration.texts, calibration.scenarios, strict=True)
            ),
            "test": [(r["text"], r["scenario_id"].strip()) for r in test_rows],
        },
    )
    if not leakage.clean:
        return _refuse(run, out, leakage.reasons(), leakage_ran=True)
    print(
        "leakage check: clean (exact text, scenario_id, near-duplicate across train, calibration, test)"
    )

    # 3. Train.
    max_length = int(config["max_length"])
    batch = int(config.get("predict_batch_size", 64))
    model_dir = out / "model"
    try:
        model_dir = trainer.train(train_rows, config, seed, model_dir)
        cal_logits = predictor.logits(model_dir, calibration.texts, max_length, batch)
        test_logits = predictor.logits(
            model_dir, [r["text"] for r in test_rows], max_length, batch
        )
    except Exception as error:  # noqa: BLE001 - any failure is recorded, then re-raised as exit 1
        print(f"FAILED: {type(error).__name__}: {error}", file=sys.stderr)
        run.fail(f"{type(error).__name__}: {error}").write(out / MANIFEST_NAME)
        return 1

    # 4. Calibrate on the calibration split only.
    cal_labels = np.asarray(calibration.labels)
    temperature = cal.fit_temperature(cal_logits, cal_labels)
    cal_probs = cal.softmax(cal_logits / temperature)
    print(
        f"temperature: {temperature:.4f}, fitted on {len(cal_labels):,} calibration rows"
    )

    # 5. Thresholds on the calibration split only.
    try:
        tuned = th.tune(
            cal_probs, cal_labels, calibration.languages, config["cost_matrix"]
        )
    except th.ThresholdsRefused as error:
        return _refuse(run, out, [str(error)], leakage_ran=True)
    print(
        f"thresholds: CRITICAL if p_C >= {tuned.critical:.2f}; URGENT if p_C + p_U >= {tuned.urgent:.2f}; else ROUTINE"
    )
    for warning in tuned.warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    # 6. Outputs.
    test_probs = cal.softmax(test_logits / temperature)
    predictions = out / TEST_PREDICTIONS
    _write_predictions(
        predictions,
        [r["item_id"] for r in test_rows],
        test_probs,
        th.decide(test_probs, tuned.critical, tuned.urgent),
    )
    thresholds_path = out / THRESHOLDS_NAME
    atomic_write_json(thresholds_path, tuned.as_record())
    reliability = out / RELIABILITY_NAME
    with atomic_write(reliability, "w", encoding="utf-8") as handle:
        handle.write(cal.reliability_svg(cal_probs, cal_labels))
    metadata_path = model_dir / TRAINING_METADATA
    atomic_write_json(
        metadata_path,
        {
            "max_length": max_length,
            "temperature": temperature,
            "thresholds": {
                "rule": tuned.as_record()["rule"],
                "critical": tuned.critical,
                "urgent": tuned.urgent,
            },
            "cost_matrix": [list(map(float, row)) for row in config["cost_matrix"]],
            "labels": list(spec.CLASSES),
            "base_model": config["base_model"],
            "seed": seed,
            "source": "training/pipeline.py",
        },
    )
    ece_before = cal.ece_with_interval(
        cal.softmax(cal_logits), cal_labels, calibration.scenarios
    )
    ece_after = cal.ece_with_interval(cal_probs, cal_labels, calibration.scenarios)
    run.finish(
        outputs={
            "training_metadata": metadata_path,
            "test_predictions": predictions,
            "thresholds": thresholds_path,
            "reliability_calibration": reliability,
        },
        results={
            "temperature": temperature,
            "thresholds": {"critical": tuned.critical, "urgent": tuned.urgent},
            "leakage": leakage.as_record(),
            "calibration_rows": len(cal_labels),
            "calibration_ece_in_sample": {
                "note": "in-sample: the split the temperature was fitted on. The gate's test-split ECE is the claim.",
                "before": vars(ece_before),
                "after": vars(ece_after),
            },
        },
    ).write(out / MANIFEST_NAME)
    print(f"run manifest: {out / MANIFEST_NAME}")
    print(
        "Nothing has been measured. Score the test split with the gate:\n"
        f"  python training/evaluate.py --gold {gold_test} --predictions {predictions}"
    )
    return 0


def _repo_root() -> Path:
    top = _git(ML_ROOT, "rev-parse", "--show-toplevel")
    return Path(top.strip()) if top else ML_ROOT


def main(
    argv: list[str] | None = None,
    *,
    trainer: Trainer | None = None,
    predictor: Predictor | None = None,
    repo: Path | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--gold-test", type=Path, required=True)
    parser.add_argument("--gold-calibration", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    return run_pipeline(
        train_path=args.train,
        gold_test=args.gold_test,
        gold_calibration=args.gold_calibration,
        config_path=args.config,
        seed=args.seed,
        out=args.out,
        repo=repo or _repo_root(),
        trainer=trainer or TransformersTrainer(),
        predictor=predictor or TransformersPredictor(),
    )


if __name__ == "__main__":
    raise SystemExit(main())
