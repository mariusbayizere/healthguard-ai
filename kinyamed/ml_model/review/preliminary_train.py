#!/usr/bin/env python
"""A PRELIMINARY training run on the labelled Kinyarwanda corpus. NOT A GATE RUN.

    python -m review.preliminary_train --split dataset/splits/kw_v1 \
        --config training/configs/pipeline_default.json --seed 42 --out <dir>

WHY THIS EXISTS AND WHAT IT IS NOT. `training/pipeline.py` is the gate pipeline and
it REFUSES on this split, correctly: the test split funds no gate cell (gate 5 needs
365 gold CRITICAL per language and the whole corpus holds 174). That refusal is the
truth about deployment and nothing here overrides it. This script exists to answer a
narrower question the refusal leaves open -- does a model trained on these labels
learn anything at all, or does it collapse to the majority class -- and every number
it prints is PRELIMINARY, is not a gate verdict, and must never be reported as one.

It imports the committed trainer, calibrator and threshold tuner and does not modify
them. What it does not do is score against thresholds: `evaluate.py` owns that, and
it would refuse.

EVERY FIGURE CARRIES THREE THINGS: the provenance line (one non-clinician annotator,
no second rater, no agreement statistic, not clinical ground truth), its
distinct-sentence count, and a cluster bootstrap that resamples the SENTENCE rather
than the row. Resampling rows would treat two spellings of one authored sentence as
two independent observations and narrow every interval that matters.

THE BASELINE IS PART OF THE RESULT. Always-ROUTINE is reported beside the model. A
model that cannot beat it has told you something worth knowing.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np

ML_ROOT = Path(__file__).resolve().parent.parent
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from dataset import labelled_corpus as lc
from dataset.labels import CLASS_ORDER, ID_TO_LABEL, LABEL_MAP
from training import calibration as cal
from training import thresholds as th
from training.pipeline import (
    TransformersPredictor,
    TransformersTrainer,
    leakage_check,
)

BOOTSTRAP_RESAMPLES = 2000
PRELIMINARY = "PRELIMINARY -- not a gate verdict; see the pipeline refusal."


def read_split(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return [dict(r) for r in csv.DictReader(handle)]


def free_memory_mb() -> int:
    """Available kB from /proc/meminfo, in MB. `free -h`'s 'available' column."""
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) // 1024
    return -1


def cluster_bootstrap(
    scenarios: list[str],
    correct: np.ndarray,
    mask: np.ndarray,
    seed: int,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> tuple[float, float, float]:
    """Point estimate and 95% interval for a proportion, resampling the SENTENCE.

    `mask` selects the population (all items, or the gold CRITICAL items, ...).
    Clusters are drawn with replacement; a resample in which the population is
    empty contributes nothing rather than a zero, which would bias the interval
    downward.
    """
    unique = sorted(set(scenarios))
    index: dict[str, list[int]] = {s: [] for s in unique}
    for i, s in enumerate(scenarios):
        index[s].append(i)
    denominator = int(mask.sum())
    point = float(correct[mask].mean()) if denominator else float("nan")
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(resamples):
        picked = rng.integers(0, len(unique), size=len(unique))
        rows = [i for k in picked for i in index[unique[k]]]
        sub_mask = mask[rows]
        if not sub_mask.any():
            continue
        draws.append(float(correct[rows][sub_mask].mean()))
    if not draws:
        return point, float("nan"), float("nan")
    return point, float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def _f1(gold: np.ndarray, predicted: np.ndarray, index: int) -> float:
    """F1 for one class. Undefined when the class is neither present nor predicted."""
    true_positive = float(((gold == index) & (predicted == index)).sum())
    predicted_positive = float((predicted == index).sum())
    actual_positive = float((gold == index).sum())
    if predicted_positive == 0 or actual_positive == 0:
        return float("nan")
    precision = true_positive / predicted_positive
    recall = true_positive / actual_positive
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def f1_bootstrap(
    scenarios: list[str],
    gold: np.ndarray,
    predicted: np.ndarray,
    index: int,
    seed: int,
    resamples: int = BOOTSTRAP_RESAMPLES,
) -> tuple[float, float, float]:
    """F1 and a 95% interval, resampling the SENTENCE rather than the row.

    F1 is not a proportion over a fixed population, so it cannot reuse
    `cluster_bootstrap`: precision and recall move together under a resample and
    the interval has to be built from the recomputed statistic. Resamples in
    which the class is absent from both gold and prediction contribute nothing
    rather than a zero, which would drag the lower bound down for a class that is
    simply rare.
    """
    unique = sorted(set(scenarios))
    grouped: dict[str, list[int]] = {s: [] for s in unique}
    for i, s in enumerate(scenarios):
        grouped[s].append(i)
    point = _f1(gold, predicted, index)
    rng = np.random.default_rng(seed)
    draws = []
    for _ in range(resamples):
        picked = rng.integers(0, len(unique), size=len(unique))
        rows = [i for k in picked for i in grouped[unique[k]]]
        value = _f1(gold[rows], predicted[rows], index)
        if not np.isnan(value):
            draws.append(value)
    if not draws:
        return point, float("nan"), float("nan")
    return point, float(np.percentile(draws, 2.5)), float(np.percentile(draws, 97.5))


def metrics(
    gold: np.ndarray, predicted: np.ndarray, scenarios: list[str], seed: int
) -> dict[str, Any]:
    """Accuracy, per-class recall and the CRITICAL -> ROUTINE rate, each with an interval."""
    out: dict[str, Any] = {}
    everything = np.ones(len(gold), dtype=bool)
    point, low, high = cluster_bootstrap(scenarios, gold == predicted, everything, seed)
    out["accuracy"] = {
        "n_sentences": len(set(scenarios)),
        "value": point,
        "ci": [low, high],
    }
    for name, index in LABEL_MAP.items():
        mask = gold == index
        point, low, high = cluster_bootstrap(scenarios, predicted == gold, mask, seed)
        out[f"recall_{name}"] = {
            "n_sentences": len({s for s, m in zip(scenarios, mask, strict=True) if m}),
            "value": point,
            "ci": [low, high],
        }
        predicted_mask = predicted == index
        point, low, high = cluster_bootstrap(
            scenarios, predicted == gold, predicted_mask, seed
        )
        out[f"precision_{name}"] = {
            "n_sentences": len(
                {s for s, m in zip(scenarios, predicted_mask, strict=True) if m}
            ),
            "value": point,
            "ci": [low, high],
        }
        point, low, high = f1_bootstrap(scenarios, gold, predicted, index, seed)
        out[f"f1_{name}"] = {
            "n_sentences": len({s for s, m in zip(scenarios, mask, strict=True) if m}),
            "value": point,
            "ci": [low, high],
        }
    critical = gold == LABEL_MAP["CRITICAL"]
    to_routine = (predicted == LABEL_MAP["ROUTINE"]).astype(float)
    point, low, high = cluster_bootstrap(scenarios, to_routine, critical, seed)
    out["critical_to_routine_rate"] = {
        "n_sentences": len({s for s, m in zip(scenarios, critical, strict=True) if m}),
        "value": point,
        "ci": [low, high],
    }
    matrix = [[0] * len(CLASS_ORDER) for _ in CLASS_ORDER]
    for g, p in zip(gold.tolist(), predicted.tolist(), strict=True):
        matrix[g][p] += 1
    out["confusion_gold_by_predicted"] = {
        "order": list(CLASS_ORDER),
        "matrix": matrix,
    }
    return out


def majority_baseline(
    gold: np.ndarray, scenarios: list[str], seed: int
) -> dict[str, Any]:
    """Always-ROUTINE, scored exactly as the model is."""
    predicted = np.full_like(gold, LABEL_MAP["ROUTINE"])
    return metrics(gold, predicted, scenarios, seed)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.out.exists() and any(args.out.iterdir()):
        print(f"REFUSED: {args.out} is not empty; a run never overwrites another")
        return 2
    args.out.mkdir(parents=True, exist_ok=True)

    config = json.loads(args.config.read_text())
    train_rows = read_split(args.split / "train.csv")
    calibration_rows = read_split(args.split / "calibration.csv")
    test_rows = read_split(args.split / "test.csv")

    record: dict[str, Any] = {
        "status": PRELIMINARY,
        "provenance": lc.provenance_line(),
        "corpus_sha256": lc.digest(),
        "split": str(args.split),
        "split_manifest_sha256": json.loads((args.split / "manifest.json").read_text())[
            "file_sha256"
        ],
        "config": config,
        # "Class weighting" in this pipeline is the cost matrix, not a per-class
        # frequency weight: cross-entropy is unweighted and the second loss term is
        # the expected misclassification cost under the model's own softmax
        # (training/cost_loss.py). Recorded explicitly so the report names the
        # mechanism that ran rather than one it might have had.
        "weighting": {
            "mechanism": "cost matrix via training/cost_loss.py; cross-entropy unweighted",
            "cost_matrix": config["cost_matrix"],
            "cost_weight": config["cost_weight"],
            "class_frequency_weights": None,
        },
        "seed": args.seed,
        "memory_available_mb": {"before_training": free_memory_mb()},
    }
    print(lc.provenance_line())
    print(
        f"free memory before training: {record['memory_available_mb']['before_training']} MB"
    )

    # L8: the leakage check the pipeline never reached, run on the same comparison.
    leakage = leakage_check(
        train=[(r["text"], r["scenario_id"]) for r in train_rows],
        held_out={
            "calibration": [(r["text"], r["scenario_id"]) for r in calibration_rows],
            "test": [(r["text"], r["scenario_id"]) for r in test_rows],
        },
    )
    record["leakage"] = leakage.as_record()
    print(
        f"leakage check: {'clean' if leakage.clean else 'DIRTY -- ' + '; '.join(leakage.reasons())}"
    )
    if not leakage.clean:
        (args.out / "preliminary_run.json").write_text(
            json.dumps(record, indent=2) + "\n"
        )
        return 2

    trainer_rows = [{"text": r["text"], "label": r["gold_label"]} for r in train_rows]
    started = time.time()
    model_dir = TransformersTrainer().train(
        trainer_rows, config, args.seed, args.out / "checkpoint"
    )
    record["training_seconds"] = round(time.time() - started, 1)
    record["memory_available_mb"]["after_training"] = free_memory_mb()
    print(
        f"trained in {record['training_seconds']} s; free memory now "
        f"{record['memory_available_mb']['after_training']} MB"
    )

    predictor = TransformersPredictor()
    max_length = int(config["max_length"])
    batch = int(config.get("predict_batch_size", 64))

    calibration_logits = predictor.logits(
        model_dir, [r["text"] for r in calibration_rows], max_length, batch
    )
    calibration_gold = np.array(
        [LABEL_MAP[r["gold_label"]] for r in calibration_rows], dtype=int
    )
    temperature = cal.fit_temperature(calibration_logits, calibration_gold)
    record["temperature"] = float(temperature)
    print(f"temperature fitted on the calibration split: {temperature:.4f}")

    # Thresholds tuned to CRITICAL safety on the CALIBRATION split only, with the
    # committed tuner and the committed cost matrix. Its two hard constraints are
    # gate 5's and gate 7's targets, and it is being asked to satisfy them from 17
    # CRITICAL sentences -- three hundred and forty-eight short of what gate 5
    # needs to be a claim. Whatever it returns is a point estimate used to pick two
    # numbers, and the pipeline's refusal still stands over it.
    calibration_probabilities = cal.softmax(calibration_logits / temperature)
    tuned: th.Thresholds | None = None
    try:
        tuned = th.tune(
            calibration_probabilities,
            calibration_gold,
            [r["language"] for r in calibration_rows],
            config["cost_matrix"],
        )
    except th.ThresholdsRefused as refusal:
        # THE TUNER'S OWN REFUSAL, recorded and not worked around. Gate 5 is a
        # per-pure-language constraint and this arm is Kinyarwanda only, so three
        # of the four languages have no CRITICAL rows to constrain it with.
        # Relaxing the constraint to the languages that happen to be present would
        # be re-slicing a requirement to fit the corpus, which is the one move this
        # whole exercise exists to refuse. Argmax is reported instead, and the
        # report says plainly that no thresholds were tuned.
        record["thresholds"] = {
            "status": "REFUSED",
            "reason": str(refusal),
            "effect": "no thresholded decision; argmax reported instead",
        }
        print(f"thresholds REFUSED: {refusal}")

    if tuned is not None:
        record["thresholds"] = tuned.as_record()
        record["thresholds"]["tuned_on_n_sentences"] = len(
            {r["scenario_id"] for r in calibration_rows}
        )
        record["thresholds"]["tuned_on_n_critical_sentences"] = len(
            {
                r["scenario_id"]
                for r in calibration_rows
                if r["gold_label"] == "CRITICAL"
            }
        )
        print(
            f"thresholds tuned on the calibration split: t_critical={tuned.critical:.3f} "
            f"t_urgent={tuned.urgent:.3f}"
        )
        for warning in tuned.warnings:
            print(f"  threshold warning: {warning}")

    test_logits = predictor.logits(
        model_dir, [r["text"] for r in test_rows], max_length, batch
    )
    test_gold = np.array([LABEL_MAP[r["gold_label"]] for r in test_rows], dtype=int)
    test_scenarios = [r["scenario_id"] for r in test_rows]
    probabilities = cal.softmax(test_logits / temperature)
    predicted = probabilities.argmax(axis=1)

    decided = (
        th.decide(probabilities, tuned.critical, tuned.urgent)
        if tuned is not None
        else None
    )

    record["test"] = metrics(test_gold, predicted, test_scenarios, args.seed)
    # The thresholded decision is what the service would actually serve; argmax is
    # kept beside it because the gap between them is the price the safety rule is
    # charging, and that price is a result in its own right.
    record["test_thresholded"] = (
        metrics(test_gold, decided, test_scenarios, args.seed)
        if decided is not None
        else None
    )
    record["baseline_always_routine"] = majority_baseline(
        test_gold, test_scenarios, args.seed
    )
    record["predicted_class_distribution"] = {
        ID_TO_LABEL[i]: int(n) for i, n in sorted(Counter(predicted.tolist()).items())
    }
    record["thresholded_class_distribution"] = (
        {ID_TO_LABEL[i]: int(n) for i, n in sorted(Counter(decided.tolist()).items())}
        if decided is not None
        else None
    )
    record["gold_class_distribution"] = {
        ID_TO_LABEL[i]: int(n) for i, n in sorted(Counter(test_gold.tolist()).items())
    }
    # ECE on the TEST split, scenario-clustered. EVAL_SET_SPEC needs n=2,000 for
    # this to be a claim and the split has 447, so it is reported as an
    # observation with its interval, never as the X-ECE gate.
    raw = cal.ece_with_interval(
        cal.softmax(test_logits), test_gold, test_scenarios, seed=args.seed
    )
    scaled_ece = cal.ece_with_interval(
        probabilities, test_gold, test_scenarios, seed=args.seed
    )
    record["ece_uncalibrated"] = {
        "value": raw.point,
        "ci": [raw.low, raw.high],
        "n_sentences": len(set(test_scenarios)),
    }
    record["ece_temperature_scaled"] = {
        "value": scaled_ece.point,
        "ci": [scaled_ece.low, scaled_ece.high],
        "n_sentences": len(set(test_scenarios)),
    }

    with (args.out / "predictions_test.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "item_id",
                "scenario_id",
                "gold_label",
                "predicted_label",
                "thresholded_label",
                *CLASS_ORDER,
            ]
        )
        served = decided if decided is not None else predicted
        for row, gold, prediction, decision, probability in zip(
            test_rows, test_gold, predicted, served, probabilities, strict=True
        ):
            writer.writerow(
                [
                    row["item_id"],
                    row["scenario_id"],
                    ID_TO_LABEL[int(gold)],
                    ID_TO_LABEL[int(prediction)],
                    ID_TO_LABEL[int(decision)] if decided is not None else "REFUSED",
                    *[f"{p:.6f}" for p in probability],
                ]
            )

    (args.out / "preliminary_run.json").write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(record["test"], indent=2, sort_keys=True))
    print(f"\n{PRELIMINARY}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
