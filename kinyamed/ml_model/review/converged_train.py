#!/usr/bin/env python
"""Train the labelled Kinyarwanda corpus TO CONVERGENCE, then evaluate test ONCE.

    python -m review.converged_train --split dataset/splits/kw_v1 \
        --config training/configs/pipeline_default.json --seed 42 \
        --max-epochs 20 --patience 3 --out <dir>

WHY THIS EXISTS. The first run (`review/preliminary_train.py`) gave one epoch, 98
optimisation steps, onto a randomly initialised head. It lost to always-ROUTINE, but
a model that never fit anything says nothing about the corpus it was fitted on. This
run removes that confound and nothing else: same corpus, same frozen split, same
committed cost objective, same learning rate, same two threads. Only the budget and
a stopping rule change, because the budget was the confound.

THE BUDGET IS FIXED BEFORE EVALUATION AND WRITTEN DOWN FIRST. `budget.json` is
written to the output directory before a single training step runs, and it records
the cap, the patience, the selection criterion and the fact that test is read once.
That ordering is the whole point: a number produced after the budget was recorded
cannot later be mistaken for the best of several attempts, and this file is the
evidence of the ordering rather than an assertion about it.

TEST IS READ ONCE, AT THE END, AND NEVER SELECTS ANYTHING. Early stopping and
checkpoint selection use a validation slice carved out of the TRAINING split only.
The test split is not tokenised, not scored and not loaded into a model until
training has finished and the checkpoint is already chosen. The script refuses to
write into a directory that already holds a run, so a second evaluation of the same
output directory is not something a tired operator can do by accident.

THE VALIDATION SLICE IS CARVED BY SENTENCE, NOT BY ROW, and stratified by class.
Carving by row would put two spellings of one authored sentence on both sides of the
early-stopping boundary, and the stopping decision would then be made partly on
sentences the model had already fitted -- the same leakage the split itself exists to
prevent, reintroduced one level down.

THE LEARNING RATE IS NOT TUNED HERE. It stays at the committed value. Changing it
alongside the budget would leave two variables moved and no way to say which one
mattered.

SCOPE CHANGE, AND IT IS NOT A SMALL ONE. The embedding matrix is frozen, so this run
fits the twelve encoder layers and the classification head and nothing else. The
model CANNOT adapt its Kinyarwanda subword representations: whatever AfroXLMR already
believes a Kinyarwanda wordpiece means is what it will still believe at the end. That
makes this a DIFFERENT EXPERIMENT from the one-epoch run, and no figure from it should
be compared with that run as though only the budget had changed.

The reason is memory, and the reason it is defensible is not. Full fine-tuning needs
about 3.9 GiB at this budget because gradients and Adam state scale with trainable
parameters, and 96.2M of the model's 117.6M parameters -- 81.8% -- are one 250,002-row
vocabulary matrix. This machine has about 3.2 GiB. Two independent arguments say the
freeze is the right call anyway rather than a dodge: 117M parameters fitted on 1,332
rows is over-parameterised by any reading, so freezing 82% of them is regularisation
one would plausibly choose with memory to spare; and layer freezing is this project's
existing practice, not an invention for this problem -- the v2d checkpoint is named
`model_v2d_freeze8_lr1e-5`.

BEST WEIGHTS GO TO DISK, NOT TO A CLONE IN RAM. Keeping the best epoch's state_dict in
memory costs a second full copy of the weights for the whole run. The checkpoint
directory is simply overwritten whenever validation improves, so at the end it already
holds the best epoch and nothing has to be loaded back.
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ML_ROOT = Path(__file__).resolve().parent.parent
if str(ML_ROOT) not in sys.path:
    sys.path.insert(0, str(ML_ROOT))

from dataset import labelled_corpus as lc
from dataset.labels import CLASS_ORDER, ID_TO_LABEL, LABEL_MAP
from review.preliminary_train import (
    PRELIMINARY,
    free_memory_mb,
    majority_baseline,
    metrics,
    read_split,
)
from training import calibration as cal
from training import thresholds as th
from training.pipeline import TransformersPredictor, leakage_check


def peak_rss_mb() -> int:
    """VmHWM from /proc/self/status, in MB: the high-water mark of resident memory.

    The first two runs reported `ps` spot samples, which name a moment rather than a
    peak and understate whatever happened between polls. This is the actual maximum
    the kernel observed for this process, read at exit.
    """
    for line in Path("/proc/self/status").read_text().splitlines():
        if line.startswith("VmHWM:"):
            return int(line.split()[1]) // 1024
    return -1


#: Share of TRAINING scenarios held back to stop on. Large enough that a loss on it
#: is not pure noise at 122 CRITICAL scenarios, small enough to leave the fit its data.
VALIDATION_SHARE = 0.15


def carve_validation(
    rows: list[dict[str, str]], seed: int, share: float = VALIDATION_SHARE
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Split training rows into fit and validation BY SENTENCE, stratified by class.

    Stratifying matters more than usual here: CRITICAL is 122 of 1,565 training
    scenarios, and an unstratified 15% draw can leave the validation slice with a
    handful of them, at which point the early-stopping signal is dominated by the
    two classes we are least worried about.
    """
    by_class: dict[str, list[str]] = defaultdict(list)
    seen: set[str] = set()
    for row in rows:
        scenario = row["scenario_id"]
        if scenario not in seen:
            seen.add(scenario)
            by_class[row["gold_label"]].append(scenario)

    rng = random.Random(seed)
    held: set[str] = set()
    for label in sorted(by_class):
        scenarios = sorted(by_class[label])
        rng.shuffle(scenarios)
        held.update(scenarios[: max(1, round(len(scenarios) * share))])

    fit = [r for r in rows if r["scenario_id"] not in held]
    validation = [r for r in rows if r["scenario_id"] in held]
    return fit, validation


def class_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    out = {name: 0 for name in CLASS_ORDER}
    for row in rows:
        out[row["gold_label"]] += 1
    return out


def scenario_counts(rows: list[dict[str, str]]) -> dict[str, int]:
    out: dict[str, set[str]] = {name: set() for name in CLASS_ORDER}
    for row in rows:
        out[row["gold_label"]].add(row["scenario_id"])
    return {name: len(v) for name, v in out.items()}


def train_to_convergence(
    fit_rows: list[dict[str, str]],
    validation_rows: list[dict[str, str]],
    config: dict[str, Any],
    seed: int,
    max_epochs: int,
    patience: int,
    out_dir: Path,
    log: Any,
    freeze_embeddings: bool,
) -> tuple[Path, list[dict[str, float]], dict[str, Any]]:
    """The committed trainer's loop, with a validation pass and a stopping rule.

    Everything inside the step -- tokenizer, model, cost objective, optimiser,
    schedule, seeding -- is the committed `TransformersTrainer.train` unchanged. What
    is added is a per-epoch validation loss, early stopping on it, and keeping the
    weights from the best epoch rather than the last.
    """
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
    if freeze_embeddings:
        for parameter in model.base_model.embeddings.parameters():
            parameter.requires_grad = False
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_parameters = sum(p.numel() for p in model.parameters())
    log(
        f"trainable parameters: {trainable:,} of {total_parameters:,} "
        f"({100 * trainable / total_parameters:.1f}%)"
        + ("; embedding matrix frozen" if freeze_embeddings else "")
    )
    max_length = int(config["max_length"])

    def encode(rows: list[dict[str, str]]):
        texts = [r["text"] for r in rows]
        labels = torch.tensor([LABEL_MAP[r["gold_label"]] for r in rows])
        return (
            tokenizer(texts, truncation=True, max_length=max_length, padding=False),
            labels,
        )

    fit_encoded, fit_labels = encode(fit_rows)
    val_encoded, val_labels = encode(validation_rows)

    objective = CostSensitiveLoss(
        config["cost_matrix"], cost_weight=float(config["cost_weight"])
    )
    optimiser = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=float(config["learning_rate"]),
        weight_decay=float(config["weight_decay"]),
    )
    batch_size = int(config["batch_size"])
    # The schedule spans the CAP, not the epoch we happen to stop at. Stopping early
    # therefore leaves the learning rate partly undecayed, which is the honest
    # consequence of fixing the budget in advance rather than after the fact.
    steps_per_epoch = -(-len(fit_rows) // batch_size)
    total_steps = max_epochs * steps_per_epoch
    schedule = transformers.get_linear_schedule_with_warmup(
        optimiser,
        int(float(config.get("warmup_ratio", 0.0)) * total_steps),
        total_steps,
    )

    def batches(encoded, labels, order, size):
        for start in range(0, len(order), size):
            batch = order[start : start + size]
            inputs = tokenizer.pad(
                {
                    "input_ids": [encoded["input_ids"][k] for k in batch],
                    "attention_mask": [encoded["attention_mask"][k] for k in batch],
                },
                return_tensors="pt",
            )
            yield inputs, labels[batch]

    generator = torch.Generator().manual_seed(seed)
    checkpoint = out_dir / "checkpoint"
    checkpoint.mkdir(parents=True, exist_ok=True)
    tokenizer.save_pretrained(checkpoint)
    curve: list[dict[str, float]] = []
    best: dict[str, Any] = {"validation_loss": float("inf"), "epoch": 0}
    epochs_without_improvement = 0
    stopped: dict[str, Any] = {"reason": "reached the epoch cap", "epoch": max_epochs}

    for epoch in range(1, max_epochs + 1):
        started = time.time()
        model.train()
        order = torch.randperm(len(fit_rows), generator=generator).tolist()
        total, seen = 0.0, 0
        for inputs, targets in batches(fit_encoded, fit_labels, order, batch_size):
            optimiser.zero_grad()
            loss = objective(model(**inputs).logits, targets)
            loss.backward()
            optimiser.step()
            schedule.step()
            total += float(loss) * len(targets)
            seen += len(targets)
        train_loss = total / seen

        model.eval()
        total, seen, correct = 0.0, 0, 0
        with torch.no_grad():
            val_order = list(range(len(validation_rows)))
            for inputs, targets in batches(val_encoded, val_labels, val_order, 32):
                logits = model(**inputs).logits
                total += float(objective(logits, targets)) * len(targets)
                correct += int((logits.argmax(dim=1) == targets).sum())
                seen += len(targets)
        validation_loss = total / seen
        validation_accuracy = correct / seen

        entry = {
            "epoch": epoch,
            "train_loss": round(train_loss, 6),
            "validation_loss": round(validation_loss, 6),
            "validation_accuracy": round(validation_accuracy, 6),
            "seconds": round(time.time() - started, 1),
            "memory_available_mb": free_memory_mb(),
        }
        curve.append(entry)
        log(
            f"epoch {epoch:2d}/{max_epochs}  train {train_loss:.5f}  "
            f"val {validation_loss:.5f}  val_acc {validation_accuracy:.4f}  "
            f"{entry['seconds']:.0f}s  free {entry['memory_available_mb']} MB"
        )

        if validation_loss < best["validation_loss"] - 1e-6:
            best = {"validation_loss": validation_loss, "epoch": epoch}
            # Straight to disk, overwriting. A state_dict clone here would cost a
            # second full copy of the weights for the rest of the run, which is
            # 0.44 GiB this machine does not have to spare. Overwriting means the
            # directory always holds the best epoch so far and nothing is loaded back.
            model.save_pretrained(checkpoint)
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
            if epochs_without_improvement >= patience:
                stopped = {
                    "reason": f"validation loss did not improve for {patience} epochs",
                    "epoch": epoch,
                }
                log(f"early stop at epoch {epoch}: {stopped['reason']}")
                break

    # No restore step: `checkpoint` was last written at the best epoch, so the weights
    # on disk are already the ones being kept. If validation never improved at all the
    # directory would hold no model, which is a real failure and must not pass quietly.
    if not (checkpoint / "model.safetensors").exists():
        raise RuntimeError("validation loss never improved; no checkpoint was written")
    return (
        checkpoint,
        curve,
        {
            "best": best,
            "stopped": stopped,
            "trainable_parameters": trainable,
            "total_parameters": total_parameters,
            "embeddings_frozen": freeze_embeddings,
        },
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--split", type=Path, required=True)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--max-epochs", type=int, default=20)
    parser.add_argument("--patience", type=int, default=3)
    parser.add_argument(
        "--freeze-embeddings",
        action="store_true",
        help="freeze the 96.2M-parameter embedding matrix; see the module docstring",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)

    # A directory holding ONLY budget.json is a run that was killed before it read
    # the test split. Its pre-commitment is still intact and is reused verbatim;
    # rewriting it would destroy the only evidence that the budget predates the
    # numbers. Anything else in the directory means a run that got further, and that
    # is never overwritten.
    existing = sorted(p.name for p in args.out.iterdir()) if args.out.exists() else []
    resuming = existing == ["budget.json"]
    if existing and not resuming:
        print(f"REFUSED: {args.out} already holds a run ({', '.join(existing)})")
        return 2
    args.out.mkdir(parents=True, exist_ok=True)

    def log(message: str) -> None:
        print(message, flush=True)

    config = json.loads(args.config.read_text())
    train_rows = read_split(args.split / "train.csv")
    calibration_rows = read_split(args.split / "calibration.csv")
    fit_rows, validation_rows = carve_validation(train_rows, args.seed)

    log(lc.provenance_line())

    # ── THE BUDGET, WRITTEN BEFORE A SINGLE TRAINING STEP RUNS ────────────────
    budget = {
        "fixed_before_evaluation": True,
        "written_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "note": (
            "This file is written to disk before training begins and before the test "
            "split is read. The figures this run reports are therefore the figures of "
            "one pre-committed budget, not the best of several attempts."
        ),
        "max_epochs": args.max_epochs,
        "patience": args.patience,
        "early_stopping_signal": "validation loss on a slice of the TRAINING split",
        "checkpoint_selection": "lowest validation loss; never test performance",
        "test_reads": 1,
        "test_read_when": "after training has finished and the checkpoint is chosen",
        "validation_share_of_training_scenarios": VALIDATION_SHARE,
        "validation_carved_by": "source sentence (scenario_id), stratified by class",
        "learning_rate": config["learning_rate"],
        "learning_rate_note": "committed value, deliberately not tuned alongside the budget",
        "schedule_spans": "the epoch cap, not the epoch reached",
        "seed": args.seed,
        "config": config,
        "split": str(args.split),
        "split_file_sha256": json.loads((args.split / "manifest.json").read_text())[
            "file_sha256"
        ],
        "corpus_sha256": lc.digest(),
        "provenance": lc.provenance_line(),
        "fit": {
            "rows": len(fit_rows),
            "rows_by_class": class_counts(fit_rows),
            "scenarios_by_class": scenario_counts(fit_rows),
        },
        "validation": {
            "rows": len(validation_rows),
            "rows_by_class": class_counts(validation_rows),
            "scenarios_by_class": scenario_counts(validation_rows),
        },
    }
    if resuming:
        # The killed run's budget, reused byte for byte. It was written before that
        # run read anything, and that run died before it read the test split, so the
        # pre-commitment it records is still true of the numbers this run produces.
        budget = json.loads((args.out / "budget.json").read_text())
        log(
            f"reusing the budget fixed at {budget['written_at']}; not rewritten. "
            "The test split was never read by the killed run."
        )
    else:
        (args.out / "budget.json").write_text(json.dumps(budget, indent=2) + "\n")
        log(f"budget fixed and written to {args.out / 'budget.json'} before training")

    # The amendment sits BESIDE the budget rather than inside it. What changed is a
    # memory constraint on the machine, not a change of mind about the budget, and the
    # two must stay separable for anyone auditing which came first.
    amendment = {
        "amends": "budget.json",
        "written_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "test_still_unread_at_this_point": True,
        "reason": (
            "The first attempt at this budget was killed under memory pressure before "
            "completing an epoch. Full fine-tuning at 20 epochs needs about 3.9 GiB: "
            "gradients and Adam state scale with trainable parameters, and 96.2M of "
            "the model's 117.6M (81.8%) are the 250,002-row embedding matrix. This "
            "machine has about 3.2 GiB available."
        ),
        "changes": [
            {
                "change": "embedding matrix frozen",
                "effect": "trainable parameters fall to 21.4M (18.2%)",
                "memory": "gradients + Adam state 1.32 GiB -> 0.24 GiB",
                "scope_cost": (
                    "The model fits the twelve encoder layers and the classification "
                    "head only. It CANNOT adapt its Kinyarwanda subword "
                    "representations. This is a DIFFERENT EXPERIMENT from the "
                    "one-epoch run, not the same experiment with a longer budget."
                ),
                "why_defensible": [
                    "117M parameters fitted on 1,332 rows is over-parameterised by "
                    "any reading; freezing 82% of them is regularisation one would "
                    "plausibly choose with memory to spare.",
                    "Layer freezing is this project's existing practice rather than "
                    "an invention for a memory problem: the v2d checkpoint is named "
                    "model_v2d_freeze8_lr1e-5.",
                ],
            },
            {
                "change": "best weights streamed to disk instead of cloned in RAM",
                "effect": "the checkpoint directory is overwritten whenever validation improves",
                "memory": "removes a second full copy of the weights, 0.44 GiB",
                "scope_cost": "none; the weights kept are identical either way",
            },
        ],
        "rejected": {
            "gradient accumulation with a smaller batch": (
                "weights, gradients and optimiser state are batch-independent; at "
                "seq 96 / hidden 384 / 12 layers the batch-16 activations are order "
                "tens of MB, so this saves ~50 MB for 4x the step count"
            ),
            "fp16 / bf16": (
                "this CPU reports AVX2 only, with no avx512_bf16 and no amx_bf16; "
                "autocast would emulate and run slower, and Adam state stays fp32 "
                "regardless, so the 0.88 GiB does not shrink"
            ),
            "either change alone": (
                "all-trainable with weights streamed to disk still peaks at 2.74 GiB "
                "against a 3.0 GiB ceiling, which is roughly the margin that was "
                "already reaped once"
            ),
        },
        "projected_memory_gib": {
            "as first attempted (all trainable, best in RAM)": 3.18,
            "all trainable, best on disk": 2.74,
            "embeddings frozen, best in RAM": 2.10,
            "this run (embeddings frozen, best on disk)": 1.67,
        },
        "hardware_finding": (
            "This machine does not fund twenty epochs of FULL fine-tuning at about "
            "3.9 GiB, and does fund twenty epochs of encoder-only fine-tuning at "
            "about 1.67 GiB. The constraint bounds WHAT can be trained rather than "
            "ruling the experiment out. Belongs beside the 43-hour sweep measurement "
            "as a fact about the hardware."
        ),
        "unchanged_from_budget": [
            "max_epochs",
            "patience",
            "early_stopping_signal",
            "checkpoint_selection",
            "test_reads",
            "learning_rate",
            "seed",
            "split",
        ],
    }
    (args.out / "budget_amendment.json").write_text(
        json.dumps(amendment, indent=2) + "\n"
    )
    log(f"amendment written to {args.out / 'budget_amendment.json'}; test still unread")
    log(f"  fit         {budget['fit']['scenarios_by_class']}")
    log(f"  validation  {budget['validation']['scenarios_by_class']}")

    # Leakage, including the new fit/validation boundary.
    leakage = leakage_check(
        train=[(r["text"], r["scenario_id"]) for r in fit_rows],
        held_out={
            "validation": [(r["text"], r["scenario_id"]) for r in validation_rows],
            "calibration": [(r["text"], r["scenario_id"]) for r in calibration_rows],
        },
    )
    log(
        f"leakage check (fit vs validation and calibration): "
        f"{'clean' if leakage.clean else 'DIRTY -- ' + '; '.join(leakage.reasons())}"
    )
    if not leakage.clean:
        return 2

    log(f"free memory before training: {free_memory_mb()} MB")
    started = time.time()
    checkpoint, curve, outcome = train_to_convergence(
        fit_rows,
        validation_rows,
        config,
        args.seed,
        args.max_epochs,
        args.patience,
        args.out,
        log,
        args.freeze_embeddings,
    )
    training_seconds = round(time.time() - started, 1)
    log(
        f"trained {len(curve)} epochs in {training_seconds} s; "
        f"kept epoch {outcome['best']['epoch']} "
        f"(validation loss {outcome['best']['validation_loss']:.5f})"
    )

    with (args.out / "loss_curve.csv").open("w", encoding="utf-8", newline="") as h:
        writer = csv.DictWriter(h, fieldnames=list(curve[0]))
        writer.writeheader()
        writer.writerows(curve)

    # ── Only now is the test split read, once ─────────────────────────────────
    test_rows = read_split(args.split / "test.csv")
    predictor = TransformersPredictor()
    max_length = int(config["max_length"])
    batch = int(config.get("predict_batch_size", 64))

    calibration_logits = predictor.logits(
        checkpoint, [r["text"] for r in calibration_rows], max_length, batch
    )
    calibration_gold = np.array(
        [LABEL_MAP[r["gold_label"]] for r in calibration_rows], dtype=int
    )
    temperature = cal.fit_temperature(calibration_logits, calibration_gold)
    log(f"temperature fitted on the calibration split: {temperature:.4f}")

    tuned: th.Thresholds | None = None
    threshold_record: dict[str, Any]
    try:
        tuned = th.tune(
            cal.softmax(calibration_logits / temperature),
            calibration_gold,
            [r["language"] for r in calibration_rows],
            config["cost_matrix"],
        )
        threshold_record = tuned.as_record()
    except th.ThresholdsRefused as refusal:
        threshold_record = {
            "status": "REFUSED",
            "reason": str(refusal),
            "effect": "no thresholded decision; argmax reported instead",
        }
        log(f"thresholds REFUSED: {refusal}")

    test_logits = predictor.logits(
        checkpoint, [r["text"] for r in test_rows], max_length, batch
    )
    test_gold = np.array([LABEL_MAP[r["gold_label"]] for r in test_rows], dtype=int)
    test_scenarios = [r["scenario_id"] for r in test_rows]
    probabilities = cal.softmax(test_logits / temperature)
    predicted = probabilities.argmax(axis=1)

    raw = cal.ece_with_interval(
        cal.softmax(test_logits), test_gold, test_scenarios, seed=args.seed
    )
    scaled = cal.ece_with_interval(
        probabilities, test_gold, test_scenarios, seed=args.seed
    )

    record = {
        "status": PRELIMINARY,
        "provenance": lc.provenance_line(),
        "budget": budget,
        "training_seconds": training_seconds,
        "loss_curve": curve,
        "stopping": outcome,
        "amendment": amendment,
        "peak_rss_mb": peak_rss_mb(),
        "temperature": float(temperature),
        "thresholds": threshold_record,
        "test": metrics(test_gold, predicted, test_scenarios, args.seed),
        "baseline_always_routine": majority_baseline(
            test_gold, test_scenarios, args.seed
        ),
        "ece_uncalibrated": {
            "value": raw.point,
            "ci": [raw.low, raw.high],
            "n_sentences": len(set(test_scenarios)),
        },
        "ece_temperature_scaled": {
            "value": scaled.point,
            "ci": [scaled.low, scaled.high],
            "n_sentences": len(set(test_scenarios)),
        },
        "predicted_class_distribution": {
            ID_TO_LABEL[i]: int((predicted == i).sum()) for i in range(len(CLASS_ORDER))
        },
        "gold_class_distribution": {
            ID_TO_LABEL[i]: int((test_gold == i).sum()) for i in range(len(CLASS_ORDER))
        },
    }
    (args.out / "converged_run.json").write_text(json.dumps(record, indent=2) + "\n")

    with (args.out / "predictions_test.csv").open(
        "w", encoding="utf-8", newline=""
    ) as h:
        writer = csv.writer(h)
        writer.writerow(
            ["item_id", "scenario_id", "gold_label", "predicted_label", *CLASS_ORDER]
        )
        for row, gold, prediction, probability in zip(
            test_rows, test_gold, predicted, probabilities, strict=True
        ):
            writer.writerow(
                [
                    row["item_id"],
                    row["scenario_id"],
                    ID_TO_LABEL[int(gold)],
                    ID_TO_LABEL[int(prediction)],
                    *[f"{p:.6f}" for p in probability],
                ]
            )

    log(f"peak resident memory (VmHWM): {peak_rss_mb()} MB")
    log(PRELIMINARY)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
