"""Build the seeds-vs-rows sweep arms as derived subsets of the frozen v2 split.

WHAT THIS IS AND IS NOT. It does not regenerate a split and does not touch the
committed v2 split, which stays exactly as frozen. It selects rows from
`train_phrase_holdout.csv` to make one training file per arm, and writes a
manifest per arm in the schema `training/train_holdout.py` already reads. The
trainer is used unmodified.

EVERY ARM IS EVALUATED ON THE SAME FILE. `eval_phrase_holdout.csv`, frozen, 15
phrases, verified to share no seed with the training split. The eval digest is
copied from the parent manifest into every arm, and
`tests/test_sweep_arms.py` fails if any two arms disagree about it. Convention
is not enough for the one file the whole comparison rests on.

WHY THE TOTAL IS 3,000 ROWS AND NOT 30,000. The generator's output per seed
varies twenty-one-fold: 386 rows for the smallest phrase, 8,129 for the largest,
median 1,146. A fixed 30,000-row budget therefore silently selects for large
seeds, and only 51 of 150 phrases can supply the 3,000 rows a ten-seed arm would
need. Those 51 are not label-balanced: ROUTINE is 27% of the full inventory and
18% of that pool. An arm built that way differs from a 120-seed arm in class mix
as well as seed count, and no curve could separate the two.

3,860 is the largest total at which every arm can still draw seeds uniformly
from all 150 (ten seeds times the 386 rows of the smallest phrase). 3,000 is the
round number below it. At that budget every arm samples from the same pool with
the same label distribution, and the arms differ only in seed count.

IT IS ALSO THE HARDER TEST. The claim is that seeds matter and rows do not, so
running at a tenth of the volume tests it directly: if the curve still tracks
seeds at 3,000 rows the claim is stronger, and if every arm collapses because
3,000 rows is too few for a three-class task, that is a boundary condition.

PROVENANCE. The labels these arms carry were assigned by a single non-clinician
annotator with no second rater and no inter-rater agreement. Nothing measured
here is clinical performance; it is a property of corpus structure.

Usage:
    python review/build_sweep_arms.py            # write arms and manifests
    python review/build_sweep_arms.py --check    # fail if any arm has drifted
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import random
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARENT_MANIFEST = ROOT / "dataset" / "processed" / "eval_manifest_phrase_v2.json"
TRAIN_SPLIT = ROOT / "dataset" / "processed" / "train_phrase_holdout.csv"
OUT_DIR = ROOT / "dataset" / "sweep"

# The design, fixed here so a run cannot quietly use different numbers.
TOTAL_ROWS = 3_000
SEED_COUNTS = (10, 20, 40, 80, 120)
REPLICATE_SEEDS = (101, 202, 303)

# The training configuration every arm is run with, recorded in each manifest so
# the run is reconstructable from the manifest alone.
#
# THREADS 4, NOT THE 2 THE REPORTED RUNS USED. This machine has four cores; the
# three reported configurations were pinned to two threads and their 115, 70 and
# 95 minute figures are for that pinning. A thread count changes throughput and
# not what is learned, so a new experiment may choose its own, but it must be
# recorded rather than left to be inferred from whoever ran it.
RUN_CONFIG = {
    "epochs": 5,
    "batch_size": 16,
    "max_length": 96,
    "learning_rate": 1e-5,
    "freeze_layers": 8,
    "stop_groups": 3,
    "threads": 4,
}


class Refused(RuntimeError):
    """A condition the sweep will not work around. Reported, never patched."""


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def load_parent() -> dict:
    if not PARENT_MANIFEST.exists():
        raise Refused(
            f"{PARENT_MANIFEST.name} is missing; there is no parent to derive from"
        )
    parent = json.loads(PARENT_MANIFEST.read_text(encoding="utf-8"))
    actual = sha256(TRAIN_SPLIT)
    if actual != parent["files"]["train"]["sha256"]:
        raise Refused(
            "the parent train split has drifted from its frozen manifest.\n"
            f"  manifest {parent['files']['train']['sha256']}\n  actual   {actual}\n"
            "Refusing to derive arms from a split that is not the one that was frozen."
        )
    return parent


def read_train() -> tuple[list[dict], list[str]]:
    with TRAIN_SPLIT.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader), list(reader.fieldnames or [])


def arm_rows(
    rows: list[dict], n_seeds: int, rng: random.Random
) -> tuple[list[dict], list[str]]:
    """Draw n_seeds phrases uniformly from ALL phrases, then rows from each.

    Uniform over the whole inventory is the point: restricting to phrases large
    enough for a bigger budget is what introduces the class-mix confound.
    """
    by_phrase: dict[str, list[dict]] = collections.defaultdict(list)
    for row in rows:
        by_phrase[row["phrase"]].append(row)

    phrases = sorted(by_phrase)
    if n_seeds > len(phrases):
        raise Refused(f"{n_seeds} seeds requested but the split has {len(phrases)}")
    chosen = rng.sample(phrases, n_seeds)

    base, extra = divmod(TOTAL_ROWS, n_seeds)
    selected: list[dict] = []
    for index, phrase in enumerate(sorted(chosen)):
        quota = base + (1 if index < extra else 0)
        available = by_phrase[phrase]
        if len(available) < quota:
            raise Refused(
                f"phrase {phrase!r} has {len(available)} rows but the arm needs "
                f"{quota}. The budget selects for large seeds; that is the "
                "condition this design exists to avoid."
            )
        selected.extend(rng.sample(available, quota))
    rng.shuffle(selected)
    return selected, sorted(chosen)


def write_arm(
    rows: list[dict],
    fields: list[str],
    parent: dict,
    n_seeds: int,
    replicate: int,
    rng_seed: int,
) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    name = f"seeds{n_seeds:03d}_rep{replicate}"
    train_path = OUT_DIR / f"train_{name}.csv"
    with train_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    train_digest = sha256(train_path)
    eval_entry = dict(parent["files"]["eval"])

    manifest = {
        "manifest_version": 2,
        "strategy": parent["strategy"],
        "split_seed": parent["split_seed"],
        "generator_seed": parent["generator_seed"],
        # THE DERIVATION CHAIN, explicit so it can be audited.
        "derived_from": {
            "manifest": str(PARENT_MANIFEST.relative_to(ROOT)),
            "manifest_sha256": sha256(PARENT_MANIFEST),
            "train_sha256": parent["files"]["train"]["sha256"],
            "eval_sha256": parent["files"]["eval"]["sha256"],
        },
        "sweep": {
            "arm": name,
            "distinct_seeds": n_seeds,
            "total_rows": len(rows),
            "rows_per_seed": TOTAL_ROWS // n_seeds,
            "replicate": replicate,
            "rng_seed": rng_seed,
            "code_commit": git_commit(),
            "run_config": dict(RUN_CONFIG),
        },
        "provenance": (
            "Labels assigned by a single non-clinician annotator; no second "
            "rater; no inter-rater agreement. Not clinical ground truth."
        ),
        "source": parent["source"],
        "files": {
            "train": {
                "path": str(train_path.relative_to(ROOT)),
                "sha256": train_digest,
                "rows": len(rows),
            },
            # UNCHANGED, copied from the parent. Every arm scores on this file.
            "eval": eval_entry,
        },
    }
    manifest_path = OUT_DIR / f"manifest_{name}.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def build() -> list[dict]:
    parent = load_parent()
    rows, fields = read_train()
    manifests = []
    for n_seeds in SEED_COUNTS:
        for replicate, rng_seed in enumerate(REPLICATE_SEEDS, 1):
            rng = random.Random(rng_seed * 1000 + n_seeds)
            selected, chosen = arm_rows(rows, n_seeds, rng)
            manifest = write_arm(selected, fields, parent, n_seeds, replicate, rng_seed)
            labels = collections.Counter(r["label"] for r in selected)
            manifest["sweep"]["label_mix"] = dict(labels)
            manifest["sweep"]["phrases"] = chosen
            path = OUT_DIR / f"manifest_{manifest['sweep']['arm']}.json"
            path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            manifests.append(manifest)
    return manifests


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    try:
        if args.check:
            ok = True
            for path in sorted(OUT_DIR.glob("manifest_*.json")):
                m = json.loads(path.read_text(encoding="utf-8"))
                train = ROOT / m["files"]["train"]["path"]
                if not train.exists() or sha256(train) != m["files"]["train"]["sha256"]:
                    print(f"  STALE {path.name}", file=sys.stderr)
                    ok = False
            print("all arms match their manifests." if ok else "arms have drifted.")
            return 0 if ok else 1

        manifests = build()
    except Refused as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2

    print(
        "Labels: single non-clinician annotator, no second rater, no "
        "inter-rater agreement. Not clinical ground truth.\n"
    )
    print(
        f"{len(manifests)} arms in {OUT_DIR.relative_to(ROOT)}, total {TOTAL_ROWS:,} rows each\n"
    )
    print(
        f"  {'arm':18} {'seeds':>5} {'rows/seed':>9} {'CRITICAL':>8} {'URGENT':>7} {'ROUTINE':>7}"
    )
    for m in manifests:
        s, mix = m["sweep"], m["sweep"]["label_mix"]
        print(
            f"  {s['arm']:18} {s['distinct_seeds']:5} {s['rows_per_seed']:9} "
            f"{mix.get('CRITICAL', 0):8} {mix.get('URGENT', 0):7} {mix.get('ROUTINE', 0):7}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
