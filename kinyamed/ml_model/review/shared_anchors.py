#!/usr/bin/env python
"""Which concepts cite the same clinical anchor? A mechanical duplicate detector.

Two concepts pointing at one line of WHO/IMCI are making the same clinical claim.
That is not proof they are one concept — an anchor can name two signs and each
concept take one limb — but it is objective evidence, unlike reading two glosses
and judging whether they feel alike.

It found two pairs a hand survey of the same domain had missed, and it separates
the interesting case from the noise: a pair sharing an anchor while carrying
DIFFERENT urgency labels cannot both be right.

    python review/shared_anchors.py
    python review/shared_anchors.py --split-labels-only

`clinician-defined (no WHO emergency-care anchor)` is a null anchor, not a shared
one - 19 concepts carry it because they have no anchor at all. It is excluded.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ANCHORS = ROOT / "review" / "concept_anchors.csv"
NULL_ANCHOR = "clinician-defined (no WHO emergency-care anchor)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--split-labels-only", action="store_true",
                    help="Only pairs that also disagree on urgency.")
    args = ap.parse_args()

    shared: dict[str, list[tuple[str, str, str]]] = defaultdict(list)
    for row in csv.DictReader(ANCHORS.open(encoding="utf-8")):
        anchor = row["anchor"].strip()
        if anchor and anchor != NULL_ANCHOR:
            shared[anchor].append((row["concept_id"], row["domain"], row["urgency"]))

    groups = {a: m for a, m in shared.items() if len(m) > 1}
    conflicted = {a: m for a, m in groups.items() if len({x[2] for x in m}) > 1}
    for anchor, members in sorted((conflicted if args.split_labels_only else groups).items()):
        labels = {m[2] for m in members}
        note = "  <-- and they disagree on urgency" if len(labels) > 1 else ""
        print(f"{anchor!r}{note}")
        for concept_id, domain, urgency in members:
            print(f"    {concept_id}  {domain:20s} {urgency}")
        print()

    print(f"{len(groups)} anchors are cited by more than one concept; "
          f"{len(conflicted)} of those carry conflicting urgency labels.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
