#!/usr/bin/env python
"""Crash-safe file writing and step checkpointing.

A process killed mid-write must never leave a file that passes a shallow check.
Everything here writes to a sibling temp file, fsyncs it, and only then renames
into place: os.replace is atomic within a filesystem, so a reader sees either
the old complete file or the new complete file, never a partial one.

The temp file is a sibling (not /tmp) so the rename cannot cross a filesystem
boundary, which would silently downgrade it to a copy.
"""

from __future__ import annotations

import json
import os
import resource
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator


def peak_rss_mib() -> float:
    """Peak resident set size of this process, in MiB."""
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024


@contextmanager
def atomic_write(path: Path, mode: str = "w", **kwargs) -> Iterator:
    """Yield a handle to a temp file that is renamed onto `path` on clean exit.

    On any exception the temp file is removed and `path` is left untouched, so a
    crash cannot produce a truncated output that still looks valid to `ls`.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}.", suffix=".partial"
    )
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, mode, **kwargs) as handle:
            yield handle
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
        # Durability of the rename itself needs the directory synced too.
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise


def atomic_write_json(path: Path, payload: object) -> None:
    with atomic_write(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


class Checkpoint:
    """A tiny resumable step ledger stored as one atomically-written JSON file.

    Each completed step records whatever it needs to prove it is still valid
    (digests, row counts). A rerun skips a step only when its recorded inputs
    still match, so an edited upstream file forces the dependent steps to redo.
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.state: dict = {"steps": {}}
        if self.path.exists():
            try:
                self.state = json.loads(self.path.read_text())
            except json.JSONDecodeError:
                # A checkpoint we cannot parse is worth less than no checkpoint.
                self.state = {"steps": {}}

    def done(self, step: str, fingerprint: str | None = None) -> bool:
        entry = self.state["steps"].get(step)
        if entry is None:
            return False
        return fingerprint is None or entry.get("fingerprint") == fingerprint

    def mark(self, step: str, fingerprint: str | None = None, **detail) -> None:
        self.state["steps"][step] = {"fingerprint": fingerprint, **detail}
        atomic_write_json(self.path, self.state)

    def clear(self, step: str) -> None:
        self.state["steps"].pop(step, None)
        atomic_write_json(self.path, self.state)


def peak_rss_mib_total() -> float:
    """Peak RSS of this process plus any worker children, in MiB.

    Children are reported separately by the kernel, so a parallel step that
    keeps the parent small can still be expensive; both matter on a box where
    systemd-oomd watches the whole user slice.
    """
    own = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    kids = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
    return (own + kids) / 1024


def sweep_partials(*paths: Path) -> list[str]:
    """Remove stale temp files left by a previous kill, returning their names.

    atomic_write unlinks its temp file when an exception unwinds, but SIGKILL
    (which is how systemd-oomd ends a run) gives the process no chance to do
    that, so debris survives. Sweeping the destinations we are about to write
    keeps a crashed run from silently accumulating hundreds of MB of orphans.

    Only siblings of the named destinations are touched, so this cannot remove
    another job's in-flight file unless that job writes the same destination —
    which would already be a conflict.
    """
    removed: list[str] = []
    for path in paths:
        path = Path(path)
        for stale in path.parent.glob(f".{path.name}.*.partial"):
            try:
                size = stale.stat().st_size
                stale.unlink()
                removed.append(f"{stale.name} ({size:,} B)")
            except OSError:
                continue
    return removed
