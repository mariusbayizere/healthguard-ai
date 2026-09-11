"""The D2 clinician pack agrees with the record it describes.

The pack said "the 20 `needs_clinician` rows" while the brief carried 25, and
nothing noticed because the number was typed into prose. `CLAUDE.md` rule 3
forbids exactly that for paper figures; a count of rows being sent to a
clinician for signature deserves the same treatment, so the pack is emitted by
`review/build_clinician_pack.py` and this test is the gate that keeps it
current.

It also guards the two invariants the split depends on, because both are easy
to break by editing the brief and neither would show up as a wrong number:
every flagged row reaches exactly one sheet, and no concept is split across
the two.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "review"))

from review.build_clinician_pack import (  # noqa: E402
    OUT,
    SHEET_BUILDERS,
    SHEET_FILES,
    SPINE,
    VOCABULARY_SHEET,
    build,
    derive,
)


def _flagged() -> list[dict[str, str]]:
    with SPINE.open(encoding="utf-8", newline="") as handle:
        return [r for r in csv.DictReader(handle) if r["needs_clinician"].strip()]


def test_the_committed_pack_is_what_the_builder_emits() -> None:
    """Regenerate and compare. A stale pack is one a clinician reads."""
    assert OUT.exists(), f"{OUT} is missing; run review/build_clinician_pack.py"
    assert OUT.read_text(encoding="utf-8") == build(), (
        f"{OUT.name} has drifted from the brief. Regenerate it:\n"
        "  python review/build_clinician_pack.py"
    )


def test_every_flagged_row_reaches_exactly_one_sheet() -> None:
    """No flagged row may fall between the two sheets.

    A row that reaches neither is the failure this whole change was about:
    silently absent from the pack while the record says a clinician must rule
    it.
    """
    flagged = _flagged()
    assert flagged, "no rows carry needs_clinician; the brief cannot be right"

    ask = [r for r in flagged if r["concept_id"] not in VOCABULARY_SHEET]
    words = [r for r in flagged if r["concept_id"] in VOCABULARY_SHEET]

    assert len(ask) + len(words) == len(flagged)
    assert not ({id(r) for r in ask} & {id(r) for r in words})


def test_no_concept_is_split_across_the_two_sheets() -> None:
    """Both persons of a concept travel together.

    A third-person row here is held only because its first person is. Putting
    the question on one sheet and its consequence on the other would let a
    clinician answer the question while the row it releases sat on a sheet
    they were told to skip.
    """
    by_concept: dict[str, set[bool]] = {}
    for row in _flagged():
        by_concept.setdefault(row["concept_id"], set()).add(
            row["concept_id"] in VOCABULARY_SHEET
        )
    split = {cid for cid, sheets in by_concept.items() if len(sheets) > 1}
    assert not split, f"concepts split across both sheets: {sorted(split)}"


@pytest.mark.parametrize("concept", sorted(VOCABULARY_SHEET))
def test_optional_sheet_concepts_are_really_flagged(concept: str) -> None:
    """The optional sheet is a subtraction from the ask, not a separate list.

    If a concept named here stops carrying `needs_clinician`, the sheet-2 entry
    becomes a question nobody recorded, and the ask silently gains nothing back.
    """
    assert any(r["concept_id"] == concept for r in _flagged()), (
        f"{concept} is on the optional sheet but carries no needs_clinician "
        "flag in the brief. Either restore the flag or drop it from "
        "VOCABULARY_SHEET."
    )


def test_the_four_reclassified_rows_carry_both_flag_and_hold() -> None:
    """AUDIT of 2026-09-11: `hold` alone was the wrong bucket for these.

    They gained `needs_clinician` so the pack shows them. They keep `hold`
    because nothing generates until their first person is ruled -- and clearing
    it is the one edit here that could put an unruled row into the corpus.
    """
    with SPINE.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    for concept in ("IF01", "IF03", "IF04", "IF06"):
        third = next(
            r for r in rows if r["concept_id"] == concept and r["person"] == "third"
        )
        assert third["needs_clinician"].strip(), f"{concept} third lost its flag"
        assert third["hold"].strip().lower() == "yes", (
            f"{concept} third is no longer held. Its first person is still "
            "flagged for a clinician, so this row must not generate."
        )
        assert not third["your_phrasing"].strip(), (
            f"{concept} third has a phrasing. It was 'not drafted' precisely "
            "because drafting it would transform a guess."
        )


# ── the three CSV sheets ────────────────────────────────────────────────────
#
# These are what the workbook is built from and therefore what actually
# reaches a clinician. The Markdown is read in the repository; a stale CSV is
# read at the desk of the person signing, which is worse.


@pytest.mark.parametrize("name", sorted(SHEET_FILES))
def test_each_sheet_is_what_the_builder_emits(name: str) -> None:
    path = SHEET_FILES[name]
    assert path.exists(), (
        f"{path} is missing. Regenerate:\n  python review/build_clinician_pack.py"
    )
    columns, rows = SHEET_BUILDERS[name](derive())
    with path.open(encoding="utf-8", newline="") as handle:
        on_disk = list(csv.DictReader(handle))
    assert list(on_disk[0]) == columns, f"{path.name}: columns differ"
    assert on_disk == rows, (
        f"{path.name} has drifted from the brief. Regenerate:\n"
        "  python review/build_clinician_pack.py"
    )


def test_the_clinical_sheet_holds_every_row_of_the_ask() -> None:
    """The sheet and the document must ask about the same rows.

    Two renderings of one derivation, so this is cheap -- but it is the
    assertion that would fail if someone gave the workbook its own filter.
    """
    d = derive()
    _, rows = SHEET_BUILDERS["clinical"](d)
    assert len(rows) == len(d.ask)
    assert {(r["concept_id"], r["person"]) for r in rows} == {
        (r["concept_id"], r["person"]) for r in d.ask
    }


def _author_columns() -> set[str]:
    """Read `csv_to_xlsx.AUTHOR_COLUMNS` WITHOUT importing it.

    Parsed rather than imported because `csv_to_xlsx` needs openpyxl, which is
    deliberately not in requirements -- and the CI job that runs this suite
    installs nothing but pytest. An importorskip here would turn the guard off
    in the only place it has to hold, so the set is read out of the source the
    way `test_label_parity.py` reads the backend enum.
    """
    import ast

    source = (ROOT / "review" / "csv_to_xlsx.py").read_text(encoding="utf-8")
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "AUTHOR_COLUMNS" for t in node.targets
        ):
            assert isinstance(node.value, ast.Set)
            return {
                element.value
                for element in node.value.elts
                if isinstance(element, ast.Constant)
            }
    raise AssertionError("AUTHOR_COLUMNS not found in review/csv_to_xlsx.py")


def test_answer_columns_are_empty_and_tinted() -> None:
    """A pre-filled answer column is a leading question.

    The tint is what tells a clinician where to type, so these column names
    must stay in `csv_to_xlsx.AUTHOR_COLUMNS` -- a renamed column would arrive
    un-tinted and read as ours rather than theirs.
    """
    AUTHOR_COLUMNS = _author_columns()

    answers = {"your_ruling", "your_notes", "your_word", "your_answer"}
    for name, builder in SHEET_BUILDERS.items():
        columns, rows = builder(derive())
        present = answers & set(columns)
        assert present, f"{name} sheet offers nowhere to answer"
        assert present <= AUTHOR_COLUMNS, (
            f"{name}: {sorted(present - AUTHOR_COLUMNS)} would not be tinted"
        )
        for row in rows:
            for column in present:
                assert row[column] == "", f"{name}: {column} is pre-filled"
