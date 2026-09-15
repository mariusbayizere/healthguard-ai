"""reproduce.py: `make reproduce` (CLAUDE.md §14). Every committed output it covers is
re-derived and diffed; refusals must still refuse; nothing it runs may dirty the tree."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import reproduce as rp

ML_ROOT = Path(__file__).resolve().parent.parent
REPO = ML_ROOT.parent.parent


def _py(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def test_a_step_passes_on_its_expected_exit_code(tmp_path):
    assert rp.run_step(rp.Step("ok", _py("pass"), tmp_path)).ok
    refused = rp.Step("refuses", _py("raise SystemExit(2)"), tmp_path, expected_exit=2)
    assert rp.run_step(refused).ok


def test_a_step_that_exits_differently_fails(tmp_path):
    """A refusal that stops refusing is a regression, not a pass."""
    result = rp.run_step(rp.Step("x", _py("pass"), tmp_path, expected_exit=2))
    assert not result.ok and "exit 0, expected 2" in result.detail


def test_output_identical_to_the_committed_file_passes(tmp_path):
    committed = tmp_path / "out.txt"
    committed.write_text("a\nb\n")
    step = rp.Step(
        "same", _py("print('a'); print('b')"), tmp_path, compare_to=committed
    )
    assert rp.run_step(step).ok


def test_output_that_differs_fails_and_names_the_first_difference(tmp_path):
    committed = tmp_path / "out.txt"
    committed.write_text("a\nb\n")
    step = rp.Step(
        "diff", _py("print('a'); print('c')"), tmp_path, compare_to=committed
    )
    result = rp.run_step(step)
    assert not result.ok and "line 2" in result.detail


def test_stderr_can_be_the_compared_stream(tmp_path):
    committed = tmp_path / "err.txt"
    committed.write_text("refused\n")
    step = rp.Step(
        "err",
        _py("import sys; print('refused', file=sys.stderr); raise SystemExit(2)"),
        tmp_path,
        expected_exit=2,
        compare_to=committed,
        stream="stderr",
    )
    assert rp.run_step(step).ok


def test_a_file_already_matching_its_digest_is_not_regenerated(tmp_path):
    target = tmp_path / "f.csv"
    target.write_bytes(b"x")
    digest = hashlib.sha256(b"x").hexdigest()
    assert rp.matches_digest(target, digest)
    assert not rp.matches_digest(tmp_path / "absent.csv", digest)


def test_every_compared_output_is_a_tracked_file():
    tracked = set(
        subprocess.run(
            ["git", "-C", str(REPO), "ls-files"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
    )
    compared = [s.compare_to for s in rp.steps() if s.compare_to is not None]
    assert len(compared) >= 4
    for path in compared:
        assert path.resolve().relative_to(REPO.resolve()).as_posix() in tracked, path


def test_the_n9_refusals_are_expected_to_exit_2():
    by_name = {s.name: s for s in rp.steps()}
    assert by_name["gate --check-gold on the n=9 set"].expected_exit == 2
    assert by_name["training pipeline on the n=9 set"].expected_exit == 2


def test_what_is_left_out_is_listed_with_a_reason():
    names = " ".join(item for item, _ in rp.NOT_REPRODUCED)
    assert "tokenizer" in names and "latency" in names
    assert all(reason for _, reason in rp.NOT_REPRODUCED)
