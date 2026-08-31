#!/usr/bin/env python
"""Re-derive every committed digest from seed 42 and check it still matches.

This is the repository's evidence. A manifest full of SHA-256 digests proves
nothing on its own; it becomes a claim only when the pipeline that produced it
lands on the same bytes again on a different machine. That is what this checks.

Two scopes:

  --scope sample   regenerates the committed 1,000-row sample, re-runs both
                   splits, and compares against dataset/sample/sample_manifest.json.
                   Seconds; this is what CI runs on every push.

  --scope full     regenerates the whole 1M-row corpus, checks it against the
                   source digest in the frozen eval manifests, re-runs both
                   splits and compares train/eval digests byte-for-byte.
                   About a minute, and needs ~1 GB of scratch space.

Standard library only, deliberately: the reproducibility claim must not be able
to break because an upstream package published a new release.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GENERATOR_SEED = 42


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Results:
    def __init__(self) -> None:
        self.checks: list[tuple[str, bool, str]] = []

    def add(self, name: str, ok: bool, detail: str = "") -> bool:
        self.checks.append((name, ok, detail))
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}" + (f"  {detail}" if detail and not ok else ""))
        return ok

    @property
    def failed(self) -> list[tuple[str, bool, str]]:
        return [c for c in self.checks if not c[1]]


def run(args: list[str]) -> None:
    result = subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(
            f"command failed: {' '.join(args)}\n{result.stdout}\n{result.stderr}"
        )


def check_splits(
    source: Path, workdir: Path, expected: dict, results: Results, label: str
) -> None:
    """Re-run both splits from `source` and compare every digest."""
    for strategy in ("phrase", "family"):
        out = workdir / strategy
        out.mkdir(parents=True, exist_ok=True)
        run([
            "dataset/split_dataset.py", "--strategy", strategy,
            "--input", str(source), "--out-dir", str(out),
        ])
        for side in ("train", "eval"):
            produced = out / f"{side}_{strategy}_holdout.csv"
            want = expected[strategy][side]
            got = sha256(produced)
            results.add(
                f"{label} {strategy}/{side} split digest",
                got == want,
                f"expected {want[:16]} got {got[:16]}",
            )


def verify_sample(results: Results) -> None:
    manifest_path = ROOT / "dataset/sample/sample_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    sample = ROOT / manifest["path"]

    results.add(
        "committed sample matches its manifest digest",
        sample.exists() and sha256(sample) == manifest["sha256"],
    )

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        regenerated = work / "regenerated.csv"
        run([
            "dataset/generate_large_dataset.py",
            "--target", str(manifest["target"]),
            "--seed", str(manifest["seed"]),
            "--output", str(regenerated),
        ])
        results.add(
            f"sample regenerates from seed {manifest['seed']}",
            sha256(regenerated) == manifest["sha256"],
        )
        expected = {
            s: {side: manifest["splits"][s][side]["sha256"] for side in ("train", "eval")}
            for s in ("phrase", "family")
        }
        check_splits(sample, work / "splits", expected, results, "sample")


def verify_full(results: Results) -> None:
    manifests = {}
    for strategy in ("phrase", "family"):
        path = ROOT / f"dataset/processed/eval_manifest_{strategy}_v1.json"
        if not path.exists():
            raise SystemExit(
                f"{path} is missing. Run `make dataset` first, or use --scope sample."
            )
        manifests[strategy] = json.loads(path.read_text())

    sources = {m["source"]["sha256"] for m in manifests.values()}
    results.add("both manifests pin the same source corpus", len(sources) == 1)
    expected_source = sources.pop()

    free_gb = shutil.disk_usage(tempfile.gettempdir()).free / 1e9
    if free_gb < 2:
        raise SystemExit(f"needs ~1 GB of scratch space, only {free_gb:.1f} GB free")

    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        corpus = work / "symptoms_large.csv"
        print(f"  regenerating 1,000,000 rows from seed {GENERATOR_SEED} ...")
        run([
            "dataset/generate_large_dataset.py",
            "--target", "1000000", "--seed", str(GENERATOR_SEED),
            "--output", str(corpus),
        ])
        got = sha256(corpus)
        results.add(
            f"corpus regenerates from seed {GENERATOR_SEED}",
            got == expected_source,
            f"expected {expected_source[:16]} got {got[:16]}",
        )
        if got != expected_source:
            print("\n  Splits skipped: they cannot match if the corpus does not.")
            return

        expected = {
            s: {side: manifests[s]["files"][side]["sha256"] for side in ("train", "eval")}
            for s in ("phrase", "family")
        }
        check_splits(corpus, work / "splits", expected, results, "corpus")

    for strategy, manifest in manifests.items():
        on_disk = ROOT / manifest["files"]["eval"]["path"]
        if on_disk.exists():
            results.add(
                f"{strategy} eval file on disk matches its manifest",
                sha256(on_disk) == manifest["files"]["eval"]["sha256"],
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", choices=("sample", "full"), default="sample")
    args = parser.parse_args()

    print(f"Reproducibility check ({args.scope} scope)\n")
    results = Results()
    if args.scope == "sample":
        verify_sample(results)
    else:
        verify_full(results)

    total = len(results.checks)
    failed = results.failed
    print()
    if failed:
        print(f"{len(failed)} of {total} checks FAILED:")
        for name, _, detail in failed:
            print(f"  - {name}: {detail}")
        return 1
    print(f"All {total} checks passed — every committed digest re-derived from seed {GENERATOR_SEED}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
