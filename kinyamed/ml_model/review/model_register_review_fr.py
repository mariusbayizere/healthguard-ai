#!/usr/bin/env python
"""Apply the MODEL's register review to the French brief, and label it as such.

Deliberately a separate tool from `apply_french_drafts.py`, which refuses to
write `verdict_register` because that column was designed to have an owner who is
not the drafter. It still refuses. This tool writes it instead, and stamps every
row it touches with a provenance value that says who did it.

**WHAT THIS IS NOT.** The three-way verdict split existed so that register — the
question of whether a phrase is what someone would actually say — was answered by
someone with standing to answer it. **NO FRENCH SPEAKER HAS SEEN ANY OF THIS.**
This tool records the drafter's own judgement because a labelled model review is
worth more than no review, and for no other reason. It is not a substitute for
the verdict it fills in.

    source = machine_reviewed    drafted by a model, reviewed by the same model,
                                 NOT verified by a native or Rwandan French
                                 speaker

Rows carrying a doubt specific to French usage — Rwandan register, or a gender
agreement a speaker should confirm — get `rw_french_check` set, and those are the
ones that matter: they are the list a francophone reviewer would work through,
and they are the honest output of a review that cannot settle them.

    python review/model_register_review_fr.py review/reviews/<file>.csv
    python review/model_register_review_fr.py <file>.csv --dry-run
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
from walk import save  # noqa: E402

REVIEWER_COLUMNS = {"verdict_register", "rw_french_check", "source", "notes"}
PROVENANCE = "machine_reviewed"
DEFAULT_REGISTER = "4"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("exceptions", type=Path,
                    help="Rows whose register is not the default, or that carry a "
                         "Rwandan-French doubt. Everything else takes the default.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    overrides = {}
    for row in csv.DictReader(args.exceptions.open(encoding="utf-8")):
        stray = set(row) - REVIEWER_COLUMNS - {"concept_id", "person"}
        if stray:
            raise SystemExit(f"{args.exceptions} sets {sorted(stray)}, which this "
                             "tool does not own. Drafting goes through "
                             "apply_french_drafts.py.")
        overrides[(row["concept_id"], row["person"])] = row

    rows = list(csv.DictReader(OUT.open(encoding="utf-8")))
    reviewed = flagged = defaulted = 0
    skipped: list[tuple[str, str, str]] = []
    cleared: list[tuple[str, str]] = []
    for row in rows:
        # Only rows carrying drafted text are reviewable. A held or applies=no row
        # has nothing to rate, and rating one would imply it is in the corpus.
        if not row["suggested_french"].strip() or row["hold"] == "yes" \
                or row["applies"] == "no":
            # An override aimed at an unreviewable row would be lost in silence,
            # and a lost Rwandan-French flag is the one thing this pass produces
            # that nothing else records. Report it instead.
            if (row["concept_id"], row["person"]) in overrides:
                why = "held" if row["hold"] == "yes" else (
                    "applies=no" if row["applies"] == "no" else "no drafted text")
                skipped.append((row["concept_id"], row["person"], why))
            # A row that was reviewable and no longer is keeps a stale verdict
            # otherwise. EX42 and PA06 were reviewed, then collapsed into IF05 by
            # the Kinyarwanda session, and carried a register score on a concept
            # that no longer generates.
            if row["verdict_register"] or row["source"] == PROVENANCE:
                row["verdict_register"] = ""
                row["source"] = ""
                cleared.append((row["concept_id"], row["person"]))
            continue
        override = overrides.get((row["concept_id"], row["person"]))
        row["verdict_register"] = DEFAULT_REGISTER
        row["source"] = PROVENANCE
        if override:
            for column, value in override.items():
                if column in REVIEWER_COLUMNS and value != "":
                    row[column] = value
            if row["rw_french_check"].strip():
                flagged += 1
        else:
            defaulted += 1
        reviewed += 1

    print(f"{reviewed} rows reviewed, all stamped source={PROVENANCE}")
    print(f"  {defaulted} took the default register {DEFAULT_REGISTER}")
    print(f"  {reviewed - defaulted} carry an explicit verdict")
    print(f"  {flagged} carry a Rwandan-French doubt")
    for concept_id, person in cleared:
        print(f"  CLEARED: {concept_id} {person} is no longer reviewable; its stale "
              "verdict and provenance stamp were removed")
    for concept_id, person, why in skipped:
        print(f"  NOT APPLIED: {concept_id} {person} is {why}; its verdict and any "
              "Rwandan-French flag are recorded in the questions document only")
    unknown = set(overrides) - {(r["concept_id"], r["person"]) for r in rows}
    for key in sorted(unknown):
        print(f"  WARNING: {key} is not a reviewable row")
    if args.dry_run:
        print("(dry run: nothing written)")
        return 0
    save(OUT, COLUMNS, rows)
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
