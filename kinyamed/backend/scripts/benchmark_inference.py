"""Latency and memory of the served classifier, before and after micro-batching (item 5b).

Label-independent: it measures time and memory, never accuracy. It runs the
backend's own `ModelClassifier` in-process on real corpus texts. "Serialised"
is the same engine with max_batch_size=1: one worker, one forward pass at a
time, which is exactly what the removed lock did.

    cd kinyamed/backend
    python scripts/benchmark_inference.py --model ~/kinyamed-runs/model_v2d_freeze8_lr1e-5 \\
        --out ../reports/measurements/inference_benchmark

Outputs, per batch size:
  results.json                      every figure, the machine, and memory state per level
  latency_batch<B>.json             gate 14 input for training/evaluate.py (samples_ms, machine)
  memory_batch<B>.json              gate 15 input (peak_rss_mb at concurrency 50)

THE MACHINE IS NOT THE TARGET. No target CPU has been named (STATE.md H15), so
the gate will not accept these as MET whatever they show.
"""

from __future__ import annotations

import argparse
import csv
import json
import platform
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Protocol

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT.parent / "ml_model" / "dataset" / "processed" / "eval_phrase_holdout.csv"
GATE_MINIMUM_SAMPLES = 1000  # EVAL_SET_SPEC gate 14: timed requests
BOOTSTRAP = 1000


class Classifier(Protocol):
    def classify(self, text: str) -> object: ...


def run_level(
    classifier: Classifier, texts: list[str], *, concurrency: int, requests: int
) -> tuple[list[float], float]:
    """Closed loop: `concurrency` callers, each sending its next request as soon as
    the previous one returns, until `requests` have completed. Latency per request in ms."""
    counter = iter(range(requests))
    counter_lock = threading.Lock()
    samples: list[float] = []
    samples_lock = threading.Lock()

    def caller() -> None:
        while True:
            with counter_lock:
                k = next(counter, None)
            if k is None:
                return
            start = time.perf_counter()
            classifier.classify(texts[k % len(texts)])
            elapsed = (time.perf_counter() - start) * 1000.0
            with samples_lock:
                samples.append(elapsed)

    wall = time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        for future in [pool.submit(caller) for _ in range(concurrency)]:
            future.result()
    return samples, time.perf_counter() - wall


def _nearest_rank(values: list[float], q: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(-(-q * len(ordered) // 1)) - 1))
    return ordered[index]


def summarise(samples: list[float], seed: int = 20260915) -> dict[str, Any]:
    """Nearest-rank p50/p95/p99, each with a 95% bootstrap interval over requests."""
    rng = random.Random(seed)
    out: dict[str, Any] = {
        "n": len(samples),
        "gate_minimum_met": len(samples) >= GATE_MINIMUM_SAMPLES,
    }
    for name, q in (("p50", 0.50), ("p95", 0.95), ("p99", 0.99)):
        estimates = sorted(
            _nearest_rank([rng.choice(samples) for _ in samples], q)
            for _ in range(BOOTSTRAP)
        )
        out[name] = (
            _nearest_rank(samples, q),
            estimates[int(0.025 * BOOTSTRAP)],
            estimates[int(0.975 * BOOTSTRAP) - 1],
        )
    return out


def equivalence(
    single: list[list[float]], batched: list[list[float]]
) -> dict[str, Any]:
    """Padding must not change what the model says. Any argmax change is a defect."""
    disagreements = sum(
        max(range(len(a)), key=a.__getitem__) != max(range(len(b)), key=b.__getitem__)
        for a, b in zip(single, batched, strict=True)
    )
    largest = max(
        abs(x - y)
        for a, b in zip(single, batched, strict=True)
        for x, y in zip(a, b, strict=True)
    )
    return {
        "texts": len(single),
        "argmax_disagreements": disagreements,
        "max_abs_probability_difference": largest,
    }


def _machine() -> dict[str, Any]:
    info: dict[str, Any] = {
        "platform": platform.platform(),
        "python": platform.python_version(),
    }
    try:
        cpuinfo = Path("/proc/cpuinfo").read_text()
        info["cpu"] = next(
            line.split(":", 1)[1].strip()
            for line in cpuinfo.splitlines()
            if line.startswith("model name")
        )
        info["logical_cpus"] = sum(
            1 for line in cpuinfo.splitlines() if line.startswith("processor")
        )
    except (OSError, StopIteration):
        info["cpu"] = "unrecorded"
    return info


def _memory_state() -> dict[str, int]:
    fields = {}
    for line in Path("/proc/meminfo").read_text().splitlines():
        key, value = line.split(":", 1)
        if key in ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree"):
            fields[key] = int(value.split()[0]) // 1024
    return {
        "mem_total_mb": fields["MemTotal"],
        "mem_available_mb": fields["MemAvailable"],
        "swap_used_mb": fields["SwapTotal"] - fields["SwapFree"],
    }


class _PeakRss:
    """Samples this process's resident memory every 50 ms."""

    def __init__(self) -> None:
        self.peak_mb = 0.0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop.is_set():
            for line in Path("/proc/self/status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    self.peak_mb = max(self.peak_mb, int(line.split()[1]) / 1024)
            self._stop.wait(0.05)

    def __enter__(self) -> _PeakRss:
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self._stop.set()
        self._thread.join()


def _texts(limit: int, seed: int) -> list[str]:
    with CORPUS.open(encoding="utf-8", newline="") as handle:
        rows = [r["text"] for r in csv.DictReader(handle)]
    random.Random(seed).shuffle(rows)
    return rows[:limit]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument(
        "--max-length",
        type=int,
        default=None,
        help="defaults to the length the model directory records it was trained at",
    )
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=[1, 16])
    parser.add_argument("--concurrency", type=int, nargs="+", default=[1, 10, 50])
    parser.add_argument("--requests", type=int, default=GATE_MINIMUM_SAMPLES)
    parser.add_argument("--texts", type=int, default=1000)
    parser.add_argument("--equivalence-texts", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)

    sys.path.insert(0, str(ROOT))
    from app.services.model_classifier import (
        BatchedInference,
        ModelClassifier,
        resolve_max_length,
    )

    args.max_length = resolve_max_length(args.model, args.max_length)

    args.out.mkdir(parents=True, exist_ok=True)
    texts = _texts(args.texts, args.seed)
    report: dict[str, Any] = {
        "model": str(args.model),
        "max_length": args.max_length,
        "torch_threads": args.threads,
        "machine": _machine(),
        "target_hardware": "NOT NAMED (STATE.md H15); these are not target-hardware measurements",
        "memory_before_load": _memory_state(),
        "texts": {
            "source": str(CORPUS.relative_to(ROOT.parent)),
            "count": len(texts),
            "seed": args.seed,
        },
        "runs": {},
    }

    with _PeakRss() as load_rss:
        start = time.perf_counter()
        classifier = ModelClassifier(
            args.model, max_length=args.max_length, threads=args.threads
        )
        load_s = time.perf_counter() - start
        start = time.perf_counter()
        classifier.classify(texts[0])
        first_ms = (time.perf_counter() - start) * 1000.0
    report["cold_start"] = {
        "model_load_s": round(load_s, 2),
        "first_inference_ms": round(first_ms, 1),
        "peak_rss_mb": round(load_rss.peak_mb),
    }
    print(
        f"cold start: load {load_s:.1f} s, first inference {first_ms:.0f} ms",
        flush=True,
    )

    eq = texts[: args.equivalence_texts]
    single = [list(classifier._forward_batch([t])[0]) for t in eq]
    batched: list[list[float]] = []
    for k in range(0, len(eq), 16):
        batched += [list(p) for p in classifier._forward_batch(eq[k : k + 16])]
    report["equivalence"] = equivalence(single, batched)
    print(f"equivalence: {report['equivalence']}", flush=True)

    for batch_size in args.batch_sizes:
        classifier._engine.close()
        classifier._engine = BatchedInference(
            classifier._forward_batch,
            max_batch_size=batch_size,
            max_wait_ms=5,
            timeout_s=600,
        )
        run: dict[str, Any] = {}
        for concurrency in args.concurrency:
            memory_before = _memory_state()
            with _PeakRss() as rss:
                samples, wall_s = run_level(
                    classifier, texts, concurrency=concurrency, requests=args.requests
                )
            summary = summarise(samples)
            run[str(concurrency)] = {
                **summary,
                "throughput_rps": round(len(samples) / wall_s, 2),
                "peak_rss_mb": round(rss.peak_mb),
                "memory_before": memory_before,
                "memory_after": _memory_state(),
            }
            p50, p95, p99 = summary["p50"], summary["p95"], summary["p99"]
            print(
                f"batch {batch_size:>2} c={concurrency:>2}: p50 {p50[0]:.0f} [{p50[1]:.0f}, {p50[2]:.0f}] "
                f"p95 {p95[0]:.0f} [{p95[1]:.0f}, {p95[2]:.0f}] p99 {p99[0]:.0f} ms, "
                f"{run[str(concurrency)]['throughput_rps']} req/s, peak RSS {rss.peak_mb:.0f} MB",
                flush=True,
            )
            if concurrency == 1:
                (args.out / f"latency_batch{batch_size}.json").write_text(
                    json.dumps(
                        {"machine": report["machine"], "samples_ms": samples}, indent=1
                    )
                )
            if concurrency == 50:
                (args.out / f"memory_batch{batch_size}.json").write_text(
                    json.dumps(
                        {
                            "machine": report["machine"],
                            "peak_rss_mb": rss.peak_mb,
                            "concurrency": 50,
                        },
                        indent=1,
                    )
                )
        report["runs"][f"batch_{batch_size}"] = run
        (args.out / "results.json").write_text(json.dumps(report, indent=2))
    classifier._engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
