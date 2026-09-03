#!/usr/bin/env python
"""How far through a brief you are, and what is left.

Safe to run on a partially-filled file at any point. Reads only; changes nothing.

    python review/progress.py review/speaker_brief_kinyarwanda_v2.csv
"""

from __future__ import annotations

import argparse
import collections
import csv
import sys
from pathlib import Path


def bar(done: int, total: int, width: int = 28) -> str:
    filled = 0 if not total else round(width * done / total)
    return "[" + "#" * filled + "." * (width - filled) + "]"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("brief", type=Path)
    ap.add_argument("--column", default="your_phrasing")
    args = ap.parse_args()

    rows = list(csv.DictReader(args.brief.open(encoding="utf-8")))
    # A row marked applies=no is deliberately empty, not outstanding work.
    # Without this the tracker can never reach 100% on a brief where some
    # concepts only need one person.
    na = lambda r: (r.get("applies") or "yes").strip().lower() == "no"
    filled = lambda r: bool((r.get(args.column) or "").strip()) or na(r)
    done, total = sum(map(filled, rows)), len(rows)
    n_na = sum(map(na, rows))

    print(f"{args.brief.name}")
    print(f"  {bar(done, total)}  {done}/{total}  ({done/total:.0%})"
          + (f"   incl. {n_na} marked not-applicable" if n_na else "") + "\n")

    print(f"  {'domain':<22}{'done':>6}{'left':>6}")
    print("  " + "-" * 34)
    per = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        cell = per[r["domain"]]
        cell[0 if filled(r) else 1] += 1
    for dom in sorted(per):
        d, left = per[dom]
        flag = "  <- next" if left and all(per[x][1] == 0 for x in sorted(per) if x < dom) else ""
        print(f"  {dom:<22}{d:>6}{left:>6}{flag}")

    print()
    for field in ("person", "form"):
        if field not in rows[0]:
            continue
        c = collections.Counter((r.get(field) or "(blank)") for r in rows if filled(r))
        print(f"  {field:<8} of completed rows: {dict(c)}")

    undeclared = [r for r in rows if filled(r) and not (r.get("form") or "").strip()]
    if undeclared:
        print(f"\n  {len(undeclared)} completed rows have no form declared — "
              "the generator needs it to choose the frame")

    if done < total:
        left = total - done
        print(f"\n  {left} rows left. At 2-3 minutes each that is "
              f"{left*2//60}h{left*2%60:02d}m to {left*3//60}h{left*3%60:02d}m.")
    else:
        print("\n  Complete. Run the linter, then review/make_second_review.py.")

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from provenance import (CATEGORIES, LABELS, NEWLY_COMPOSED,
                                SPEAKERS_OWN_WORDS, classified)
        auth = [(r, c) for r, c in classified(args.brief)
                if (r.get("your_phrasing") or "").strip()
                and (r.get("applies") or "yes").strip().lower() != "no"]
        if auth:
            counts = collections.Counter(c for _, c in auth)
            n_auth = len(auth)
            print("\n  provenance of the authored phrases")
            for category in CATEGORIES:
                if counts.get(category):
                    n = counts[category]
                    print(f"    {n:3}  {100 * n / n_auth:5.1f}%  {LABELS[category]}")
            own = sum(counts.get(c, 0) for c in SPEAKERS_OWN_WORDS)
            fresh = sum(counts.get(c, 0) for c in NEWLY_COMPOSED)
            print(f"    speaker's own words {own}/{n_auth} = {100 * own / n_auth:.0f}%"
                  f"   |   newly composed {fresh}/{n_auth} = {100 * fresh / n_auth:.0f}%")
    except Exception as exc:                      # a report must never block the count
        print(f"\n  (provenance report unavailable: {exc})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
