"""Reproducibility of the corpus and the splits.

These are the tests that make the frozen manifests meaningful: a digest is only
evidence if the pipeline that produced it lands on the same bytes again.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Use the production digest function, so the tests exercise the same code
# path that writes the manifests rather than a copy of it.
from dataset.freeze_eval import sha256


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    result = subprocess.run(
        [sys.executable, *args], cwd=cwd, capture_output=True, text=True
    )
    assert result.returncode == 0, f"{args} failed:\n{result.stdout}\n{result.stderr}"
    return result


def test_committed_sample_matches_its_manifest(sample_csv: Path, sample_manifest: dict) -> None:
    """The sample is committed evidence; it must not drift silently."""
    assert sha256(sample_csv) == sample_manifest["sha256"]
    assert sample_manifest["rows"] == 1000


def test_sample_regenerates_from_seed(ml_root: Path, sample_manifest: dict, tmp_path: Path) -> None:
    """Seed 42 must reproduce the committed sample byte-for-byte."""
    out = tmp_path / "regen.csv"
    run(
        ["dataset/generate_large_dataset.py", "--target", str(sample_manifest["target"]),
         "--seed", str(sample_manifest["seed"]), "--output", str(out)],
        cwd=ml_root,
    )
    assert sha256(out) == sample_manifest["sha256"], (
        "regenerating from the recorded seed did not reproduce the committed sample"
    )


@pytest.mark.parametrize("strategy", ["phrase", "family"])
def test_sample_split_matches_recorded_digests(
    strategy: str, ml_root: Path, sample_csv: Path, sample_manifest: dict, tmp_path: Path
) -> None:
    """Splitting the sample must land on the digests recorded at commit time."""
    run(
        ["dataset/split_dataset.py", "--strategy", strategy,
         "--input", str(sample_csv), "--out-dir", str(tmp_path)],
        cwd=ml_root,
    )
    expected = sample_manifest["splits"][strategy]
    for side in ("train", "eval"):
        produced = tmp_path / f"{side}_{strategy}_holdout.csv"
        assert sha256(produced) == expected[side]["sha256"], (
            f"{strategy}/{side} split drifted from the recorded digest"
        )


def test_split_is_stable_across_runs(ml_root: Path, sample_csv: Path, tmp_path: Path) -> None:
    """Two independent runs must agree — catches nondeterminism the recorded
    digests would not, such as a dict-ordering dependency introduced later."""
    first, second = tmp_path / "a", tmp_path / "b"
    for out in (first, second):
        out.mkdir()
        run(
            ["dataset/split_dataset.py", "--strategy", "phrase",
             "--input", str(sample_csv), "--out-dir", str(out)],
            cwd=ml_root,
        )
    for side in ("train", "eval"):
        name = f"{side}_phrase_holdout.csv"
        assert sha256(first / name) == sha256(second / name)


def test_worker_count_does_not_change_the_output(
    ml_root: Path, sample_csv: Path, tmp_path: Path
) -> None:
    """Parallel attribution must not affect the result, only the wall clock."""
    serial, parallel = tmp_path / "w1", tmp_path / "w2"
    for out, workers in ((serial, "1"), (parallel, "2")):
        out.mkdir()
        run(
            ["dataset/split_dataset.py", "--strategy", "phrase", "--workers", workers,
             "--input", str(sample_csv), "--out-dir", str(out)],
            cwd=ml_root,
        )
    for side in ("train", "eval"):
        name = f"{side}_phrase_holdout.csv"
        assert sha256(serial / name) == sha256(parallel / name)


def test_split_resumes_from_its_checkpoint(ml_root: Path, sample_csv: Path, tmp_path: Path) -> None:
    """A second run reuses the scan checkpoint and still produces the same bytes."""
    run(
        ["dataset/split_dataset.py", "--strategy", "phrase",
         "--input", str(sample_csv), "--out-dir", str(tmp_path)],
        cwd=ml_root,
    )
    first = sha256(tmp_path / "train_phrase_holdout.csv")

    result = run(
        ["dataset/split_dataset.py", "--strategy", "phrase",
         "--input", str(sample_csv), "--out-dir", str(tmp_path)],
        cwd=ml_root,
    )
    assert "resumed from checkpoint" in result.stdout, "the checkpoint was not reused"
    assert sha256(tmp_path / "train_phrase_holdout.csv") == first


def test_split_rows_account_for_every_source_row(
    ml_root: Path, sample_csv: Path, tmp_path: Path, sample_manifest: dict
) -> None:
    """No row may be dropped or duplicated by the split."""
    run(
        ["dataset/split_dataset.py", "--strategy", "phrase",
         "--input", str(sample_csv), "--out-dir", str(tmp_path)],
        cwd=ml_root,
    )
    report = json.loads((tmp_path / "split_phrase_holdout.json").read_text())
    assert report["train"]["rows"] + report["eval"]["rows"] == sample_manifest["rows"]
