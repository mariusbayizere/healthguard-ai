#!/usr/bin/env python
"""Bulk-declare form and person on already-written rows, then report every change.

Most first-pass phrases are first-person utterances, so this sets that as the
default and moves the exceptions rather than making you touch 47 rows by hand.

The person suggestion is a lexical cue only — a phrase opening with a
third-person subject noun. That is a hint to check, not a classification; an
earlier heuristic of mine produced false positives in Kinyarwanda. Everything it
changes is printed so you can reverse any of it.

    python review/bulk_declare.py review/speaker_brief_kinyarwanda_v2.csv \\
        --form utterance --default-person first
"""

from __future__ import annotations

import argparse
import collections
import csv
import re
from pathlib import Path

THIRD_PERSON_OPENERS = {
    "kinyarwanda": r'^(umwana|umugore|umugabo|mama|papa|mushiki|umuturanyi|umukecuru)\b',
    "swahili": r'^(mtoto|mke|mume|mama|baba|dada|jirani|bibi)\b',
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("brief", type=Path)
    ap.add_argument("--language", default="kinyarwanda", choices=list(THIRD_PERSON_OPENERS))
    ap.add_argument("--form", default="utterance")
    ap.add_argument("--default-person", default="first")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    rows = list(csv.DictReader(args.brief.open(encoding="utf-8")))
    fields = list(rows[0])
    if "applies" not in fields:
        # A concept may not need both persons. "no" means deliberately empty,
        # which is different from not yet written, and the tooling must not
        # count it as outstanding work.
        fields.insert(fields.index("person") + 1, "applies")
        for r in rows:
            r["applies"] = "yes"
        print("  added an 'applies' column, default yes\n")

    cue = re.compile(THIRD_PERSON_OPENERS[args.language], re.I)
    by_concept: dict[str, list[dict]] = collections.OrderedDict()
    for r in rows:
        by_concept.setdefault(r["concept_id"], []).append(r)

    set_form = moved = 0
    for cid, group in by_concept.items():
        for r in group:
            phrase = (r["your_phrasing"] or "").strip()
            if not phrase:
                continue
            if not (r.get("form") or "").strip():
                r["form"] = args.form
                set_form += 1
            looks_third = bool(cue.match(phrase))
            want = "third" if looks_third else args.default_person
            if r["person"] != want:
                partner = next((o for o in group if o["person"] == want), None)
                if partner is not None and not (partner["your_phrasing"] or "").strip():
                    partner["your_phrasing"] = phrase
                    partner["form"] = r["form"]
                    partner["notes"] = (r.get("notes") or "") + " [moved by bulk_declare — verify]"
                    r["your_phrasing"] = ""
                    r["form"] = ""
                    r["notes"] = ""
                    moved += 1
                    print(f"  moved to person={want}: {phrase[:72]}")

    print(f"\n  form set to {args.form!r} on {set_form} rows")
    print(f"  moved to a different person row       : {moved}   <- check these")
    print(f"  left at person={args.default_person!r}: {set_form - moved}")

    if args.dry_run:
        print("\n  dry run: nothing written")
        return 0
    with args.brief.open("w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f"\n  wrote {args.brief}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
