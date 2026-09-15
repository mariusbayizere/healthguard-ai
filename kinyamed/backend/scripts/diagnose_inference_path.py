"""Is the micro-batching engine slow, or is the machine? (item 5b root cause)

Same process, same model, same texts, interleaved: a direct forward pass on the
main thread against the same request through `BatchedInference` at batch 1. If
the two agree, any latency beyond the repository's older record is the machine's
state (load, swap), not the engine.

    cd kinyamed/backend
    python scripts/diagnose_inference_path.py --model ~/kinyamed-runs/model_v2d_freeze8_lr1e-5
"""

from __future__ import annotations

import argparse
import csv
import random
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT.parent / "ml_model" / "dataset" / "processed" / "eval_phrase_holdout.csv"


def _nearest_rank(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[max(0, int(-(-q * len(ordered) // 1)) - 1)]


def _memory() -> str:
    fields: dict[str, int] = {}
    with Path("/proc/meminfo").open() as handle:
        for line in handle:
            key, value = line.split(":", 1)
            fields[key] = int(value.split()[0]) // 1024
    swap = fields["SwapTotal"] - fields["SwapFree"]
    return f"MemAvailable {fields['MemAvailable']} MB, swap used {swap} MB"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--requests", type=int, default=300)
    parser.add_argument("--max-length", type=int, default=None)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args(argv)

    sys.path.insert(0, str(ROOT))
    import torch
    from app.services.model_classifier import ModelClassifier, resolve_max_length

    args.max_length = resolve_max_length(args.model, args.max_length)

    with CORPUS.open(encoding="utf-8", newline="") as handle:
        texts = [row["text"] for row in csv.DictReader(handle)]
    random.Random(42).shuffle(texts)
    texts = texts[: args.requests]

    classifier = ModelClassifier(
        args.model, max_length=args.max_length, threads=args.threads
    )
    for text in texts[:20]:
        classifier.classify(text)  # warm

    direct: list[float] = []
    engine: list[float] = []
    for text in texts:
        start = time.perf_counter()
        classifier._forward_batch([text])
        direct.append((time.perf_counter() - start) * 1000.0)
        start = time.perf_counter()
        classifier.classify(text)
        engine.append((time.perf_counter() - start) * 1000.0)

    for name, values in (
        ("direct forward (main thread)", direct),
        ("through engine, batch 1", engine),
    ):
        print(
            f"{name}: p50 {_nearest_rank(values, 0.5):.0f} ms, "
            f"p95 {_nearest_rank(values, 0.95):.0f} ms, "
            f"mean {statistics.mean(values):.0f} ms, n={len(values)}"
        )
    print(f"torch threads {torch.get_num_threads()}; {_memory()}")
    with Path("/proc/loadavg").open() as handle:
        print(f"load average {handle.read().split()[:3]}")
    classifier._engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
