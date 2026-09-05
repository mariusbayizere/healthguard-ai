#!/usr/bin/env python
"""Merge a domain's French drafts into `speaker_brief_french_v2.csv`.

A draft is a SUGGESTION. This writes only the columns that belong to the
drafter - `suggested_french`, `candidate_origin`, `verdict_fidelity`,
`suggestion_note`, `confidence`, `form`, `needs_clinician`, `hold`, `notes` -
and never touches `verdict_register`, `rw_french_check`, `your_phrasing`,
`second_phrasing_optional` or `source`, which are the reviewer's. Rule 8 of the
phrasing guide in one function.

    python review/apply_french_drafts.py review/drafts/obstetric_french.csv
    python review/apply_french_drafts.py <drafts.csv> --dry-run

`agreement_check` is not writable either, and not because it belongs to the
reviewer: it is DERIVED from the phrase, so it is recomputed here after every
merge. A drafter who could set it by hand could assert a phrase was safe.

`hold` takes `yes` to set and **`no` to lift** - an empty cell means the draft is
silent about the column and leaves it alone, so a hold can only be lifted by
saying so. Anything else would let a batch drop a hold by omission.

Refuses to overwrite a row the reviewer has already ruled (`your_phrasing`
non-empty) unless `--force`.
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

from build_french_brief import COLUMNS, OUT  # noqa: E402
from french_relations import agreement_risks, obstetric_scope  # noqa: E402
from walk import save  # noqa: E402

DRAFTER_COLUMNS = {"suggested_french", "candidate_origin", "verdict_fidelity",
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
            f"{args.drafts} sets {sorted(stray)}, which belong to the reviewer or are "
            "derived, not the drafter's. A draft proposes; it does not rule."
        )

    rows = list(csv.DictReader(OUT.open(encoding="utf-8")))
    scope = obstetric_scope(rows)
    index = {(r["concept_id"], r["person"]): r for r in rows}

    applied, skipped, flagged, lifted = 0, [], [], []
    for draft in drafts:
        key = (draft["concept_id"], draft["person"])
        row = index.get(key)
        if row is None:
            raise SystemExit(f"{key} is not a row in the brief; the spine is fixed at 128 x 2")
        if row["your_phrasing"].strip() and not args.force:
            skipped.append(key)
            continue
        for column, value in draft.items():
            if column not in DRAFTER_COLUMNS or value == "":
                continue
            # LIFTING A HOLD IS A POSITIVE ACT. An empty cell means "this draft
            # does not speak to that column", so it can never clear anything -
            # which meant a batch that lifted a hold in its prose left the hold
            # standing in the data, and the register review then skipped the row
            # as unreviewable. `hold=no` is the explicit lift, and it has to be
            # written in the drafts file where the reason for it is written too.
            if column == "hold" and value == "no":
                row["hold"] = ""
                lifted.append(key)
                continue
            row[column] = value
        risks = agreement_risks(row["suggested_french"], scope[row["concept_id"]])
        row["agreement_check"] = " ; ".join(risks)
        if risks:
            flagged.append((key, row["suggested_french"], risks))
        applied += 1

    print(f"{args.drafts.name}: {applied} rows applied, {len(skipped)} skipped as ruled")
    for key in lifted:
        print(f"  HOLD LIFTED: {key}")
    for key in skipped:
        print(f"  skipped (already ruled): {key}")
    for key, phrase, risks in flagged:
        print(f"  FR-1 {key}: {phrase}")
        for risk in risks:
            print(f"        {risk}")
    if args.dry_run:
        print("dry run — nothing written")
        return 0
    save(OUT, COLUMNS, rows)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
