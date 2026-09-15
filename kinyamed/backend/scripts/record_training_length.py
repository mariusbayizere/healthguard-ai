"""Record a model's training max_length in its directory, from its own training run record.

The backend serves only at the length a model was trained at, and refuses to start
when it cannot tell (app/services/model_classifier.py). Models trained before that
rule do not record it. This copies the value from the run record the training wrote,
so the number is traceable and never typed in.

    python scripts/record_training_length.py \\
        --model ~/kinyamed-runs/model_v2d_freeze8_lr1e-5 \\
        --run-record ~/kinyamed-runs/last_run_v2d_freeze8_lr1e-5.json

Refuses (exit 2), writing nothing, if the run record lacks args.max_length or the
directory already records a different length.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

TRAINING_METADATA = "kinyamed_training.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--run-record", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        raw = json.loads(args.run_record.read_text())["args"]["max_length"]
        max_length = int(raw)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(
            f"REFUSED: {args.run_record} has no usable args.max_length ({error!r})",
            file=sys.stderr,
        )
        return 2
    target = args.model / TRAINING_METADATA
    if target.exists():
        existing = json.loads(target.read_text()).get("max_length")
        if existing != max_length:
            print(
                f"REFUSED: {target} already records max_length={existing!r}, "
                f"not {max_length}; not overwritten",
                file=sys.stderr,
            )
            return 2
    target.write_text(
        json.dumps(
            {
                "max_length": max_length,
                "source": str(args.run_record),
                "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
            },
            indent=2,
        )
        + "\n"
    )
    print(f"recorded max_length={max_length} in {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
