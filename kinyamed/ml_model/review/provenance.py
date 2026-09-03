#!/usr/bin/env python
"""Who actually wrote each phrase — five categories, derived not asserted.

The old scheme had one bucket for everything the speaker did not type, so a
`ndi` -> `ari` transform of a sentence they wrote counted the same as a phrase I
composed. The headline "speaker rate" then fell every time third-person work
landed — 74% -> 66% -> 61% across three batches — although nothing about the
speaker's involvement had changed. That is a measurement artefact, not a trend.

    speaker_authored     the speaker wrote the words
    speaker_derived      mechanical person-transform of the SAME concept's
                         speaker-authored phrase
    machine_approved     I composed new wording; the speaker accepted it unchanged
    machine_derived      person-transform of a machine-drafted phrase
    machine_edited       I drafted, the speaker changed it (currently unused)
    not_applicable       this person does not apply to this concept
    unresolved           wording settled, concept still open

**Every category is derived from data already in the brief**, so anyone can
recompute it and no category depends on how a note was worded. `speaker_derived`
in particular is a defined test — the same concept's other person is
`source=speaker` and non-empty — not a judgement about how speaker-ish a phrase
feels.

    python review/provenance.py                 # report
    python review/provenance.py --write         # backfill the source column

The classification is deliberately CONSERVATIVE. A phrase reusing the speaker's
clause from a DIFFERENT concept — GI06 taking CR06's `Maze ibyumweru birenga
bibiri`, GI01 taking OB10's `ndaruka ibyo ndya byose` — still counts as
machine_approved, because widening the test needs a threshold for how much reuse
is enough and a threshold is exactly what a reviewer should distrust. The number
comes out lower than it could, which is the right direction to be wrong in.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BRIEF = ROOT / "review" / "speaker_brief_kinyarwanda_v2.csv"

SPEAKER_AUTHORED = "speaker"
SPEAKER_DERIVED = "speaker_derived"
MACHINE_APPROVED = "machine_approved"
MACHINE_DERIVED = "machine_derived"
MACHINE_EDITED = "machine_edited"
NOT_APPLICABLE = "not_applicable"
UNRESOLVED = "unresolved"

# Order is report order, and is roughly "most speaker" to "least".
CATEGORIES = (
    SPEAKER_AUTHORED, SPEAKER_DERIVED, MACHINE_APPROVED,
    MACHINE_DERIVED, MACHINE_EDITED, UNRESOLVED, NOT_APPLICABLE,
)
LABELS = {
    SPEAKER_AUTHORED: "speaker-authored — the speaker wrote the words",
    SPEAKER_DERIVED: "speaker-derived — person-transform of their own phrase",
    MACHINE_APPROVED: "machine-drafted, speaker-approved",
    MACHINE_DERIVED: "machine-derived — transform of a machine-drafted phrase",
    MACHINE_EDITED: "machine-drafted, speaker-edited",
    UNRESOLVED: "unresolved — wording settled, concept open",
    NOT_APPLICABLE: "not applicable for this person",
}
# The two roll-ups the paper needs.
SPEAKERS_OWN_WORDS = (SPEAKER_AUTHORED, SPEAKER_DERIVED)
NEWLY_COMPOSED = (MACHINE_APPROVED, MACHINE_DERIVED, MACHINE_EDITED)

OTHER = {"first": "third", "third": "first"}


def classify(row: dict, by_key: dict[tuple[str, str], dict]) -> str:
    """The category this row belongs in. Pure function of the brief."""
    if (row.get("applies") or "yes").strip().lower() == "no":
        return NOT_APPLICABLE
    if not (row.get("your_phrasing") or "").strip():
        return row.get("source", "") or ""      # unauthored: nothing to classify

    current = (row.get("source") or "").strip()
    if current in (SPEAKER_AUTHORED, MACHINE_EDITED, UNRESOLVED):
        return current

    counterpart = by_key.get((row["concept_id"], OTHER[row["person"]]))
    counterpart_authored = bool(counterpart and (counterpart.get("your_phrasing") or "").strip())
    counterpart_source = (counterpart.get("source") or "").strip() if counterpart else ""

    # A person-transform only exists in the third person: the first person is the
    # form the speaker writes, the third is derived from it.
    if row["person"] == "third" and counterpart_authored:
        if counterpart_source == SPEAKER_AUTHORED:
            return SPEAKER_DERIVED
        if counterpart_source in (MACHINE_APPROVED, MACHINE_DERIVED, MACHINE_EDITED):
            return MACHINE_DERIVED
    return MACHINE_APPROVED


def classified(brief: Path = BRIEF) -> list[tuple[dict, str]]:
    rows = list(csv.DictReader(brief.open(encoding="utf-8")))
    by_key = {(r["concept_id"], r["person"]): r for r in rows}
    return [(r, classify(r, by_key)) for r in rows]


def report(brief: Path = BRIEF) -> None:
    pairs = classified(brief)
    authored = [(r, c) for r, c in pairs
                if (r.get("your_phrasing") or "").strip()
                and (r.get("applies") or "yes").strip().lower() != "no"]
    counts = Counter(c for _, c in authored)
    total = len(authored)
    print(f"{total} authored phrases\n")
    for category in CATEGORIES:
        if category == NOT_APPLICABLE or not counts.get(category):
            continue
        n = counts[category]
        print(f"  {n:3}  {100 * n / total:5.1f}%  {LABELS[category]}")
    own = sum(counts.get(c, 0) for c in SPEAKERS_OWN_WORDS)
    new = sum(counts.get(c, 0) for c in NEWLY_COMPOSED)
    print()
    print(f"  the speaker's own words   {own:3}/{total} = {100 * own / total:.0f}%")
    print(f"  newly composed by me      {new:3}/{total} = {100 * new / total:.0f}%"
          f"   (every row carries an explicit accept)")
    na = sum(1 for r, c in pairs if c == NOT_APPLICABLE)
    print(f"\n  {na} rows are not applicable for their person; "
          f"{len(pairs) - total - na} are still unauthored.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--write", action="store_true",
                    help="Backfill the brief's source column from the classification.")
    ap.add_argument("brief", nargs="?", type=Path, default=BRIEF)
    args = ap.parse_args()

    if args.write:
        sys.path.insert(0, str(ROOT / "review"))
        from walk import save
        rows = list(csv.DictReader(args.brief.open(encoding="utf-8")))
        fields = list(rows[0])
        by_key = {(r["concept_id"], r["person"]): r for r in rows}
        changed = Counter()
        for row in rows:
            new = classify(row, by_key)
            old = (row.get("source") or "").strip()
            if new and new != old:
                changed[f"{old or '(empty)'} -> {new}"] += 1
                row["source"] = new
        save(args.brief, fields, rows)
        for move, n in sorted(changed.items()):
            print(f"  {n:3}  {move}")
        print(f"\n{sum(changed.values())} row(s) reclassified\n")

    report(args.brief)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
