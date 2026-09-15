#!/usr/bin/env python
"""Run the deployment gate on the only held-out set that exists today, to show it refuse.

The v2 phrase holdout's reporting subset is 17,942 rows built from 9 distinct
Kinyarwanda sentences (MODEL_AUDIT §4.1). This script rebuilds that subset with the
training code's own splitter, writes it as a gold file with one scenario per
distinct sentence, and runs the gate's population check. On today's set that check
refuses (9 distinct sentences are below every EVAL_SET_SPEC minimum) and the script
exits 2 without loading the model. Only if some gate cell can be measured does it
score the set with the model (inference only; nothing is trained) and run
`training/evaluate.py`. The refusal is the result.

    cd kinyamed/ml_model
    python scripts/gate_on_current_holdout.py --model ~/kinyamed-runs/model_v2d_freeze8_lr1e-5
    python scripts/gate_on_current_holdout.py --check-only   # counts only, no weights

The CSVs it writes are corpus-derived and git-ignored (dataset/processed/*.csv).
The report goes to ../reports/measurements/gate_n9/.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

MANIFEST = ROOT / "dataset/processed/eval_manifest_phrase_v2.json"
GOLD = ROOT / "dataset/processed/gate_n9_gold.csv"
PREDICTIONS = ROOT / "dataset/processed/gate_n9_predictions.csv"
OUT = ROOT.parent / "reports/measurements/gate_n9"
STOP_GROUPS = 3  # as the v2d run (run record args.stop_groups)


def build_gold() -> tuple[int, int]:
    import pandas as pd
    from training.holdout_eval import load_manifest
    from training.train_holdout import split_eval_by_group

    manifest = load_manifest(MANIFEST)  # verifies the frozen digests
    frame = pd.read_csv(ROOT / manifest["files"]["eval"]["path"])
    _, report, _ = split_eval_by_group(frame, STOP_GROUPS, manifest["split_seed"])
    with GOLD.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["item_id", "text", "language", "gold_label", "scenario_id", "split"]
        )
        for k, row in report.iterrows():
            # One scenario per distinct authored sentence: the rows are frame
            # permutations of it, not independent observations.
            writer.writerow(
                [
                    f"r{k:05d}",
                    row["text"],
                    row["language"],
                    row["label"],
                    row["phrase"],
                    "test",
                ]
            )
    return len(report), int(report["phrase"].nunique())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path)
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="build the gold file and print the gate's counts; never load a model",
    )
    parser.add_argument("--max-length", type=int, default=96)  # as the v2d run
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args(argv)
    if args.model is None and not args.check_only:
        parser.error("give --model, or --check-only to stop at the counts")

    from training import evaluate as gate

    rows, sentences = build_gold()
    print(
        f"gold: {rows} rows from {sentences} distinct sentences -> {GOLD.name}",
        file=sys.stderr if args.check_only else sys.stdout,
    )
    # Counts first. If no gate cell can be measured, the model is never loaded:
    # inference on 17,942 rows from 9 sentences is n=9 of information.
    checked = gate.main(["--gold", str(GOLD), "--check-gold"])
    if args.check_only:
        return checked
    if checked != 0:
        return 2
    predictions = gate.predict_with_model(
        args.model, GOLD, args.max_length, args.batch_size
    )
    with PREDICTIONS.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, ["item_id", "p_critical", "p_urgent", "p_routine"]
        )
        writer.writeheader()
        writer.writerows(predictions.values())
    print(f"predictions: {len(predictions)} -> {PREDICTIONS.name}")
    return gate.main(
        [
            "--gold",
            str(GOLD),
            "--predictions",
            str(PREDICTIONS),
            "--out",
            str(OUT),
        ]
    )


if __name__ == "__main__":
    raise SystemExit(main())
