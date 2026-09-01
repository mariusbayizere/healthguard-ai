#!/usr/bin/env python
"""How far through a brief you are, and what is left.

Safe to run on a partially-filled file at any point. Reads only; changes nothing.

    python review/progress.py review/speaker_brief_kinyarwanda_v2.csv
"""

from __future__ import annotations

import argparse
import collections
import csv
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
    filled = lambda r: bool((r.get(args.column) or "").strip())
    done, total = sum(map(filled, rows)), len(rows)

    print(f"{args.brief.name}")
    print(f"  {bar(done, total)}  {done}/{total}  ({done/total:.0%})\n")

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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
