"""The committed archive carries what the paper needs, not merely a stable digest.

This exists because of the twelfth instance in Section~\\ref{sec:disc:unread}.
The archive shipped for two commits without `main.bbl`: it was named on a shell
command line, did not exist, and the archiver's "name not matched" went into a
pipe whose output was discarded. Its SHA-256 was recomputed on every rebuild and
matched every time, and that was read as reproducibility. It was reproducible.
It was reproducing an absence.

A digest answers whether two things are identical. These tests ask the question
a digest cannot: whether the thing is complete. They read the archive that is
committed, not the manifest the builder was asked for, because the gap being
guarded against is exactly the distance between those two.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper"
ARCHIVE = ROOT / "KinyaMed_arxiv_ready.zip"

pytestmark = pytest.mark.skipif(
    not ARCHIVE.exists(), reason="no archive built in this working tree"
)


def names() -> list[str]:
    with zipfile.ZipFile(ARCHIVE) as archive:
        return archive.namelist()


def read(name: str) -> str:
    with zipfile.ZipFile(ARCHIVE) as archive:
        return archive.read(name).decode("utf-8")


def _bibitem_keys(bbl: str) -> set[str]:
    """Every \\bibitem key, scanned rather than matched with a regex.

    A natbib \\bibitem's optional argument holds the full author list with its
    own braces and runs over several lines, so `\\[[^\\]]*\\]` finds the wrong
    bracket and a regex without DOTALL finds none. The first version of this
    test used one and reported six of the seven keys as missing from a .bbl
    that contains all seven -- a checker wrong about the thing it was checking,
    which is the failure this file is named after.
    """
    keys: set[str] = set()
    i = 0
    while (at := bbl.find("\\bibitem", i)) >= 0:
        j = at + len("\\bibitem")
        if j < len(bbl) and bbl[j] == "[":  # optional label, brace-nested
            depth = 1
            j += 1
            while j < len(bbl) and depth:
                if bbl[j] == "\\":
                    j += 2
                    continue
                if bbl[j] == "[":
                    depth += 1
                elif bbl[j] == "]":
                    depth -= 1
                j += 1
        if j < len(bbl) and bbl[j] == "{":
            depth, start = 1, j + 1
            j += 1
            while j < len(bbl) and depth:
                if bbl[j] == "\\":
                    j += 2
                    continue
                depth += (bbl[j] == "{") - (bbl[j] == "}")
                j += 1
            keys.add(bbl[start : j - 1].strip())
        i = j
    return keys


def test_bibitem_scanner_handles_the_real_shapes() -> None:
    """Both forms, and an optional label carrying braces and newlines."""
    assert _bibitem_keys(r"\bibitem{plain}") == {"plain"}
    assert _bibitem_keys("\\bibitem[{Yu et~al.(2026)Yu,\n  Adelani}]{withlabel}") == {
        "withlabel"
    }
    assert _bibitem_keys("\\bibitem[{A}]{one}\ntext\n\\bibitem[{B}]{two}") == {
        "one",
        "two",
    }


def test_archive_carries_the_bibliography() -> None:
    """arXiv does not run bibtex. Without this every citation renders as [?]."""
    assert "main.bbl" in names(), (
        "the archive has no main.bbl. It will compile locally, because Overleaf "
        "runs bibtex, and every citation will be [?] on arXiv."
    )


def test_every_cited_key_is_in_the_bbl() -> None:
    """A .bbl present but stale is the same failure wearing the right filename."""
    cited: set[str] = set()
    for name in names():
        if not name.endswith(".tex"):
            continue
        for match in re.finditer(r"\\cite[a-z]*\{([^}]*)\}", read(name)):
            cited.update(k.strip() for k in match.group(1).split(",") if k.strip())

    defined = _bibitem_keys(read("main.bbl"))

    assert cited, "no citations found in the archive at all"
    missing = cited - defined
    assert not missing, (
        f"cited but not in main.bbl, so they will render as [?]: {sorted(missing)}"
    )


def test_archive_carries_every_file_the_document_inputs() -> None:
    """An \\input the archive lacks is a compile failure for whoever downloads it."""
    present = set(names())
    wanted: set[str] = set()
    for name in present:
        if not name.endswith(".tex"):
            continue
        body = read(name)
        for match in re.finditer(r"\\(?:input|include)\{([^}]+)\}", body):
            target = match.group(1).strip()
            wanted.add(target if target.endswith(".tex") else target + ".tex")

    missing = {w for w in wanted if w not in present}
    assert not missing, (
        f"the document inputs these and the archive lacks them: {missing}"
    )


def test_archive_omits_what_is_not_a_source() -> None:
    """full_text.txt is a plain-text render for the tests, not something to compile."""
    for name in names():
        assert not name.endswith("full_text.txt"), (
            "generated/full_text.txt is in the archive; it is rendered from the "
            "sources by render_plain.py and is not one of them"
        )
        assert not name.endswith((".aux", ".log", ".blg", ".out")), (
            f"{name} is a build product and does not belong in the submission"
        )


def test_archive_matches_the_working_tree() -> None:
    """A stale archive is the original failure with a different file in it."""
    stale = []
    with zipfile.ZipFile(ARCHIVE) as archive:
        for info in archive.infolist():
            source = PAPER / info.filename
            if not source.exists():
                stale.append(f"{info.filename} (not in paper/)")
            elif source.read_bytes() != archive.read(info.filename):
                stale.append(info.filename)
    assert not stale, (
        "the archive disagrees with paper/; rebuild with "
        "`python paper/build_archive.py`: " + ", ".join(stale)
    )
