"""Build the arXiv archive from an explicit manifest, and fail loudly on a gap.

WHY THIS IS A SCRIPT AND NOT A ZIP COMMAND. The archive was built by hand from a
shell for several rounds. Twice that went wrong in a way nothing reported:

  - `generated/full_text.txt` was swept in, adding 138 KB of a plain-text
    rendering that the archive does not need, and the file count in the commit
    message was then taken from that build and carried forward after the file
    was removed.
  - `main.bbl` was named on the command line, did not exist, and `zip` said
    "name not matched" into a pipe whose output was discarded. The archive
    shipped without a bibliography for two commits and the sha256 matched
    across rebuilds, which looked like reproducibility and was really the same
    gap reproduced.

So the manifest is explicit, a missing REQUIRED file is an error rather than a
warning, and the listing and digest are printed from the archive that was
actually written rather than from what was requested.

Usage:
    python paper/build_archive.py                    # refuses without main.bbl
    python paper/build_archive.py --allow-missing-bbl
    python paper/build_archive.py --check            # verify, build nothing
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import zipfile
from pathlib import Path

PAPER = Path(__file__).resolve().parent
ROOT = PAPER.parent
OUT = ROOT / "KinyaMed_arxiv_ready.zip"

# Every file the document needs to compile from a clean directory.
REQUIRED_FILES = (
    "main.tex",
    "results.tex",
    "references.bib",
    "acl.sty",
    "acl_natbib.bst",
)
REQUIRED_DIRS = ("sections", "generated")

# arXiv does not run bibtex. Without this the references come out as [?].
BBL = "main.bbl"

# Rendered from the sources by render_plain.py for the completeness tests. Not a
# LaTeX source, so it is not part of what a reader compiles.
EXCLUDE_NAMES = frozenset({"full_text.txt"})
EXCLUDE_SUFFIXES = (".bak", ".pyc", ".aux", ".log", ".out", ".blg", ".synctex.gz")


class Missing(RuntimeError):
    """A file the archive must carry is not there. Never a silent omission."""


def manifest(allow_missing_bbl: bool) -> list[Path]:
    """Every file to archive, or an error naming what is absent."""
    chosen: list[Path] = []
    absent: list[str] = []

    for name in REQUIRED_FILES:
        path = PAPER / name
        (chosen if path.is_file() else absent).append(path if path.is_file() else name)

    bbl = PAPER / BBL
    if bbl.is_file():
        chosen.append(bbl)
    elif not allow_missing_bbl:
        absent.append(BBL)

    for name in REQUIRED_DIRS:
        directory = PAPER / name
        if not directory.is_dir():
            absent.append(name + "/")
            continue
        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            if path.name in EXCLUDE_NAMES or path.name.endswith(EXCLUDE_SUFFIXES):
                continue
            if "__pycache__" in path.parts:
                continue
            chosen.append(path)

    if absent:
        raise Missing(
            "not in paper/: "
            + ", ".join(str(a) for a in absent)
            + (
                f"\n\n{BBL} is produced by a local compile (latex, bibtex, latex, "
                "latex). arXiv does not run bibtex, so an archive without it "
                "renders every citation as [?]. Pass --allow-missing-bbl to build "
                "anyway, for a local Overleaf compile that will run bibtex itself."
            )
            if BBL in absent
            else ""
        )
    return chosen


def build(files: list[Path]) -> None:
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(PAPER).as_posix())


def report() -> int:
    with zipfile.ZipFile(OUT) as archive:
        names = archive.namelist()
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    print(f"{OUT.relative_to(ROOT)}: {len(names)} files, {OUT.stat().st_size:,} bytes")
    print(f"sha256 {digest}")
    if BBL not in names:
        print(f"\nWARNING: no {BBL}. Citations will render as [?] on arXiv.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allow-missing-bbl",
        action="store_true",
        help="build without main.bbl (Overleaf runs bibtex; arXiv does not)",
    )
    parser.add_argument(
        "--check", action="store_true", help="verify the manifest, write nothing"
    )
    args = parser.parse_args()

    try:
        files = manifest(args.allow_missing_bbl)
    except Missing as exc:
        print(f"refusing to build: {exc}", file=sys.stderr)
        return 1

    if args.check:
        print(f"manifest complete: {len(files)} files")
        return 0

    build(files)
    return report()


if __name__ == "__main__":
    raise SystemExit(main())
