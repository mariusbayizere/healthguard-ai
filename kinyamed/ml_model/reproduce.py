#!/usr/bin/env python
"""`make reproduce`: re-derive every committed result that needs no network and no model
weights, from a clean clone, with one command (CLAUDE.md §14).

Each step either must exit with a stated code (a refusal must still refuse: exit 2) or
must print exactly the committed output file. Any difference fails the run and names
the first line that differs.

The phrase-v2 corpus and split are rebuilt in a temporary directory and only the two
CSVs, after their digests match the frozen manifest, are moved into
dataset/processed/. The splitter also rewrites a tracked JSON report, so it is never
pointed at the working tree. If both CSVs are already present with the frozen
digests they are left alone.

What is not covered, and why, is printed at the end (NOT_REPRODUCED).

STEP 0, BEFORE ANYTHING RUNS: the interpreter must be Python 3.11 (pinned in the
repository's `.python-version`), every package in `requirements-reproduce.lock` must be
installed at exactly its locked version, and the modules the steps import must import.
Any failure names what is wrong and runs nothing. A reviewer on a fresh machine runs
`make reproduce-env` once (a venv built from the lock), then `make reproduce`.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import partial
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parent
KINYAMED = ML_ROOT.parent
MEASUREMENTS = KINYAMED / "reports" / "measurements"
PY = sys.executable
PHRASE_V2_MANIFEST = ML_ROOT / "dataset/processed/eval_manifest_phrase_v2.json"

REQUIRED_PYTHON: tuple[int, int] = (3, 11)
LOCK_FILE = ML_ROOT / "requirements-reproduce.lock"

# Imported by the steps (pandas: the n=9 gold builder; numpy: the gate; torch: the
# pipeline's cost matrix). Checked before anything runs, so a wrong interpreter fails in
# a second, not after the corpus regeneration.
REQUIRED_MODULES: tuple[str, ...] = ("numpy", "pandas", "torch")

NOT_REPRODUCED: tuple[tuple[str, str], ...] = (
    (
        "tokenizer study (reports/TOKENIZER_STUDY.md)",
        "downloads tokenizers from the Hugging Face Hub (network). Command: "
        "cd kinyamed/ml_model && python training/tokenizer_study.py --out "
        "../reports/measurements/tokenizer_study --only <repo>, then --render",
    ),
    (
        "inference latency and memory (reports/MODEL_AUDIT.md §3.3)",
        "needs the v2d model weights, which are not in the repository (H16), and is "
        "machine-specific: no latency number is a gate result off the target CPU (H15). "
        "Command: backend/scripts/benchmark_inference.py",
    ),
    (
        "triage wording inventory (reports/measurements/triage_wording_inventory.txt)",
        "an inventory of the working tree at one moment, including the git-ignored "
        "CLAUDE.md; it changes with every edit and is not a result",
    ),
    (
        "any model quality metric",
        "there is no evaluation set that meets EVAL_SET_SPEC; the gate and the "
        "pipeline refuse, and those refusals are reproduced above",
    ),
)


@dataclass(frozen=True)
class Step:
    name: str
    command: list[str]
    cwd: Path
    expected_exit: int = 0
    compare_to: Path | None = None
    stream: str = "stdout"
    timeout: int = 3600


@dataclass(frozen=True)
class Result:
    ok: bool
    detail: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def matches_digest(path: Path, digest: str) -> bool:
    return Path(path).is_file() and sha256(path) == digest


def _first_difference(got: str, want: str) -> str:
    got_lines, want_lines = got.splitlines(), want.splitlines()
    for number, (g, w) in enumerate(zip(got_lines, want_lines, strict=False), start=1):
        if g != w:
            return f"line {number}: got {g!r}, committed {w!r}"
    return (
        f"line {min(len(got_lines), len(want_lines)) + 1}: "
        f"got {len(got_lines)} lines, committed {len(want_lines)}"
    )


def run_step(step: Step) -> Result:
    try:
        completed = subprocess.run(
            step.command,
            cwd=step.cwd,
            capture_output=True,
            text=True,
            timeout=step.timeout,
        )
    except subprocess.TimeoutExpired:
        return Result(False, f"timed out after {step.timeout}s")
    if completed.returncode != step.expected_exit:
        tail = (completed.stderr or completed.stdout).strip().splitlines()[-5:]
        return Result(
            False,
            f"exit {completed.returncode}, expected {step.expected_exit}\n    "
            + "\n    ".join(tail),
        )
    if step.compare_to is not None:
        got = completed.stdout if step.stream == "stdout" else completed.stderr
        want = step.compare_to.read_text(encoding="utf-8")
        if got != want:
            return Result(
                False,
                f"differs from {step.compare_to.name}: {_first_difference(got, want)}",
            )
        return Result(True, f"identical to {step.compare_to.name}")
    return Result(True, f"exit {completed.returncode}")


def ensure_phrase_v2_split() -> Result:
    """Put the frozen phrase-v2 train and eval CSVs in dataset/processed/, verified."""
    manifest = json.loads(PHRASE_V2_MANIFEST.read_text(encoding="utf-8"))
    files = {side: manifest["files"][side] for side in ("train", "eval")}
    if all(matches_digest(ML_ROOT / f["path"], f["sha256"]) for f in files.values()):
        return Result(True, "already present with the frozen digests")
    with tempfile.TemporaryDirectory(prefix="kinyamed-reproduce-") as tmp:
        work = Path(tmp)
        corpus = work / "symptoms_large.csv"
        for step in (
            Step(
                "generate v2 corpus",
                [
                    PY,
                    "dataset/generate_large_dataset.py",
                    "--seed",
                    str(manifest["generator_seed"]),
                    "--corpus-version",
                    "2",
                    "--output",
                    str(corpus),
                ],
                ML_ROOT,
            ),
            Step(
                "split phrase",
                [
                    PY,
                    "dataset/split_dataset.py",
                    "--strategy",
                    "phrase",
                    "--input",
                    str(corpus),
                    "--out-dir",
                    str(work / "split"),
                    "--corpus-version",
                    "2",
                    "--seed",
                    str(manifest["split_seed"]),
                ],
                ML_ROOT,
            ),
        ):
            result = run_step(step)
            if not result.ok:
                return Result(False, f"{step.name}: {result.detail}")
        if sha256(corpus) != manifest["source"]["sha256"]:
            return Result(
                False, "the regenerated corpus does not match the frozen manifest"
            )
        for side, entry in files.items():
            produced = work / "split" / f"{side}_phrase_holdout.csv"
            if sha256(produced) != entry["sha256"]:
                return Result(
                    False, f"the regenerated {side} split does not match the manifest"
                )
            destination = ML_ROOT / entry["path"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(produced), destination)
    return Result(True, "regenerated from seed and matched the frozen digests")


def steps(pipeline_out: Path | None = None) -> list[Step]:
    pipeline_out = (
        pipeline_out or Path(tempfile.gettempdir()) / "kinyamed-reproduce-pipeline"
    )
    return [
        Step(
            "committed 1,000-row sample and its splits",
            [PY, "verify.py", "--scope", "sample"],
            ML_ROOT,
        ),
        Step(
            "evaluation-set minimums (power calculations)",
            [PY, "training/eval_spec.py", "--verify"],
            ML_ROOT,
        ),
        Step(
            "arithmetic path to a 1M corpus",
            [PY, "reports/measurements/corpus_1m_arithmetic.py"],
            KINYAMED,
            compare_to=MEASUREMENTS / "corpus_1m_arithmetic.txt",
        ),
        Step(
            "both frozen corpora and all split digests from seed 42",
            [PY, "verify.py", "--scope", "full"],
            ML_ROOT,
        ),
        Step(
            "grammatical person of the v2 corpus",
            [PY, "../reports/measurements/grammatical_person.py"],
            ML_ROOT,
            compare_to=MEASUREMENTS / "grammatical_person.txt",
        ),
        Step(
            "gate --check-gold on the n=9 set",
            [PY, "scripts/gate_on_current_holdout.py", "--check-only"],
            ML_ROOT,
            expected_exit=2,
            compare_to=MEASUREMENTS / "gate_n9_check_gold.txt",
        ),
        Step(
            "training pipeline on the n=9 set",
            [
                PY,
                "-m",
                "training.pipeline",
                "--train",
                "dataset/processed/train_phrase_holdout.csv",
                "--gold-test",
                "dataset/processed/gate_n9_gold.csv",
                "--gold-calibration",
                "dataset/processed/gold_calibration.csv",
                "--config",
                "training/configs/pipeline_default.json",
                "--seed",
                "42",
                "--out",
                str(pipeline_out),
            ],
            ML_ROOT,
            expected_exit=2,
            compare_to=MEASUREMENTS / "pipeline_n9_refusal.txt",
            stream="stderr",
        ),
    ]


def _normalise(name: str) -> str:
    return name.strip().lower().replace("_", "-")


def read_lock(path: Path) -> dict[str, str]:
    """name -> version for every `name==version` line; comments and pip options skipped."""
    pins = {}
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        name, _, version = line.partition("==")
        pins[_normalise(name)] = version.strip()
    return pins


def _installed_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def dependency_mismatches(
    locked: dict[str, str],
    installed: Callable[[str], str | None] | None = None,
) -> list[str]:
    lookup = installed or _installed_version
    problems = []
    for name, version in locked.items():
        found = lookup(name)
        if found is None:
            problems.append(f"{name} not installed, {version} locked")
        elif found != version:
            problems.append(f"{name} {found} installed, {version} locked")
    return problems


def python_version_problem(version: Sequence[int]) -> str | None:
    if tuple(version[:2]) == REQUIRED_PYTHON:
        return None
    major, minor = REQUIRED_PYTHON
    found = ".".join(str(v) for v in version[:3])
    return (
        f"Python {major}.{minor} is required (repository .python-version); {PY} is "
        f"Python {found}."
    )


def preflight() -> list[str]:
    """Step 0. Everything that would make a later step fail for a reason other than code."""
    problem = python_version_problem(sys.version_info)
    if problem:
        return [problem]
    problems = dependency_mismatches(read_lock(LOCK_FILE))
    problems += [f"cannot import {name}" for name in missing_modules(REQUIRED_MODULES)]
    return problems


def missing_modules(names: Sequence[str]) -> list[str]:
    return [name for name in names if importlib.util.find_spec(name) is None]


def main() -> int:
    problems = preflight()
    if problems:
        print("[0] environment ... FAIL. Nothing was run.")
        for problem in problems:
            print(f"    {problem}")
        print(
            "    Build the pinned environment first: make reproduce-env "
            "(Python 3.11 plus requirements-reproduce.lock), then make reproduce.\n"
            "    Or install the lock into your own Python 3.11 (make install uses the "
            "same pins) and run: make reproduce REPRO_PY=/path/to/python"
        )
        return 1
    print(
        f"[0] environment ... PASS: Python {sys.version.split()[0]}, lock matched, imports ok"
    )
    failures = 0
    with tempfile.TemporaryDirectory(prefix="kinyamed-reproduce-run-") as tmp:
        plan = steps(pipeline_out=Path(tmp) / "pipeline")
        actions: list[tuple[str, Callable[[], Result]]] = [
            (s.name, partial(run_step, s)) for s in plan
        ]
        actions.insert(
            4, ("frozen phrase-v2 split in dataset/processed", ensure_phrase_v2_split)
        )
        for number, (name, action) in enumerate(actions, start=1):
            print(f"[{number}/{len(actions)}] {name} ...", flush=True)
            result = action()
            print(f"    {'PASS' if result.ok else 'FAIL'}: {result.detail}", flush=True)
            failures += not result.ok
    print()
    print("NOT REPRODUCED by this target:")
    for item, reason in NOT_REPRODUCED:
        print(f"  - {item}: {reason}")
    print()
    if failures:
        print(f"{failures} step(s) FAILED.")
        return 1
    print(f"All {len(actions)} steps reproduced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
