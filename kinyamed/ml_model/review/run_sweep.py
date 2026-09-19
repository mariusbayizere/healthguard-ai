"""Run the seeds-vs-rows sweep arms sequentially, and survive a reboot.

LOGS AND REPORTS LIVE OUTSIDE /tmp. This machine has lost two long runs to
reboots that cleared /tmp, taking the log with them, so there was nothing left
to diagnose. Everything lands in ~/kinyamed-sweep, which survives.

RESUMABLE BY DESIGN. An arm whose report already exists is skipped, so a
reboot costs the arm in flight and nothing else. The check is the report file,
not a marker, because a report that exists is an arm that finished.

IT RUNS ARMS ONE AT A TIME. Two training runs on four cores contend for memory
and neither finishes sooner; the previous regeneration on this machine dropped
from 640 to 192 rows a minute when something else competed.

COLLAPSE IS A RESULT, NOT AN ERROR. An arm that predicts a single class for
every row has not failed to run; it has told us the task was not learnable from
what it was given. The runner detects it from the report's confusion matrix and
says which class, because "it collapsed" without the class is half a finding.

Usage:
    python review/run_sweep.py             # run every arm not yet done
    python review/run_sweep.py --status    # what is done, what collapsed
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SWEEP = ROOT / "dataset" / "sweep"
OUT = Path.home() / "kinyamed-sweep"
TRAINER = ROOT / "training" / "train_holdout.py"

CLASSES = ("CRITICAL", "URGENT", "ROUTINE")


def arms() -> list[Path]:
    """Manifests in the order the sweep should report: by seed count, then replicate."""
    return sorted(
        SWEEP.glob("manifest_*.json"),
        key=lambda p: json.loads(p.read_text(encoding="utf-8"))["sweep"]["arm"],
    )


def report_path(name: str) -> Path:
    return OUT / f"report_{name}.json"


def collapsed(report: dict) -> str | None:
    """The single class an arm predicted, or None. Read from the confusion matrix.

    A row of the matrix is a truth class; a column is a prediction. If every
    prediction falls in one column, the model answered one class for everything.
    """
    # metrics.confusion_matrix, NOT a top-level "confusion". The first draft of
    # this function read the wrong key and would have reported no collapse ever,
    # which is the blind-checker failure this project has already hit once.
    matrix = (report.get("metrics") or {}).get("confusion_matrix")
    if not matrix:
        raise KeyError(
            "the run report carries no metrics.confusion_matrix, so collapse "
            "cannot be detected. Refusing to report 'no collapse' from a matrix "
            "that was never read."
        )
    columns = [sum(row[i] for row in matrix) for i in range(len(matrix[0]))]
    non_empty = [i for i, total in enumerate(columns) if total]
    if len(non_empty) == 1:
        return CLASSES[non_empty[0]] if non_empty[0] < len(CLASSES) else "?"
    return None


def run_arm(manifest_path: Path) -> tuple[str, float, bool]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sweep, config = manifest["sweep"], manifest["sweep"]["run_config"]
    name = sweep["arm"]
    report = report_path(name)
    if report.exists():
        return name, 0.0, True

    OUT.mkdir(parents=True, exist_ok=True)
    log = OUT / f"log_{name}.log"
    command = [
        sys.executable,
        str(TRAINER.relative_to(ROOT)),
        "--manifest",
        str(manifest_path.relative_to(ROOT)),
        "--freeze-layers",
        str(config["freeze_layers"]),
        "--learning-rate",
        str(config["learning_rate"]),
        "--batch-size",
        str(config["batch_size"]),
        "--max-length",
        str(config["max_length"]),
        "--threads",
        str(config["threads"]),
        "--epochs",
        str(config["epochs"]),
        "--stop-groups",
        str(config["stop_groups"]),
        "--seed",
        str(sweep["rng_seed"]),
        "--no-save",
        "--report",
        str(report),
    ]
    started = time.time()
    with log.open("w", encoding="utf-8") as handle:
        handle.write(" ".join(command) + "\n\n")
        handle.flush()
        result = subprocess.run(command, cwd=ROOT, stdout=handle, stderr=handle)
    return name, time.time() - started, result.returncode == 0


def summarise() -> None:
    print(
        "Labels: single non-clinician annotator, no second rater, no "
        "inter-rater agreement. Not clinical ground truth.\n"
    )
    print(f"  {'arm':18} {'seeds':>5} {'status':>10}  {'macro F1':>8}  note")
    for path in arms():
        manifest = json.loads(path.read_text(encoding="utf-8"))
        sweep = manifest["sweep"]
        report = report_path(sweep["arm"])
        if not report.exists():
            print(f"  {sweep['arm']:18} {sweep['distinct_seeds']:5} {'pending':>10}")
            continue
        data = json.loads(report.read_text(encoding="utf-8"))
        macro = data.get("metrics", {}).get("macro_f1")
        one = collapsed(data)
        note = f"COLLAPSED to {one}" if one else ""
        macro_text = f"{macro:.4f}" if isinstance(macro, (int, float)) else "n/a"
        print(
            f"  {sweep['arm']:18} {sweep['distinct_seeds']:5} {'done':>10}  "
            f"{macro_text:>8}  {note}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--status", action="store_true")
    args = parser.parse_args()

    if args.status:
        summarise()
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    for path in arms():
        name, seconds, ok = run_arm(path)
        report = report_path(name)
        if seconds == 0.0:
            print(f"  {name}: already done, skipped", flush=True)
            continue
        state = "ok" if ok else "FAILED"
        note = ""
        if report.exists():
            one = collapsed(json.loads(report.read_text(encoding="utf-8")))
            if one:
                note = f"  COLLAPSED to {one}"
        print(f"  {name}: {state} in {seconds / 60:.1f} min{note}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
