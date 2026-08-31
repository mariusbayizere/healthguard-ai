#!/usr/bin/env python
"""Freeze an evaluation split so benchmark numbers stay comparable.

Writes a versioned manifest recording exactly which rows the eval set contains,
which phrase groups were held out, the seeds that produced them, and SHA-256
digests of the split files. `--verify` re-checks the digests, so a split that
drifts between runs is caught before it silently invalidates a comparison.

Usage:
    python dataset/freeze_eval.py --strategy phrase
    python dataset/freeze_eval.py --strategy phrase --verify
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dataset.atomicio import atomic_write_json  # noqa: E402
from dataset.split_dataset import phrase_components  # noqa: E402

MANIFEST_VERSION = 1
LANGUAGE_ORDER = ("kinyarwanda", "english", "french", "swahili", "mixed")
CLASS_ORDER = ("CRITICAL", "URGENT", "ROUTINE")
# Below this, a per-cell metric is too noisy to quote in a paper.
THIN_CELL_THRESHOLD = 1_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_commit() -> str | None:
    """The commit the split was produced at, when inside a repository."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip() or None if result.returncode == 0 else None
    except (OSError, subprocess.SubprocessError):
        return None


def cell_matrix(path: Path) -> tuple[dict[str, dict[str, int]], Counter, Counter, int]:
    """Language x class counts for a split."""
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    languages: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    total = 0
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            matrix[row["language"]][row["label"]] += 1
            languages[row["language"]] += 1
            labels[row["label"]] += 1
            total += 1
    return {k: dict(v) for k, v in matrix.items()}, languages, labels, total


def print_matrix(matrix: dict[str, dict[str, int]], languages: Counter, labels: Counter, total: int) -> list[str]:
    """Print the matrix and return the cells too thin to report on."""
    header = f"  {'language':<13}" + "".join(f"{label:>12}" for label in CLASS_ORDER) + f"{'row total':>12}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    thin: list[str] = []
    for language in LANGUAGE_ORDER:
        if language not in matrix:
            continue
        line = f"  {language:<13}"
        for label in CLASS_ORDER:
            count = matrix[language].get(label, 0)
            marker = " *" if count < THIN_CELL_THRESHOLD else "  "
            line += f"{count:>10,}{marker}"
            if count < THIN_CELL_THRESHOLD:
                thin.append(f"{language}/{label} ({count:,})")
        line += f"{languages[language]:>12,}"
        print(line)
    print("  " + "-" * (len(header) - 2))
    footer = f"  {'col total':<13}" + "".join(f"{labels.get(label, 0):>12,}" for label in CLASS_ORDER)
    print(footer + f"{total:>12,}")
    if thin:
        print(f"\n  * below {THIN_CELL_THRESHOLD:,} rows — too thin to quote a per-cell metric")
    return thin


def build_manifest(strategy: str, out_dir: Path, source: Path) -> dict:
    split_report_path = out_dir / f"split_{strategy}_holdout.json"
    if not split_report_path.exists():
        raise SystemExit(f"Missing {split_report_path}; run split_dataset.py first.")
    split_report = json.loads(split_report_path.read_text())

    train_path = out_dir / f"train_{strategy}_holdout.csv"
    eval_path = out_dir / f"eval_{strategy}_holdout.csv"
    for path in (train_path, eval_path):
        if not path.exists():
            raise SystemExit(f"Missing {path}; run split_dataset.py without --dry-run.")

    components = phrase_components()
    members: dict[str, list[str]] = defaultdict(list)
    for phrase, root in components.items():
        members[root].append(phrase)

    holdout = split_report["holdout_groups"]
    holdout_detail = [
        {"group": group, "phrases": sorted(members.get(group, [group]))} for group in sorted(holdout)
    ]

    matrix, languages, labels, total = cell_matrix(eval_path)

    return {
        "manifest_version": MANIFEST_VERSION,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_commit(),
        "strategy": strategy,
        "eval_fraction_target": split_report["eval_fraction_target"],
        "split_seed": split_report["seed"],
        # The generator's own seed; changing it changes the corpus itself.
        "generator_seed": 42,
        "source": {"path": str(source), "sha256": sha256(source)},
        "files": {
            "train": {
                "path": str(train_path),
                "sha256": sha256(train_path),
                "rows": split_report["train"]["rows"],
            },
            "eval": {
                "path": str(eval_path),
                "sha256": sha256(eval_path),
                "rows": split_report["eval"]["rows"],
            },
        },
        "holdout_groups": holdout_detail,
        "held_out_phrase_count": sum(len(entry["phrases"]) for entry in holdout_detail),
        "leakage": split_report["leakage"],
        "eval_matrix": matrix,
        "eval_languages": dict(languages),
        "eval_labels": dict(labels),
        "eval_total": total,
    }


def verify(manifest_path: Path) -> int:
    """Re-check every digest in a manifest."""
    manifest = json.loads(manifest_path.read_text())
    print(f"Verifying {manifest_path} (version {manifest['manifest_version']})")
    print(f"  created  {manifest['created_at']}")
    print(f"  strategy {manifest['strategy']}, split seed {manifest['split_seed']}")

    failures = 0
    checks = [("source", Path(manifest["source"]["path"]), manifest["source"]["sha256"])]
    for name, entry in manifest["files"].items():
        checks.append((name, Path(entry["path"]), entry["sha256"]))

    for name, path, expected in checks:
        if not path.exists():
            print(f"  {name:<8} MISSING  {path}")
            failures += 1
            continue
        actual = sha256(path)
        status = "ok" if actual == expected else "DRIFTED"
        print(f"  {name:<8} {status:<8} {path}")
        if actual != expected:
            print(f"           expected {expected[:16]}  actual {actual[:16]}")
            failures += 1

    if failures:
        print(f"\n{failures} file(s) do not match the frozen manifest.")
        return 1
    print("\nEval set matches the frozen manifest.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strategy", choices=("phrase", "family"), default="phrase")
    parser.add_argument("--out-dir", type=Path, default=Path("dataset/processed"))
    parser.add_argument("--source", type=Path, default=Path("dataset/raw/symptoms_large.csv"))
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    manifest_path = args.out_dir / f"eval_manifest_{args.strategy}_v{MANIFEST_VERSION}.json"
    if args.verify:
        return verify(manifest_path)

    manifest = build_manifest(args.strategy, args.out_dir, args.source)

    print(f"Frozen eval manifest : {manifest_path}")
    print(f"  strategy           : {manifest['strategy']}")
    print(f"  split seed         : {manifest['split_seed']}   generator seed: {manifest['generator_seed']}")
    print(f"  git commit         : {manifest['git_commit'] or 'not a git repository'}")
    print(f"  source sha256      : {manifest['source']['sha256'][:16]}")
    print(f"  train              : {manifest['files']['train']['rows']:,} rows, "
          f"sha256 {manifest['files']['train']['sha256'][:16]}")
    print(f"  eval               : {manifest['files']['eval']['rows']:,} rows, "
          f"sha256 {manifest['files']['eval']['sha256'][:16]}")
    print(f"  held-out groups    : {len(manifest['holdout_groups'])} "
          f"({manifest['held_out_phrase_count']} phrases)")
    print(f"  substring leaks    : {manifest['leakage']['substring_violations']}")

    print(f"\nEval per-cell counts (language x class), {manifest['eval_total']:,} rows:")
    matrix, languages, labels, total = (
        manifest["eval_matrix"],
        Counter(manifest["eval_languages"]),
        Counter(manifest["eval_labels"]),
        manifest["eval_total"],
    )
    thin = print_matrix(matrix, languages, labels, total)
    manifest["thin_cells"] = thin
    atomic_write_json(manifest_path, manifest)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
