"""A run manifest: everything needed to re-run a training run and check its outputs
(CLAUDE.md L6, L8, §10.8).

Recorded: seed, full config, sha256 and size of every input and output, the git
commit and whether the tree was dirty, Python and package versions, the machine's
architecture, CPU and memory, and UTC start and finish times.

A run is marked NOT REPRODUCIBLE, with every reason listed, when the seed is unset,
the code is not an identifiable commit, or the tracked tree (or any untracked .py
file, which the run could import) differs from that commit. The manifest is still
written: an unreproducible run is recorded as one, never hidden.

Refused and failed runs get a manifest too, with status "refused" or "failed".

No username or hostname is written, and paths inside the repository are relative:
the manifest is published alongside results (L11).
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import os
import platform
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PACKAGES = (
    "numpy",
    "pandas",
    "scipy",
    "torch",
    "transformers",
    "tokenizers",
    "sentencepiece",
    "safetensors",
)
SCHEMA_VERSION = 1


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _display_path(path: Path, repo: Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(Path(repo).resolve()).as_posix()
    except ValueError:
        return f"<outside repository>/{resolved.name}"


def _file_entry(path: Path, repo: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"run input or output {path} does not exist")
    return {
        "path": _display_path(path, repo),
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
    }


def _git(repo: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return completed.stdout


def code_state(repo: Path) -> dict[str, Any]:
    commit = _git(repo, "rev-parse", "HEAD")
    if commit is None:
        return {"commit": None, "dirty": True, "dirty_paths": []}
    status = _git(repo, "status", "--porcelain=v1", "--untracked-files=all") or ""
    dirty_paths = []
    for line in status.splitlines():
        code, path = line[:2], line[3:]
        if code == "??" and not path.endswith(".py"):
            continue
        dirty_paths.append(path)
    return {
        "commit": commit.strip(),
        "dirty": bool(dirty_paths),
        "dirty_paths": sorted(dirty_paths),
    }


def package_versions(names: Sequence[str] = PACKAGES) -> dict[str, str | None]:
    versions: dict[str, str | None] = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def _cpu_model() -> str | None:
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        return None
    return platform.processor() or None


def _memory_mib() -> int | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1]) // 1024
    except (OSError, ValueError, IndexError):
        return None
    return None


def machine() -> dict[str, Any]:
    return {
        "architecture": platform.machine(),
        "system": f"{platform.system()} {platform.release()}",
        "cpu_model": _cpu_model(),
        "cpu_count": os.cpu_count() or 0,
        "memory_total_mib": _memory_mib(),
    }


def environment() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "implementation": sys.implementation.name,
        "packages": package_versions(),
    }


@dataclass
class RunManifest:
    repo: Path
    record: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def start(
        cls,
        *,
        repo: Path,
        seed: int | None,
        config: Mapping[str, Any],
        inputs: Mapping[str, Path],
    ) -> RunManifest:
        """Hash every input before anything runs; a missing input stops the run here."""
        repo = Path(repo)
        record: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "status": "running",
            "started_at": _now(),
            "finished_at": None,
            "seed": seed,
            "config": dict(config),
            "inputs": {name: _file_entry(path, repo) for name, path in inputs.items()},
            "outputs": {},
            "results": {},
            "code": code_state(repo),
            "environment": environment(),
            "machine": machine(),
        }
        return cls(repo=repo, record=record)

    def _close(self, status: str) -> None:
        if self.record["status"] != "running":
            raise RuntimeError(f"this run is already {self.record['status']}")
        self.record["status"] = status
        self.record["finished_at"] = _now()
        reasons = []
        if self.record["seed"] is None:
            reasons.append("no seed was set")
        if self.record["code"]["commit"] is None:
            reasons.append("the code is not an identifiable git commit")
        elif self.record["code"]["dirty"]:
            reasons.append(
                "uncommitted changes: " + ", ".join(self.record["code"]["dirty_paths"])
            )
        self.record["reproducible"] = not reasons
        self.record["not_reproducible_because"] = reasons

    def finish(
        self, *, outputs: Mapping[str, Path], results: Mapping[str, Any]
    ) -> RunManifest:
        self._close("completed")
        self.record["outputs"] = {
            name: _file_entry(path, self.repo) for name, path in outputs.items()
        }
        self.record["results"] = dict(results)
        return self

    def refuse(self, reasons: Sequence[str]) -> RunManifest:
        self._close("refused")
        self.record["refusal"] = list(reasons)
        return self

    def fail(self, error: str) -> RunManifest:
        self._close("failed")
        self.record["error"] = error
        return self

    def write(self, path: Path) -> None:
        from dataset.atomicio import atomic_write_json

        atomic_write_json(Path(path), self.record)


def verify(manifest_path: Path, repo: Path) -> list[str]:
    """Every recorded input or output whose bytes no longer match. Empty means all match."""
    import json

    record = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    problems = []
    for kind in ("inputs", "outputs"):
        for name, entry in record.get(kind, {}).items():
            path = Path(repo) / entry["path"]
            if not path.is_file():
                problems.append(f"{kind[:-1]} {name} ({entry['path']}) is missing")
            elif sha256_file(path) != entry["sha256"]:
                problems.append(
                    f"{kind[:-1]} {name} ({entry['path']}) has changed since the run"
                )
    return problems
