#!/usr/bin/env python
"""Merge a domain's English drafts into `speaker_brief_english_v2.csv`.

A draft is a SUGGESTION. This writes only the columns that belong to the
drafter - `suggested_english`, `verdict_fidelity`, `suggestion_note`,
`confidence`, `form`, `needs_clinician`, `hold` - and never touches
`verdict_register`, `your_phrasing`, `second_phrasing_optional` or `source`,
which are the reviewer's. Rule 8 of the phrasing guide in one function.

    python review/apply_english_drafts.py review/drafts/obstetric_english.csv
    python review/apply_english_drafts.py <drafts.csv> --dry-run

Refuses to overwrite a row the reviewer has already ruled (`your_phrasing`
non-empty) unless `--force`, so a re-run after a review pass cannot quietly
replace ruled text with a draft.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from build_english_brief import COLUMNS, OUT  # noqa: E402
from walk import save  # noqa: E402

# Columns a drafts file may set. Anything else in it is a mistake worth failing on.
DRAFTER_COLUMNS = {"suggested_english", "candidate_origin", "verdict_fidelity",
                   "suggestion_note", "confidence", "form", "needs_clinician",
                   "hold", "notes"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("drafts", type=Path)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="Also overwrite rows that already carry a ruling.")
    args = ap.parse_args()

    drafts = list(csv.DictReader(args.drafts.open(encoding="utf-8")))
    if not drafts:
        raise SystemExit(f"{args.drafts}: no rows")
    stray = set(drafts[0]) - DRAFTER_COLUMNS - {"concept_id", "person"}
    if stray:
        raise SystemExit(
            f"{args.drafts} sets {sorted(stray)}, which belong to the reviewer, "
            "not the drafter. A draft proposes; it does not rule."
        )

    rows = list(csv.DictReader(OUT.open(encoding="utf-8")))
    index = {(r["concept_id"], r["person"]): r for r in rows}

    applied, skipped = 0, []
    for draft in drafts:
        key = (draft["concept_id"], draft["person"])
        row = index.get(key)
        if row is None:
            raise SystemExit(f"{key} is not a row in the brief; the spine is fixed at 127 x 2")
        if row["your_phrasing"].strip() and not args.force:
            skipped.append(key)
            continue
        for column, value in draft.items():
            if column not in DRAFTER_COLUMNS or value == "":
                continue
            # Blank in a drafts file means "say nothing about this column", so
            # lifting an inherited hold needs an explicit token rather than an
            # empty cell that cannot be told from silence.
            row[column] = "" if value == "CLEAR" else value
        applied += 1

    print(f"{applied} rows drafted, {len(skipped)} skipped as already ruled")
    for key in skipped:
        print(f"  skipped {key[0]} {key[1]}")
    if args.dry_run:
        print("(dry run: nothing written)")
        return 0
    save(OUT, COLUMNS, rows)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
