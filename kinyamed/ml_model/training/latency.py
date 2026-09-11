#!/usr/bin/env python
"""A1 — measure single-row inference latency for a saved model on this machine.

The project document claims sub-200ms. This measures what the machine actually
does and emits macros so the paper quotes the measurement rather than the claim.

WHAT IS MEASURED, AND WHY IT IS SPLIT IN TWO
--------------------------------------------
BATCH 1, because that is the deployment shape. A triage endpoint classifies one
patient's sentence at a time; a batched throughput figure would be a different
and easier number, and quoting it against a per-request latency claim would be
a category error.

COLD is the first inference after the model is loaded, reported separately and
as a single observation rather than a distribution. It absorbs lazy allocator
and kernel warm-up and is not repeatable within a process, so a median of cold
starts would require reloading the model per sample.

WARM is the steady state, reported as median and p95 over the sample. p95
rather than mean: latency distributions here are right-skewed by scheduler
preemption on a 2-core machine, and a mean hides exactly the tail a queue
cares about.

The rows are drawn from the frozen evaluation split so the text length
distribution is the real one. Token length drives cost, and a synthetic string
would measure the wrong thing.

    python training/latency.py --model ~/kinyamed-runs/model_v2d_freeze8_lr1e-5 \
        --manifest dataset/processed/eval_manifest_phrase_v2.json --rows 1000
"""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dataset.atomicio import atomic_write


def machine() -> dict[str, str]:
    """What produced the numbers. A latency figure without a machine is noise."""
    model_name = ""
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                model_name = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
    import torch

    return {
        "cpu": model_name or platform.processor() or "unknown",
        "cores_available": str(len(__import__("os").sched_getaffinity(0))),
        "torch": torch.__version__,
        "torch_threads": str(torch.get_num_threads()),
        "python": platform.python_version(),
        "platform": platform.platform(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--model", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--rows", type=int, default=1000)
    ap.add_argument("--max-length", type=int, default=96)
    ap.add_argument(
        "--threads",
        type=int,
        default=None,
        help="Pin torch threads. Recorded in the output either way.",
    )
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=Path("training/latency_v2d.json"))
    args = ap.parse_args()

    import pandas as pd
    import torch
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    if args.threads:
        torch.set_num_threads(args.threads)

    manifest = json.loads(args.manifest.read_text())
    frame = pd.read_csv(manifest["files"]["eval"]["path"])
    texts = (
        frame["text"]
        .sample(n=min(args.rows, len(frame)), random_state=args.seed)
        .tolist()
    )

    tok_dir = args.model / "tokenizer"
    tokenizer = AutoTokenizer.from_pretrained(
        str(tok_dir if tok_dir.exists() else args.model)
    )
    model = AutoModelForSequenceClassification.from_pretrained(str(args.model))
    model.eval()

    lengths = [len(tokenizer(t)["input_ids"]) for t in texts]

    def once(text: str) -> float:
        """One end-to-end request: tokenise, forward, argmax. Wall clock."""
        start = time.perf_counter()
        with torch.no_grad():
            encoded = tokenizer(
                text, return_tensors="pt", truncation=True, max_length=args.max_length
            )
            logits = model(**encoded).logits
            int(logits.argmax(dim=-1).item())
        return (time.perf_counter() - start) * 1000.0

    # COLD: the first request this process ever serves. One observation, and it
    # is reported as one -- repeating it inside a warm process would not be cold.
    cold_ms = once(texts[0])

    # A short warm-up that is NOT counted, so the reported distribution is the
    # steady state rather than a mixture of it and the allocator settling.
    for text in texts[:20]:
        once(text)

    warm = [once(t) for t in texts]
    warm_sorted = sorted(warm)

    def pct(p: float) -> float:
        # Nearest-rank, stated because percentile conventions differ and a p95
        # computed two ways can differ by a millisecond at this sample size.
        k = max(1, round(p / 100.0 * len(warm_sorted)))
        return warm_sorted[k - 1]

    result = {
        "generated_at": datetime.now(UTC).isoformat(),
        "model": str(args.model),
        "model_name": args.model.name,
        "manifest": str(args.manifest),
        "rows": len(warm),
        "batch_size": 1,
        "max_length": args.max_length,
        "seed": args.seed,
        "machine": machine(),
        "token_length": {
            "min": min(lengths),
            "median": int(statistics.median(lengths)),
            "p95": sorted(lengths)[max(0, round(0.95 * len(lengths)) - 1)],
            "max": max(lengths),
        },
        "cold_ms": round(cold_ms, 2),
        "warm_ms": {
            "min": round(warm_sorted[0], 2),
            "median": round(statistics.median(warm), 2),
            "mean": round(statistics.fmean(warm), 2),
            "p95": round(pct(95), 2),
            "p99": round(pct(99), 2),
            "max": round(warm_sorted[-1], 2),
        },
        "percentile_method": "nearest-rank",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with atomic_write(args.out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)

    m, w = result["machine"], result["warm_ms"]
    print(f"model      : {args.model.name}")
    print(f"machine    : {m['cpu']}")
    print(
        f"             {m['cores_available']} cores available, "
        f"torch {m['torch']} using {m['torch_threads']} threads"
    )
    print(f"rows       : {result['rows']:,} at batch 1, max_length {args.max_length}")
    print(
        f"tokens     : median {result['token_length']['median']}, "
        f"p95 {result['token_length']['p95']}, max {result['token_length']['max']}"
    )
    print()
    print(f"  COLD (first request, n=1) : {result['cold_ms']:8.2f} ms")
    print(f"  WARM median               : {w['median']:8.2f} ms")
    print(f"  WARM p95                  : {w['p95']:8.2f} ms")
    print(f"  WARM p99                  : {w['p99']:8.2f} ms")
    print(f"  WARM min / max            : {w['min']:8.2f} / {w['max']:.2f} ms")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
