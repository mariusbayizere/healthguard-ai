"""Crash safety of the write path.

The failure these guard against is specific: a run killed mid-write leaving a
file that is the right size and parses cleanly, so a later step trains on
truncated data without ever raising.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

from dataset.atomicio import Checkpoint, atomic_write, atomic_write_json, sweep_partials


def test_atomic_write_replaces_only_on_success(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    with atomic_write(target) as handle:
        handle.write("complete")
    assert target.read_text() == "complete"


def test_exception_leaves_previous_file_intact(tmp_path: Path) -> None:
    target = tmp_path / "out.txt"
    with atomic_write(target) as handle:
        handle.write("original")

    try:
        with atomic_write(target) as handle:
            handle.write("HALF")
            raise RuntimeError("simulated failure")
    except RuntimeError:
        pass

    assert target.read_text() == "original"
    assert not list(tmp_path.glob(".*.partial")), "temp file was not cleaned up"


def test_sigkill_cannot_corrupt_the_destination(tmp_path: Path) -> None:
    """The real crash: SIGKILL runs no handler, so cleanup cannot happen.

    The destination must still be either the old complete file or nothing —
    never a truncated file that looks valid.
    """
    target = tmp_path / "out.txt"
    with atomic_write(target) as handle:
        handle.write("original-content")
    before = target.read_bytes()

    script = textwrap.dedent(
        f"""
        import os, sys
        sys.path.insert(0, {str(Path(__file__).resolve().parent.parent)!r})
        from pathlib import Path
        from dataset.atomicio import atomic_write
        with atomic_write(Path({str(target)!r})) as handle:
            handle.write("X" * 100000)
            handle.flush()
            os.kill(os.getpid(), 9)   # no cleanup can run past this point
        """
    )
    result = subprocess.run([sys.executable, "-c", script], capture_output=True)
    assert result.returncode == -9, f"expected SIGKILL, got {result.returncode}"

    assert target.read_bytes() == before, "SIGKILL corrupted the destination"


def test_sweep_removes_debris_a_kill_left_behind(tmp_path: Path) -> None:
    target = tmp_path / "out.csv"
    with atomic_write(target) as handle:
        handle.write("kept")

    # Debris of exactly the size a complete file would be: the case that makes
    # a shallow `ls` or size check useless.
    orphan = tmp_path / f".{target.name}.deadbeef.partial"
    orphan.write_text("kept")

    removed = sweep_partials(target)
    assert len(removed) == 1
    assert not orphan.exists()
    assert target.read_text() == "kept", "sweep must not touch the real output"


def test_checkpoint_records_and_invalidates_on_fingerprint(tmp_path: Path) -> None:
    ledger = Checkpoint(tmp_path / "checkpoint.json")
    assert not ledger.done("scan", "fp-a")

    ledger.mark("scan", "fp-a", rows=10)
    assert ledger.done("scan", "fp-a")
    # An upstream change must force the step to redo rather than resume stale
    # state against different inputs.
    assert not ledger.done("scan", "fp-b")

    reloaded = Checkpoint(tmp_path / "checkpoint.json")
    assert reloaded.done("scan", "fp-a"), "checkpoint did not survive a restart"


def test_unreadable_checkpoint_is_not_fatal(tmp_path: Path) -> None:
    path = tmp_path / "checkpoint.json"
    path.write_text("{ this is not json")
    ledger = Checkpoint(path)
    assert not ledger.done("scan", "fp-a")


def test_atomic_write_json_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "payload.json"
    atomic_write_json(target, {"b": 2, "a": [1, 2, 3]})
    import json

    assert json.loads(target.read_text()) == {"b": 2, "a": [1, 2, 3]}
