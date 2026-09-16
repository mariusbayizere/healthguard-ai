"""The majority-class baseline of a labelled split: what a model that has learned nothing scores.

    cd kinyamed/ml_model && python3 ../reports/measurements/majority_baseline.py \\
        > ../reports/measurements/majority_baseline.txt

WHY THIS NUMBER IS LEGITIMATE AND A MODEL SCORE IS NOT
------------------------------------------------------
This reads labels only. It never runs a model, so it is not a claim about any model's
quality and it is not a gate metric (the gate is `training/evaluate.py`, and it refuses
on every set below EVAL_SET_SPEC). What it gives is the floor: a constant classifier
that always answers the most frequent class scores exactly this. Any reported accuracy
must be read against it, because an accuracy below or near the floor is evidence of
nothing having been learned.

THE LABELS HERE ARE TEMPLATE LABELS, NOT GOLD
---------------------------------------------
Every split below is generated: each row's label comes from the seed phrase it was built
from, not from a clinician (DATASET_AUDIT). The baseline is therefore the floor *of that
generated distribution*, and nothing here says what the real-world prevalence is.

ROWS ARE NOT INDEPENDENT
------------------------
Each split is built from a handful of distinct source sentences, so rows are clustered.
The distinct-sentence counts are printed beside the row counts for that reason: they are
what any interval would have to be computed over (EVAL_SET_SPEC §8).
"""

from __future__ import annotations

import csv
from collections import Counter
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[2] / "ml_model"

SPLITS = (
    ("v2 phrase-holdout eval split", "dataset/processed/eval_phrase_holdout.csv", "label", "phrase"),
    ("n=9 gate gold set (the reporting subset)", "dataset/processed/gate_n9_gold.csv", "gold_label", "scenario_id"),
)
PROBE_LIMIT = 200  # training/probe.py's default sample


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _report(name: str, rows: list[dict[str, str]], label_column: str, cluster_column: str) -> None:
    labels = Counter(row[label_column] for row in rows)
    clusters = len({row.get(cluster_column, "") for row in rows})
    total = sum(labels.values())
    top, count = labels.most_common(1)[0]
    print(f"{name}")
    print(f"  rows {total:,} from {clusters:,} distinct source sentences")
    for label, n in sorted(labels.items(), key=lambda kv: -kv[1]):
        print(f"    {label:<9} {n:>7,}  {n / total:6.2%}")
    print(f"  majority class: {top}")
    print(f"  ALWAYS-{top} accuracy on this split: {count / total:.4f}")
    print()


def main() -> int:
    print("Majority-class baselines. Labels only; no model is run. NOT A GATE METRIC.")
    print()
    for name, relative, label_column, cluster_column in SPLITS:
        path = ML_ROOT / relative
        if not path.is_file():
            print(f"{name}\n  {relative} is not on disk (corpus-derived, git-ignored); skipped\n")
            continue
        rows = _rows(path)
        _report(name, rows, label_column, cluster_column)
        if relative.endswith("eval_phrase_holdout.csv"):
            step = max(1, len(rows) // PROBE_LIMIT)
            sample = [rows[k] for k in range(0, len(rows), step)][:PROBE_LIMIT]
            _report(
                f"  -> the {PROBE_LIMIT}-row sample training/probe.py takes from it",
                sample,
                label_column,
                cluster_column,
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
