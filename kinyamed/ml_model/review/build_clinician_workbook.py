#!/usr/bin/env python
"""Turn the clinician pack's three CSVs into one workbook a clinician can fill in.

`build_clinician_pack.py` writes the three sheets as CSV; this adds the
presentation and nothing else. The styling, the tinted answer columns and the
read-back check all come from `csv_to_xlsx.py` by import rather than by copy --
the audit's finding was five copies of one constant, and two copies of a
workbook writer would be the same mistake in a different shape.

Three tabs in ONE workbook on purpose. The vocabulary sheet is explicitly
optional and the questions sheet is explicitly not row-by-row, and both of
those facts are only legible NEXT TO the ask. Split into three files they
arrive as three requests, which is exactly the misreading the covering note
exists to prevent.

    python review/build_clinician_pack.py        # writes the CSVs first
    python review/build_clinician_workbook.py    # -> ~/kinyamed-briefs/

Needs openpyxl, which is not in requirements.txt because nothing else uses it:

    python3 -m venv /tmp/xlsxenv && /tmp/xlsxenv/bin/pip install openpyxl
    /tmp/xlsxenv/bin/python review/build_clinician_workbook.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "review"))

from build_clinician_pack import SHEET_FILES, derive
from csv_to_xlsx import verify, write_sheet

# Tab order is the order of the ask: what is being requested, then what is
# optional, then the questions that are not about one row. `SHEET_FILES` is
# keyed the same way, so a sheet cannot be added there and silently not appear
# here -- `main` asserts the two agree.
TABS = [
    ("1 clinical", "clinical", "C2"),
    ("2 vocabulary (optional)", "vocabulary", "B2"),
    ("3 questions + taxonomy", "questions", "C2"),
]


def start_here(ws, counts: dict[str, int]) -> int:
    """The covering note, as the first thing the workbook opens on.

    The same note is at the top of the Markdown pack. It is repeated here
    because a workbook gets forwarded on its own, and the one thing that must
    survive that is what the signature does and does not cover.
    """
    ask = counts["clinical"]
    words = counts["vocabulary"]

    lines = [
        ("Clinician review pack — KinyaMed urgency taxonomy", True),
        ("", False),
        ("NOT YET REVIEWED BY ANY CLINICIAN.", True),
        (
            "No claim of clinical approval appears anywhere in this project, and "
            "none may until the sign-off at the bottom of this sheet is "
            "signed.",
            False,
        ),
        ("", False),
        (f"YOU ARE BEING ASKED ABOUT {ask} ROWS", True),
        (
            "Not 20. That figure appears in this project's own planning documents "
            "and was never a count of rows — it counted concepts. The unit of "
            "review is a row: most concepts carry a first-person and a "
            "third-person phrasing, and the two can fail differently. A wording "
            "can be right in one person's mouth and wrong in the other's, which "
            "is most of why this pack exists.",
            False,
        ),
        ("", False),
        ("THE THREE TABS, AND ONLY THE FIRST IS THE ASK", True),
        (
            f"Tab 1 'clinical' — {ask} rows. This is the request. Every row can be "
            "answered without a Kinyarwanda speaker present. Type in the "
            "cream-coloured your_ruling and your_notes columns.",
            False,
        ),
        (
            f"Tab 2 'vocabulary' — {words} entries, OPTIONAL. Questions about which "
            "Kinyarwanda word a patient uses. These are blocked on a native "
            "speaker, not on you. Answer any you happen to know; skipping the tab "
            "entirely costs this project nothing it was expecting.",
            False,
        ),
        (
            f"Tab 3 'questions + taxonomy' — {counts['questions']} rows. Five "
            "questions that are not about any single row, then the taxonomy "
            "check: every concept carrying no published anchor, one per row, for "
            "you to confirm or correct.",
            False,
        ),
        ("", False),
        ("WHERE TO TYPE", True),
        (
            "The cream-coloured columns are yours. Everything else is ours — "
            "please leave it as it is.",
            False,
        ),
        ("", False),
        ("WHAT THE SIGNATURE COVERS", True),
        (
            "The sign-off is at the bottom of this sheet and covers TAB 1 ONLY. "
            "Nothing on tabs 2 or 3 is part of what you are signing.",
            False,
        ),
        ("", False),
        ("'I DON'T KNOW' IS AN ANSWER", True),
        (
            "Several of these rows are here because this project refused to guess. "
            "A row you cannot settle is worth more marked unsettled than filled "
            "in, and 'the concept should not exist' is a ruling we will act on.",
            False,
        ),
    ]
    ws.column_dimensions["A"].width = 110
    for r, (text, bold) in enumerate(lines, start=1):
        cell = ws.cell(row=r, column=1, value=text)
        cell.font = Font(bold=bold, size=13 if bold and r == 1 else 11)
        cell.alignment = Alignment(vertical="top", wrap_text=True)
    return len(lines)


def sign_off(ws, start_row: int, ask: int) -> None:
    """The signature block, on the covering sheet.

    It was first written under the clinical rows, where it reads better -- and
    `csv_to_xlsx.verify()` rejected the workbook, because those twelve extra
    rows meant tab 1 no longer matched its CSV. That check is worth more than
    the placement: it is the guarantee that a clinician is ruling on exactly
    the rows the record holds, with nothing added, dropped or coerced on the
    way. So the three data tabs stay byte-identical to their CSVs and the
    signature lives here, under the note that explains what it covers.

    On a sheet rather than in a separate document, because a workbook returned
    by email is the artefact that will exist and a detached signature page is
    the one that will not.
    """
    lines = [
        "",
        f"SIGN-OFF — covers the {ask} rows on tab 1 'clinical', and nothing else.",
        "I have reviewed the taxonomy and the rows on tab 1.",
        "",
        "Name / role / facility: ______________________________",
        "",
        "Approved  /  approved with the amendments recorded above  /  not approved",
        "(delete as applicable)",
        "",
        "Signature: ______________________     Date: ______________",
    ]
    for offset, text in enumerate(lines):
        cell = ws.cell(row=start_row + offset, column=1, value=text)
        cell.font = Font(bold=text.startswith("SIGN-OFF"))
        cell.alignment = Alignment(vertical="top")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", type=Path, default=Path.home() / "kinyamed-briefs")
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    assert {key for _, key, _ in TABS} == set(SHEET_FILES), (
        "TABS and SHEET_FILES disagree about which sheets exist"
    )

    missing = [p for p in SHEET_FILES.values() if not p.exists()]
    if missing:
        print(
            "these sheets have not been generated:\n  "
            + "\n  ".join(str(p) for p in missing)
            + "\nRun: python review/build_clinician_pack.py",
            file=sys.stderr,
        )
        return 1

    d = derive()
    counts = {
        key: len(list(SHEET_FILES[key].open(encoding="utf-8"))) - 1
        for _, key, _ in TABS
    }

    book = Workbook()
    cover = book.active
    cover.title = "start here"
    note_rows = start_here(cover, counts)
    sign_off(cover, note_rows + 2, counts["clinical"])

    for title, key, freeze in TABS:
        write_sheet(book.create_sheet(title), SHEET_FILES[key], freeze)

    path = args.out / "d2-clinician-review-pack.xlsx"
    book.save(path)

    # Read every cell back and compare it to the CSV. The signature block and
    # the covering note are presentation; the ROWS must be byte-identical to
    # what the record says, or a clinician is ruling on something else.
    verify(path, [(title, SHEET_FILES[key]) for title, key, _ in TABS])

    print(f"wrote {path}")
    for title, key, _ in TABS:
        print(f"  tab {title!r}: {counts[key]} rows from {SHEET_FILES[key].name}")
    assert counts["clinical"] == len(d.ask)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
