#!/usr/bin/env python
"""Seed provenance of a split: how many distinct source phrases it holds, and how many it
shares with the split it is compared against.

    python dataset/seed_provenance.py --train dataset/processed/train_phrase_holdout.csv \\
        --test dataset/processed/eval_phrase_holdout.csv --seed-column phrase

**This is the first number a reviewer asks of any metric computed on generated data**, so
`banner()` produces the line that goes at the top of every report carrying one.

Two distinct facts, and neither substitutes for the other:

1. **Shared seeds** — the same source phrase appearing in both splits. Zero is required
   (EVAL_SET_SPEC §8, L8), and the phrase split enforces it.
2. **Shared provenance** — both splits produced by one generator from one inventory of
   seed phrases, under one set of frames. This is true even when no seed is shared, and
   it is what makes a metric measured across them a statement about generalisation
   *within the generator's distribution*, not about clinical performance.

Stdlib only.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_SEED_COLUMN = "phrase"


@dataclass(frozen=True)
class Summary:
    path: str
    rows: int
    distinct_seeds: int
    rows_per_seed_max: int
    largest_seed_share: float
    seeds_per_language: dict[str, int]


@dataclass(frozen=True)
class Overlap:
    train_seeds: int
    test_seeds: int
    shared_seeds: list[str]
    shared_test_rows: int


def _read(path: Path, seed_column: str) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if rows and seed_column not in rows[0]:
        raise ValueError(
            f"{path} has no {seed_column!r} column; nothing can be attributed to a seed"
        )
    return rows


def summarise(path: Path, *, seed_column: str = DEFAULT_SEED_COLUMN) -> Summary:
    rows = _read(path, seed_column)
    counts = Counter((row.get(seed_column) or "").strip() for row in rows)
    per_language: dict[str, set[str]] = {}
    for row in rows:
        per_language.setdefault((row.get("language") or "").strip(), set()).add(
            (row.get(seed_column) or "").strip()
        )
    return Summary(
        path=str(path),
        rows=len(rows),
        distinct_seeds=len(counts),
        rows_per_seed_max=max(counts.values()) if counts else 0,
        largest_seed_share=(max(counts.values()) / len(rows)) if rows else 0.0,
        seeds_per_language={lang: len(seeds) for lang, seeds in per_language.items()},
    )


def overlap(
    train: Path, test: Path, *, seed_column: str = DEFAULT_SEED_COLUMN
) -> Overlap:
    train_rows, test_rows = _read(train, seed_column), _read(test, seed_column)
    train_seeds = {(row.get(seed_column) or "").strip() for row in train_rows}
    test_seeds = {(row.get(seed_column) or "").strip() for row in test_rows}
    shared = sorted(train_seeds & test_seeds)
    return Overlap(
        train_seeds=len(train_seeds),
        test_seeds=len(test_seeds),
        shared_seeds=shared,
        shared_test_rows=sum(
            1
            for row in test_rows
            if (row.get(seed_column) or "").strip() in set(shared)
        ),
    )


def banner(train: Path, test: Path, *, seed_column: str = DEFAULT_SEED_COLUMN) -> str:
    """The line that heads any report carrying a metric measured on these splits."""
    counts = overlap(train, test, seed_column=seed_column)
    train_summary = summarise(train, seed_column=seed_column)
    test_summary = summarise(test, seed_column=seed_column)
    return (
        f"SEED PROVENANCE — train {train_summary.distinct_seeds:,} distinct source phrases "
        f"({train_summary.rows:,} rows), test {test_summary.distinct_seeds:,} "
        f"({test_summary.rows:,} rows), shared seeds {len(counts.shared_seeds):,}. "
        f"Largest single seed is {test_summary.largest_seed_share:.1%} of the test split. "
        "Both splits come from the same generator and the same seed inventory, so any metric "
        "measured across them describes generalisation WITHIN the generator's distribution, "
        "not clinical performance."
    )


def report(train: Path, test: Path, *, seed_column: str = DEFAULT_SEED_COLUMN) -> str:
    lines = [banner(train, test, seed_column=seed_column), ""]
    for label, path in (("train", train), ("test", test)):
        summary = summarise(path, seed_column=seed_column)
        lines += [
            f"{label}: {summary.path}",
            f"  rows                {summary.rows:,}",
            f"  distinct seeds      {summary.distinct_seeds:,}",
            f"  max rows per seed   {summary.rows_per_seed_max:,}",
            f"  largest seed share  {summary.largest_seed_share:.2%}",
            f"  seeds per language  {summary.seeds_per_language}",
        ]
    counts = overlap(train, test, seed_column=seed_column)
    lines += [
        "",
        f"shared seeds: {len(counts.shared_seeds):,}"
        + (f" ({', '.join(counts.shared_seeds[:3])}…)" if counts.shared_seeds else ""),
        f"test rows built from a shared seed: {counts.shared_test_rows:,}",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--train", type=Path, required=True)
    parser.add_argument("--test", type=Path, required=True)
    parser.add_argument("--seed-column", default=DEFAULT_SEED_COLUMN)
    args = parser.parse_args(argv)
    print(report(args.train, args.test, seed_column=args.seed_column))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
