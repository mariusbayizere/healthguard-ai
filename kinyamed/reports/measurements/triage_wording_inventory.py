"""Inventory every line that calls something "triage" or cites ETAT.

For SRS CORRECTIONS A27 (reports/STATE.md). Lists, does not change. Run from
`kinyamed/`:

    python3 reports/measurements/triage_wording_inventory.py > reports/measurements/triage_wording_inventory.txt

Scope: files tracked by git under `kinyamed/` and the repository README, plus the
local, git-ignored `CLAUDE.md`. Matches `triag` (triage, triaged, under-triage)
case-insensitively, and `ETAT` as a whole word. The area labels come from paths
only. They do not decide whether a line describes the system or names a code
identifier; the curated table in STATE.md A27 does that.
"""

from __future__ import annotations

import re
import subprocess
from collections import Counter
from pathlib import Path

PATTERN = re.compile(r"triag|\bETAT\b", re.IGNORECASE)
SKIP_SUFFIXES = {".png", ".jpg", ".pdf", ".ico", ".woff", ".woff2", ".lock"}
SKIP_NAMES = {"package-lock.json"}

AREAS: list[tuple[str, str]] = [
    ("CLAUDE.md", "spec: CLAUDE.md (local, git-ignored)"),
    ("../README.md", "readme"),
    ("ml_model/paper/", "paper"),
    ("frontend/src/__tests__/", "frontend tests"),
    ("frontend/e2e/", "frontend tests"),
    ("frontend/src/", "frontend source (UI strings and identifiers)"),
    ("frontend/index.html", "frontend source (UI strings and identifiers)"),
    ("backend/tests/", "backend tests"),
    ("backend/migrations/", "backend migrations"),
    ("backend/", "backend source (API strings and identifiers)"),
    ("ml_model/review/", "speaker- and clinician-facing briefs"),
    ("ml_model/docs/", "ml_model docs, protocols, outreach"),
    ("ml_model/", "ml_model code and run records"),
    ("docs/", "docs/"),
    ("reports/", "audit reports"),
]


def area_of(path: str) -> str:
    if "__tests__" in path or ".test." in path:
        return "frontend tests" if path.startswith("frontend/") else "tests"
    for prefix, label in AREAS:
        if path == prefix or path.startswith(prefix):
            return label
    return "other"


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--full-name", "."], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    # --full-name gives paths from the repo root; make them relative to kinyamed/.
    return [p.removeprefix("kinyamed/") for p in out] + ["../README.md", "CLAUDE.md"]


def main() -> None:
    rows: list[tuple[str, str, int, str]] = []
    for rel in tracked_files():
        path = Path(rel)
        if path.suffix in SKIP_SUFFIXES or path.name in SKIP_NAMES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for number, line in enumerate(text.splitlines(), start=1):
            if PATTERN.search(line):
                rows.append((area_of(rel), rel, number, line.strip()[:200]))

    counts = Counter(area for area, _, _, _ in rows)
    files = Counter(area for area, _ in {(a, f) for a, f, _, _ in rows})
    print(f"# {len(rows)} matching lines in {len({f for _, f, _, _ in rows})} files\n")
    for area, n in counts.most_common():
        print(f"{n:5d} lines  {files[area]:3d} files  {area}")
    for area in sorted(counts):
        print(f"\n## {area}\n")
        for a, rel, number, line in rows:
            if a == area:
                print(f"{rel}:{number}: {line}")


if __name__ == "__main__":
    main()
