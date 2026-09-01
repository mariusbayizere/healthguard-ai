#!/usr/bin/env python
"""Divide a brief between two authors while keeping the blind agreement measure valid.

The blind arm needs both authors to phrase the SAME concepts independently. If the
work is simply halved there is no overlap and nothing to compare, so agreement
cannot be measured at all.

This carves out a stratified overlap set that both authors write, then splits the
remainder. The overlap rows are not marked in either author's file: knowing which
items are scored changes how people write them. Both authors should still be told
at the outset that a fifth of the work overlaps and is used to measure agreement —
transparent about the design, silent about which rows.

    python review/split_authoring.py review/speaker_brief_kinyarwanda_v2.csv \\
        --overlap-fraction 0.2
"""

from __future__ import annotations

import argparse
import collections
import csv
import random
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("brief", type=Path)
    ap.add_argument("--overlap-fraction", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rows = list(csv.DictReader(args.brief.open(encoding="utf-8")))
    by_concept: dict[str, list[dict]] = collections.OrderedDict()
    for r in rows:
        by_concept.setdefault(r["concept_id"], []).append(r)
    concepts = list(by_concept)

    # Stratify the overlap by domain so agreement is not concentrated in one
    # clinical area, and seed it so the choice is reproducible and not made
    # after seeing the results.
    rng = random.Random(args.seed)
    per_domain: dict[str, list[str]] = collections.defaultdict(list)
    for cid, rs in by_concept.items():
        per_domain[rs[0]["domain"]].append(cid)

    overlap: set[str] = set()
    for dom, cids in sorted(per_domain.items()):
        k = max(1, round(len(cids) * args.overlap_fraction))
        overlap.update(rng.sample(sorted(cids), k))

    rest = [c for c in concepts if c not in overlap]
    rng.shuffle(rest)
    half = len(rest) // 2
    a_only, b_only = set(rest[:half]), set(rest[half:])

    for name, own in (("A", a_only), ("B", b_only)):
        assigned = overlap | own
        out = [r for cid in concepts if cid in assigned for r in by_concept[cid]]
        # Author B starts clean: A's first-pass text must not leak into the
        # overlap rows, or the blind arm is worthless.
        if name == "B":
            out = [{**r, "your_phrasing": "", "notes": ""} for r in out]
        path = args.brief.with_name(args.brief.stem + f"_author{name}.csv")
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(out[0])); w.writeheader(); w.writerows(out)
        print(f"  {path.name:<46} {len(assigned):>3} concepts, {len(out):>3} rows "
              f"({len(overlap)} shared)")

    key = args.brief.with_name(args.brief.stem + "_OVERLAP_KEY.csv")
    with key.open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["concept_id", "domain"])
        for cid in concepts:
            if cid in overlap:
                w.writerow([cid, by_concept[cid][0]["domain"]])
    print(f"  {key.name:<46} {len(overlap)} concepts — DO NOT SEND to either author")
    print(f"\n  coverage: {len(overlap | a_only | b_only)} of {len(concepts)} concepts, "
          f"no gaps: {len(overlap | a_only | b_only) == len(concepts)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
