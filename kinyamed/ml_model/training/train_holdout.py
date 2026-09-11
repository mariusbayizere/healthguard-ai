#!/usr/bin/env python
"""Train the triage classifier on a leakage-controlled split.

Reads the split named by a frozen eval manifest and verifies its digests before
training, so a benchmark number can always be traced to exactly the rows that
produced it.

Loss is class-weighted by inverse frequency: under-triage is the dangerous
error in this system, so the rarer CRITICAL class must not be traded away for
overall accuracy.

Smoke run:
    python training/train_holdout.py --train-fraction 0.01 --max-steps 300 --no-save
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import classification_report, confusion_matrix
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset, Subset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    get_linear_schedule_with_warmup,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dataset.atomicio import atomic_write, sweep_partials
from training.config import ID_TO_LABEL, LABEL_MAP, MODEL_NAME, NUM_LABELS

# The gate lives in ONE place. This module used to carry its own
# `MINIMUM_CRITICAL_RECALL = 0.95` beside evaluate.py's, so a change to the
# safety threshold in one file would silently not apply in the other — the
# same two-sources-of-truth shape that cost this project a day on PR06 and on
# the concept relation rulings. Imported now, never redefined.
from training.evaluate import (  # noqa: F401
    CLASS_ORDER,
    MINIMUM_CRITICAL_RECALL,
    triage_gate,
)


class SymptomDataset(Dataset):
    """Tokenised symptom texts with integer labels."""

    def __init__(self, frame: pd.DataFrame, tokenizer, max_length: int) -> None:
        self.texts = frame["text"].tolist()
        self.labels = frame["label_id"].tolist()
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self) -> int:
        return len(self.texts)

    def __getitem__(self, index: int) -> dict:
        # No padding here: the collator pads each batch to its own longest
        # sequence. Token lengths run 18-63 with a median of 43, so padding
        # every row to 64 spends about a third of the compute on padding.
        encoded = self.tokenizer(
            self.texts[index],
            max_length=self.max_length,
            truncation=True,
        )
        return {
            "input_ids": encoded["input_ids"],
            "attention_mask": encoded["attention_mask"],
            "labels": self.labels[index],
        }


def make_collator(tokenizer):
    """Pad each batch to its longest member rather than to max_length."""

    def collate(batch: list[dict]) -> dict[str, torch.Tensor]:
        labels = torch.tensor([item.pop("labels") for item in batch], dtype=torch.long)
        padded = tokenizer.pad(batch, return_tensors="pt")
        padded["labels"] = labels
        return padded

    return collate


def run_fingerprint(manifest: dict, args) -> str:
    """Identity of this run's configuration.

    A checkpoint is only resumable into an identical run. Resuming a different
    learning rate or a different split into a half-trained optimiser would
    produce a model no manifest describes, so the fingerprint covers the data
    digests and every hyperparameter that changes the trajectory.
    """
    parts = [
        manifest["files"]["train"]["sha256"],
        manifest["files"]["eval"]["sha256"],
        MODEL_NAME,
        f"{args.seed}:{args.epochs}:{args.max_steps}:{args.batch_size}",
        f"{args.max_length}:{args.learning_rate}:{args.weight_decay}",
        f"{args.warmup_ratio}:{args.train_fraction}:{args.eval_limit}",
        f"freeze_embeddings={args.freeze_embeddings}",
        # Everything below changes WHICH step's weights are kept, so a
        # checkpoint written under one of these must not be resumed under
        # another. Adding them invalidates every checkpoint from before this
        # change, which is correct: those runs had no stopping rule at all.
        f"freeze_layers={args.freeze_layers}",
        f"stop_groups={args.stop_groups}",
        f"patience={args.patience}:{args.min_delta}",
    ]
    return hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()


def save_checkpoint(path: Path, payload: dict) -> None:
    """Write a training checkpoint that a kill cannot truncate.

    torch.save streams a large archive; interrupted halfway it leaves a file
    that torch.load rejects only after the run has already been lost. Writing
    to a temp file and renaming means the previous checkpoint stays loadable
    until the new one is complete on disk.
    """
    sweep_partials(path)
    with atomic_write(path, "wb") as handle:
        torch.save(payload, handle)


def load_checkpoint(path: Path, fingerprint: str) -> dict | None:
    """Return a resumable checkpoint, or None with the reason printed."""
    if not path.exists():
        return None
    try:
        payload = torch.load(path, map_location="cpu", weights_only=False)
    except Exception as error:  # noqa: BLE001 — a torn or stale checkpoint must not be fatal
        print(
            f"  checkpoint at {path} is unreadable ({type(error).__name__}); starting fresh"
        )
        return None
    if payload.get("fingerprint") != fingerprint:
        print(
            f"  checkpoint at {path} belongs to a different configuration; starting fresh"
        )
        return None
    return payload


def epoch_order(count: int, seed: int, epoch: int) -> list[int]:
    """The shuffled example order for one epoch, reproducible from the seed.

    Resume needs the same permutation the interrupted run used, so the order is
    derived from (seed, epoch) rather than from global RNG state that has since
    moved on.
    """
    generator = torch.Generator()
    generator.manual_seed(seed * 100_003 + epoch)
    return torch.randperm(count, generator=generator).tolist()


def set_seed(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def _sample_rows(path: str, fraction: float, seed: int) -> pd.DataFrame:
    """Read a fraction of a CSV without materialising the whole file.

    pd.read_csv followed by .sample() holds every row in memory before throwing
    almost all of them away: on the 228 MB training split that is most of a
    gigabyte to keep 1% of it, which on a memory-constrained box is the
    difference between running and being OOM-killed. A Bernoulli decision per
    row, seeded, keeps only what survives and stays deterministic.
    """
    if fraction >= 1.0:
        return pd.read_csv(path)
    rng = random.Random(seed)
    kept: list[dict] = []
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if rng.random() < fraction:
                kept.append(row)
    return pd.DataFrame(kept)


def _sample_eval(path: str, limit: int | None, seed: int) -> pd.DataFrame:
    """Read the eval split, optionally capped to `limit` rows per class overall.

    Stratified so a smoke run still reports every class. Streaming, so the cap
    bounds memory rather than merely trimming a frame already in memory.
    """
    if not limit:
        return pd.read_csv(path)
    per_class = max(limit // NUM_LABELS, 1)
    rng = random.Random(seed)
    # Reservoir per class: one pass, memory bounded by the cap, and every row
    # gets an equal chance regardless of where it sits in the file.
    reservoir: dict[str, list[dict]] = {}
    seen: Counter[str] = Counter()
    with open(path, newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            label = row["label"]
            seen[label] += 1
            bucket = reservoir.setdefault(label, [])
            if len(bucket) < per_class:
                bucket.append(row)
            else:
                j = rng.randrange(seen[label])
                if j < per_class:
                    bucket[j] = row
    rows = [r for bucket in reservoir.values() for r in bucket]
    return pd.DataFrame(rows)


def load_split(
    manifest_path: Path,
    *,
    verify: bool = True,
    train_fraction: float = 1.0,
    eval_limit: int | None = None,
    seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Load the train/eval frames named by a frozen manifest.

    Sampling happens during the read, not after it, so asking for 1% of the
    training split costs 1% of the memory.
    """
    manifest = json.loads(manifest_path.read_text())
    if verify:
        from dataset.freeze_eval import sha256

        for name, entry in manifest["files"].items():
            actual = sha256(Path(entry["path"]))
            if actual != entry["sha256"]:
                raise SystemExit(
                    f"{name} split has drifted from the frozen manifest.\n"
                    f"  expected {entry['sha256']}\n  actual   {actual}"
                )

    train = _sample_rows(manifest["files"]["train"]["path"], train_fraction, seed)
    evaluation = _sample_eval(manifest["files"]["eval"]["path"], eval_limit, seed)
    for frame in (train, evaluation):
        frame["label_id"] = frame["label"].map(LABEL_MAP)
    return train, evaluation, manifest


def split_eval_by_group(
    frame: pd.DataFrame, n_stop: int, seed: int
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Cut the held-out eval into a STOPPING set and a REPORTING set, by group.

    WHY THIS EXISTS. The phrase holdout is 15 distinct sentences in 8 phrase
    groups. Early-stopping on that set and then reporting the headline on the
    same set makes the headline optimistic by construction: the step was chosen
    because it scored well on exactly those rows. A third split is the fix, and
    it needs no regeneration because the groups are already in the frozen file.

    The cut is BY PHRASE GROUP, never by row. A group holds the first- and
    third-person phrasings of one concept, and those two sentences share almost
    all their words — splitting rows would put a sentence's own twin on the
    other side and the reporting set would no longer be unseen.

    STRATIFIED, so the stopping set contains every class. A stopping set with
    no CRITICAL rows would let eval loss fall while CRITICAL behaviour drifted,
    which is the one direction this project cannot afford to stop being able to
    see.

    THE COST, STATED. Five reporting groups is fewer CRITICAL sentences to
    report on, not more. The returned assignment records exactly which groups
    went where, and `main()` prints the distinct-phrase counts, because a recall
    figure over a handful of sentences must never be read as though it came
    from thousands of rows.
    """
    groups = sorted(frame["phrase_group"].unique())
    if n_stop >= len(groups):
        raise SystemExit(
            f"--stop-groups {n_stop} but the eval split has only {len(groups)} "
            "phrase groups. There would be nothing left to report on."
        )
    label_of = {
        g: frame.loc[frame["phrase_group"] == g, "label"].mode().iat[0] for g in groups
    }
    by_label: dict[str, list[str]] = defaultdict(list)
    for g in groups:
        by_label[label_of[g]].append(g)

    rng = random.Random(seed)
    for bucket in by_label.values():
        rng.shuffle(bucket)

    # Round-robin over the classes in a fixed order, so the first three picks
    # are one CRITICAL, one URGENT, one ROUTINE whatever the seed.
    stop_groups: list[str] = []
    while len(stop_groups) < n_stop:
        progressed = False
        for label in CLASS_ORDER:
            if len(stop_groups) >= n_stop:
                break
            if by_label[label]:
                stop_groups.append(by_label[label].pop())
                progressed = True
        if not progressed:
            break

    stop_set = set(stop_groups)
    stop_frame = frame[frame["phrase_group"].isin(stop_set)].reset_index(drop=True)
    report_frame = frame[~frame["phrase_group"].isin(stop_set)].reset_index(drop=True)
    assignment = {
        "stopping_groups": sorted(stop_set),
        "reporting_groups": sorted(set(groups) - stop_set),
        "stopping_phrases": int(stop_frame["phrase"].nunique()),
        "reporting_phrases": int(report_frame["phrase"].nunique()),
        "stopping_critical_phrases": int(
            stop_frame.loc[stop_frame["label"] == "CRITICAL", "phrase"].nunique()
        ),
        "reporting_critical_phrases": int(
            report_frame.loc[report_frame["label"] == "CRITICAL", "phrase"].nunique()
        ),
        "seed": seed,
    }
    return stop_frame, report_frame, assignment


def cap_per_class(frame: pd.DataFrame, limit: int | None, seed: int) -> pd.DataFrame:
    """Cap a frame to roughly `limit` rows, evenly across classes.

    Applied AFTER the group split, not during the file read: capping first
    would draw from all eight groups and there would be nothing group-shaped
    left to divide.
    """
    if not limit:
        return frame
    per_class = max(limit // NUM_LABELS, 1)
    parts = [
        part.sample(n=min(len(part), per_class), random_state=seed)
        for _, part in frame.groupby("label", sort=True)
    ]
    return pd.concat(parts).sample(frac=1.0, random_state=seed).reset_index(drop=True)


def freeze_bottom_layers(model, n: int) -> int:
    """Freeze the bottom `n` encoder layers. Returns how many were frozen.

    21.4M trainable parameters against 150 distinct training phrases is too much
    plasticity, not too much capacity: the eval is a phrase holdout, so what is
    being measured is generalisation to sentences never seen, and that comes
    from the pretrained representation. The more of it 150 examples are allowed
    to rewrite, the less of it survives to be measured.

    Freezing from the bottom keeps the layers nearest the output trainable,
    which is where task-specific behaviour belongs.
    """
    if n <= 0:
        return 0
    encoder = None
    for attribute in ("roberta", "bert", "base_model"):
        base = getattr(model, attribute, None)
        if base is not None and hasattr(base, "encoder"):
            encoder = base.encoder
            break
    if encoder is None or not hasattr(encoder, "layer"):
        raise SystemExit(
            "--freeze-layers: cannot find the encoder layer stack on this model. "
            "Freezing the wrong modules silently would be worse than not freezing."
        )
    layers = encoder.layer
    if n > len(layers):
        raise SystemExit(f"--freeze-layers {n} but the model has {len(layers)} layers")
    for layer in layers[:n]:
        for parameter in layer.parameters():
            parameter.requires_grad = False
    return n


def class_weights(labels: list[int], device: torch.device) -> torch.Tensor:
    """Inverse-frequency weights, normalised to mean 1."""
    counts = Counter(labels)
    total = sum(counts.values())
    raw = [total / (NUM_LABELS * counts.get(index, 1)) for index in range(NUM_LABELS)]
    mean = sum(raw) / len(raw)
    return torch.tensor(
        [value / mean for value in raw], dtype=torch.float, device=device
    )


@torch.no_grad()
def evaluate(model, loader: DataLoader, device: torch.device, criterion) -> dict:
    """Run the eval loop and return loss plus per-class metrics."""
    model.eval()
    losses: list[float] = []
    predictions: list[int] = []
    truths: list[int] = []

    for batch in loader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["labels"].to(device)
        logits = model(input_ids=input_ids, attention_mask=attention_mask).logits
        losses.append(criterion(logits, labels).item())
        predictions.extend(logits.argmax(dim=-1).cpu().tolist())
        truths.extend(labels.cpu().tolist())

    target_names = [ID_TO_LABEL[index] for index in range(NUM_LABELS)]
    report = classification_report(
        truths,
        predictions,
        target_names=target_names,
        output_dict=True,
        zero_division=0,
    )
    matrix = confusion_matrix(truths, predictions, labels=list(range(NUM_LABELS)))
    return {
        "loss": sum(losses) / max(len(losses), 1),
        "report": report,
        "confusion_matrix": matrix.tolist(),
        "examples": len(truths),
        "critical_recall": report["CRITICAL"]["recall"],
        "accuracy": report["accuracy"],
        "macro_f1": report["macro avg"]["f1-score"],
        "weighted_f1": report["weighted avg"]["f1-score"],
    }


def print_metrics(metrics: dict) -> None:
    report = metrics["report"]
    print(f"  eval examples   : {metrics['examples']:,}")
    print(f"  eval loss       : {metrics['loss']:.4f}")
    print(f"  accuracy        : {metrics['accuracy']:.4f}")
    print(f"  macro F1        : {metrics['macro_f1']:.4f}")
    print(f"  weighted F1     : {metrics['weighted_f1']:.4f}")
    print(f"\n  {'class':<10}{'precision':>11}{'recall':>9}{'f1':>9}{'support':>10}")
    for name in CLASS_ORDER:
        row = report[name]
        print(
            f"  {name:<10}{row['precision']:>11.4f}{row['recall']:>9.4f}"
            f"{row['f1-score']:>9.4f}{int(row['support']):>10,}"
        )
    print("\n  confusion matrix (rows = truth, cols = predicted)")
    print("             " + "".join(f"{name:>10}" for name in CLASS_ORDER))
    for index, row in enumerate(metrics["confusion_matrix"]):
        print(f"  {ID_TO_LABEL[index]:<10}" + "".join(f"{value:>10,}" for value in row))

    # THE GATE IS THREE CONDITIONS, ALL OF WHICH MUST HOLD. It was one until
    # 2026-09-07, when a model passed on CRITICAL recall alone while having
    # abandoned URGENT entirely. See training/evaluate.py for where each
    # threshold comes from and which one is still a placeholder.
    passed, lines = triage_gate(report, metrics["macro_f1"])
    print("\n  TRIAGE GATE")
    for line in lines:
        print(f"    {line}")
    print(f"    -> {'PASS' if passed else 'BELOW TARGET'} (all three must hold)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("dataset/processed/eval_manifest_phrase_v1.json"),
    )
    parser.add_argument("--train-fraction", type=float, default=1.0)
    parser.add_argument(
        "--eval-limit", type=int, default=None, help="Cap eval rows (smoke runs)."
    )
    parser.add_argument("--max-steps", type=int, default=None)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--max-length", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--warmup-ratio", type=float, default=0.1)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--log-every", type=int, default=25)
    parser.add_argument(
        "--eval-every", type=int, default=None, help="Eval mid-training."
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--threads", type=int, default=None)
    parser.add_argument(
        "--freeze-embeddings",
        dest="freeze_embeddings",
        action="store_true",
        default=True,
        help="Train only the encoder and head (default). Removes ~96M embedding "
        "parameters from gradients and optimiser state.",
    )
    parser.add_argument(
        "--no-freeze-embeddings",
        dest="freeze_embeddings",
        action="store_false",
        help="Fine-tune the embedding matrix too; needs ~1.15 GB more.",
    )
    parser.add_argument(
        "--freeze-layers",
        type=int,
        default=0,
        metavar="N",
        help="Freeze the bottom N encoder layers as well as the embeddings. "
        "12-layer model: 10 leaves 3.7M trainable, 8 leaves 7.2M, 0 leaves "
        "21.4M.",
    )
    parser.add_argument(
        "--stop-groups",
        type=int,
        default=0,
        metavar="N",
        help="Hold N of the eval phrase groups out as a STOPPING set; the rest "
        "become the REPORTING set the headline is taken from. 0 disables "
        "the third split and stops/reports on the same rows, which makes "
        "the headline optimistic.",
    )
    parser.add_argument(
        "--patience",
        type=int,
        default=0,
        metavar="N",
        help="Stop after N consecutive evals without an improvement in stopping "
        "loss. 0 disables early stopping, but best-checkpoint selection "
        "still applies whenever --eval-every is set.",
    )
    parser.add_argument(
        "--min-delta",
        type=float,
        default=0.0,
        help="Improvement in stopping loss that counts as progress.",
    )
    parser.add_argument(
        "--report-limit",
        type=int,
        default=None,
        help="Cap the REPORTING set (default: use all of it).",
    )
    parser.add_argument(
        "--checkpoint-every",
        type=int,
        default=200,
        help="Steps between resumable checkpoints; 0 disables.",
    )
    parser.add_argument(
        "--checkpoint-path",
        type=Path,
        default=Path("training/checkpoints/train_state.pt"),
    )
    parser.add_argument(
        "--restart", action="store_true", help="Ignore any existing checkpoint."
    )
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--save-path", type=Path, default=Path("saved_model_holdout"))
    parser.add_argument("--report", type=Path, default=Path("training/last_run.json"))
    args = parser.parse_args()

    set_seed(args.seed)
    if args.threads:
        torch.set_num_threads(args.threads)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # eval_limit is NOT passed down: the cap has to come after the group split,
    # or there would be nothing group-shaped left to divide. See cap_per_class.
    train_frame, eval_frame, manifest = load_split(
        args.manifest,
        train_fraction=args.train_fraction,
        eval_limit=None,
        seed=args.seed,
    )
    print(
        f"Manifest        : {args.manifest} (strategy {manifest['strategy']}, digests verified)"
    )
    print(f"Device          : {device}  threads={torch.get_num_threads()}")

    print(
        f"Train rows      : {len(train_frame):,}  {dict(Counter(train_frame['label']))}"
    )
    print(
        f"Train phrases   : {train_frame['phrase'].nunique()} distinct in "
        f"{train_frame['phrase_group'].nunique()} groups"
    )

    if args.stop_groups:
        stop_frame, report_frame, split = split_eval_by_group(
            eval_frame, args.stop_groups, args.seed
        )
        stop_frame = cap_per_class(stop_frame, args.eval_limit, args.seed)
        report_frame = cap_per_class(report_frame, args.report_limit, args.seed)
        print(
            f"\nTHIRD SPLIT     : {args.stop_groups} phrase groups stop, "
            f"{len(split['reporting_groups'])} report. Chosen by group, never "
            "by row."
        )
        print(
            f"  stopping set  : {len(stop_frame):,} rows, "
            f"{split['stopping_phrases']} distinct phrases "
            f"({split['stopping_critical_phrases']} CRITICAL)"
        )
        print(
            f"  REPORTING set : {len(report_frame):,} rows, "
            f"{split['reporting_phrases']} distinct phrases "
            f"({split['reporting_critical_phrases']} CRITICAL)"
        )
        print(
            "  the headline comes from the REPORTING set, which no stopping "
            "decision has seen"
        )
        print(
            f"  CRITICAL recall there is over "
            f"{split['reporting_critical_phrases']} distinct sentences — read "
            "it as that, not as a row count"
        )
        for group in split["stopping_groups"]:
            print(f"    stop  <- {group[:70]}")
    else:
        stop_frame, report_frame, split = eval_frame, eval_frame, None
        stop_frame = cap_per_class(stop_frame, args.eval_limit, args.seed)
        report_frame = stop_frame
        print(
            f"\nEval rows       : {len(stop_frame):,}  "
            f"{dict(Counter(stop_frame['label']))}"
        )
        print(
            "  NO THIRD SPLIT: stopping and reporting use the same rows, so "
            "the headline is optimistic by construction."
        )
    eval_frame = stop_frame

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME,
        num_labels=NUM_LABELS,
        id2label=ID_TO_LABEL,
        label2id=LABEL_MAP,
    ).to(device)

    if args.freeze_embeddings:
        for name, parameter in model.named_parameters():
            if "embeddings" in name:
                parameter.requires_grad = False
    frozen_layers = freeze_bottom_layers(model, args.freeze_layers)
    if frozen_layers:
        print(f"Frozen layers   : bottom {frozen_layers} encoder layers")

    trainable = [p for p in model.parameters() if p.requires_grad]
    n_total = sum(p.numel() for p in model.parameters())
    n_train = sum(p.numel() for p in trainable)
    # Frozen weights stay resident for the forward pass; only gradients and
    # optimiser state shrink. Reporting both stops the budget being taken
    # against the trainable slice alone.
    resident = (n_total + 3 * n_train) * 4 / 1e9
    print(
        f"Parameters      : {n_total:,} total, {n_train:,} trainable "
        f"({n_train / n_total:.1%}), {n_total - n_train:,} frozen"
    )
    print(
        f"Projected fp32  : {resident:.2f} GB (params + grads + AdamW over trainable)"
    )

    train_dataset = SymptomDataset(train_frame, tokenizer, args.max_length)
    # Length only; the per-epoch loader is rebuilt below so a resume can start
    # partway through an epoch without replaying the batches it already did.
    steps_per_epoch_full = math.ceil(len(train_dataset) / args.batch_size)
    collate = make_collator(tokenizer)
    eval_loader = DataLoader(
        SymptomDataset(eval_frame, tokenizer, args.max_length),
        batch_size=args.batch_size * 2,
        collate_fn=collate,
    )
    # The reporting set. Built once and touched only after training ends; no
    # stopping decision may ever read it, which is the whole point of the split.
    report_loader = DataLoader(
        SymptomDataset(report_frame, tokenizer, args.max_length),
        batch_size=args.batch_size * 2,
        collate_fn=collate,
    )

    weights = class_weights(train_frame["label_id"].tolist(), device)
    print(
        "Class weights   : "
        + ", ".join(f"{ID_TO_LABEL[i]}={weights[i]:.3f}" for i in range(NUM_LABELS))
    )
    criterion = torch.nn.CrossEntropyLoss(weight=weights)

    steps_per_epoch = steps_per_epoch_full
    total_steps = args.max_steps or steps_per_epoch * args.epochs
    optimiser = AdamW(trainable, lr=args.learning_rate, weight_decay=args.weight_decay)
    scheduler = get_linear_schedule_with_warmup(
        optimiser, int(total_steps * args.warmup_ratio), total_steps
    )
    print(
        f"Steps           : {total_steps:,} (batch {args.batch_size}, seq {args.max_length})\n"
    )

    history: list[dict] = []
    losses: list[float] = []
    step = 0
    start_epoch = 0
    start_batch = 0
    resumed_seconds = 0.0

    fingerprint = run_fingerprint(manifest, args)
    checkpoint_path = args.checkpoint_path
    if args.restart and checkpoint_path.exists():
        checkpoint_path.unlink()
        print("Checkpoint      : discarded on --restart")
    resumed = None if args.restart else load_checkpoint(checkpoint_path, fingerprint)
    if resumed is not None:
        model.load_state_dict(resumed["model"])
        optimiser.load_state_dict(resumed["optimiser"])
        scheduler.load_state_dict(resumed["scheduler"])
        step = resumed["step"]
        start_epoch = resumed["epoch"]
        start_batch = resumed["batch_in_epoch"]
        history = resumed["history"]
        losses = resumed["losses"]
        resumed_seconds = resumed["elapsed"]
        random.setstate(resumed["rng_python"])
        np.random.set_state(resumed["rng_numpy"])
        torch.set_rng_state(resumed["rng_torch"])
        print(
            f"Checkpoint      : resumed at step {step:,}/{total_steps:,} "
            f"(epoch {start_epoch}, batch {start_batch:,}) from {checkpoint_path}"
        )
    else:
        print(
            f"Checkpoint      : {checkpoint_path} (every {args.checkpoint_every} steps)"
            if args.checkpoint_every
            else "Checkpoint      : disabled"
        )

    started = time.monotonic() - resumed_seconds
    model.train()

    def write_checkpoint(epoch: int, batch_in_epoch: int) -> None:
        if not args.checkpoint_every:
            return
        save_checkpoint(
            checkpoint_path,
            {
                "fingerprint": fingerprint,
                "step": step,
                "epoch": epoch,
                "batch_in_epoch": batch_in_epoch,
                "model": model.state_dict(),
                "optimiser": optimiser.state_dict(),
                "scheduler": scheduler.state_dict(),
                "history": history,
                "losses": losses,
                "elapsed": time.monotonic() - started,
                "rng_python": random.getstate(),
                "rng_numpy": np.random.get_state(),
                "rng_torch": torch.get_rng_state(),
            },
        )

    # BEST-CHECKPOINT SELECTION. The trainer previously saved whatever the last
    # step produced, so a run that had already collapsed into memorisation still
    # shipped its final weights. Best weights go to disk rather than to a second
    # copy in memory: the full state_dict is ~470 MB of fp32 and the machine has
    # 7.8 GB.
    best_loss = float("inf")
    best_step = 0
    best_metrics: dict | None = None
    since_improved = 0
    stopped_early = False
    best_path = args.checkpoint_path.with_name(args.checkpoint_path.stem + "_best.pt")

    stop = False
    for epoch in range(start_epoch, args.epochs):
        if stop:
            break
        # Rebuild the epoch's shuffled order from (seed, epoch) and drop the
        # batches already done, so a resume neither repeats nor skips examples.
        order = epoch_order(len(train_dataset), args.seed, epoch)
        skip = start_batch * args.batch_size if epoch == start_epoch else 0
        train_loader = DataLoader(
            Subset(train_dataset, order[skip:]),
            batch_size=args.batch_size,
            shuffle=False,
            collate_fn=collate,
        )
        batch_in_epoch = start_batch if epoch == start_epoch else 0
        for batch in train_loader:
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["labels"].to(device)

            logits = model(input_ids=input_ids, attention_mask=attention_mask).logits
            loss = criterion(logits, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(trainable, 1.0)
            optimiser.step()
            scheduler.step()
            optimiser.zero_grad()

            losses.append(loss.item())
            step += 1
            batch_in_epoch += 1

            if args.checkpoint_every and step % args.checkpoint_every == 0:
                write_checkpoint(epoch, batch_in_epoch)

            if step % args.log_every == 0:
                window = losses[-args.log_every :]
                elapsed = time.monotonic() - started
                mean_loss = sum(window) / len(window)
                history.append({"step": step, "loss": round(mean_loss, 4)})
                print(
                    f"  step {step:>5}/{total_steps}  loss {mean_loss:.4f}  "
                    f"lr {scheduler.get_last_lr()[0]:.2e}  "
                    f"{elapsed:6.1f}s  {step / elapsed:5.2f} steps/s",
                    flush=True,
                )
            if args.eval_every and step % args.eval_every == 0:
                interim = evaluate(model, eval_loader, device, criterion)
                # SELECTION IS ON LOSS, NEVER ON critical_recall. Two reasons,
                # and the second is the one that decides it. First, the stopping
                # set holds a handful of distinct sentences, so recall over it
                # moves in coarse jumps and cannot resolve an optimum. Second,
                # critical_recall IS the deployment gate: choosing weights by it
                # would mean the gate is measuring a fit it was itself used to
                # produce. It is printed at every eval and recorded at the
                # selected step, and it decides nothing.
                improved = interim["loss"] < best_loss - args.min_delta
                if improved:
                    best_loss = interim["loss"]
                    best_step = step
                    best_metrics = {
                        k: v
                        for k, v in interim.items()
                        if k not in ("report", "confusion_matrix")
                    }
                    since_improved = 0
                    save_checkpoint(
                        best_path,
                        {
                            "fingerprint": fingerprint,
                            "step": step,
                            "model": model.state_dict(),
                        },
                    )
                else:
                    since_improved += 1
                mark = "  <- best" if improved else f"  ({since_improved} since best)"
                print(
                    f"  [interim eval] step {step}  stopping loss "
                    f"{interim['loss']:.4f}  critical_recall "
                    f"{interim['critical_recall']:.4f}{mark}",
                    flush=True,
                )
                if args.patience and since_improved >= args.patience:
                    print(
                        f"\nEARLY STOP      : stopping loss has not improved "
                        f"for {since_improved} evals "
                        f"({since_improved * args.eval_every} steps). "
                        f"Best was {best_loss:.4f} at step {best_step:,}."
                    )
                    stopped_early = True
                    stop = True
                    break
                model.train()
            if args.max_steps and step >= args.max_steps:
                stop = True
                break

    train_seconds = time.monotonic() - started
    if args.checkpoint_every and checkpoint_path.exists():
        # The run finished; a stale checkpoint would resume a completed job.
        checkpoint_path.unlink()
        print("  checkpoint cleared (run completed)")
    window = max(len(losses) // 5, 1)
    first_mean = sum(losses[:window]) / window
    last_mean = sum(losses[-window:]) / window
    print(
        f"\nTraining done   : {step:,} steps in {train_seconds:.1f}s\n"
        f"  loss first {window} steps : {first_mean:.4f}\n"
        f"  loss last  {window} steps : {last_mean:.4f}\n"
        f"  change                  : {last_mean - first_mean:+.4f} "
        f"({'decreasing' if last_mean < first_mean else 'NOT decreasing'})"
    )

    # RESTORE THE SELECTED WEIGHTS. Without this the run reports whatever the
    # last step produced, which is exactly how a collapsed run still ships.
    restored_from = None
    if best_step and best_path.exists():
        payload = load_checkpoint(best_path, fingerprint)
        if payload is None:
            raise SystemExit(
                f"best checkpoint at {best_path} could not be read back. Refusing "
                "to report on the final step's weights instead — that would be "
                "the silent substitution this selection exists to prevent."
            )
        model.load_state_dict(payload["model"])
        restored_from = best_step
        print(
            f"\nSelected step   : {best_step:,} of {step:,} "
            f"(stopping loss {best_loss:.4f})"
        )
        if not stopped_early:
            print(
                "  NOTE: the budget ran out before patience did, so the "
                "optimum may be later than this. Raise --max-steps to find out."
            )
        best_path.unlink()
    elif args.eval_every:
        print("\nSelected step   : none — no eval improved on the initial value")

    if split is not None:
        print("\nStopping set (chose the step; NOT the headline)")
        print_metrics(evaluate(model, eval_loader, device, criterion))

    print(
        "\nREPORTING SET — no stopping decision has seen these rows"
        if split is not None
        else "\nEvaluation"
    )
    metrics = evaluate(model, report_loader, device, criterion)
    print_metrics(metrics)
    if split is not None:
        print(
            f"\n  CRITICAL recall above is over "
            f"{split['reporting_critical_phrases']} distinct sentences in "
            f"{len(split['reporting_groups'])} phrase groups. The row count is "
            "frame permutations of those sentences and is not an independent "
            "sample size."
        )
        balance = Counter(report_frame["label"])
        if max(balance.values()) > 2 * min(balance.values()):
            print(
                "  The reporting set is class-IMBALANCED "
                f"({dict(balance)}) because phrase groups carry different "
                "numbers of frames. Per-class precision and recall are "
                "unaffected and are the numbers to read; accuracy and "
                "weighted F1 above are not, and must not be quoted as "
                "headline figures."
            )

    result = {
        "manifest": str(args.manifest),
        "strategy": manifest["strategy"],
        "split_seed": manifest["split_seed"],
        "train_rows": len(train_frame),
        "eval_rows": len(eval_frame),
        "steps": step,
        "selected_step": restored_from,
        "stopped_early": stopped_early,
        "stopping_loss_at_selected_step": round(best_loss, 4) if best_step else None,
        "stopping_metrics_at_selected_step": best_metrics,
        "eval_split": split,
        "train_seconds": round(train_seconds, 1),
        "loss_first_window": round(first_mean, 4),
        "loss_last_window": round(last_mean, 4),
        "loss_history": history,
        "metrics": {k: v for k, v in metrics.items() if k != "report"},
        "per_class": {name: metrics["report"][name] for name in CLASS_ORDER},
        "args": {k: str(v) for k, v in vars(args).items()},
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2))
    print(f"\nRun report written to {args.report}")

    if not args.no_save:
        args.save_path.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(args.save_path)
        tokenizer.save_pretrained(args.save_path / "tokenizer")
        print(f"Model saved to {args.save_path}")
    else:
        print("Smoke run: model not saved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
