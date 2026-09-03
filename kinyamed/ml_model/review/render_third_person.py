#!/usr/bin/env python
"""Render a domain's third-person rows across the relations each concept ACTUALLY allows.

The render CSVs used for ruling were produced ad hoc, and one of them was wrong:
`gastrointestinal_third_render.csv` showed EX16 across all eight relations when
its ruling is `CHILD_RELATIONS`, five. Five of those eight rows were relations
the speaker's own ruling excludes, and they were presented for ruling anyway.

That happened because the ad-hoc render consulted `CONCEPT_RELATIONS`, which is
empty, instead of the rulings in `routine_relation_sets.csv`. This script
resolves through `relation_sets.resolve()` — the same function the v2 build
materialises from — so a render cannot disagree with a ruling again.

    python review/render_third_person.py gastrointestinal
    python review/render_third_person.py haemorrhage_trauma -o review/ht_third_render.csv

Substitution mirrors `build_families` exactly, including the lowercasing rule for
a mid-sentence relation. It is duplicated rather than imported because the
generator does it inline inside a family loop; `tests/test_relation_sets.py`
pins the two together so they cannot drift.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "review"))

from dataset.vocabulary import REL_PLACEHOLDER  # noqa: E402
from relation_sets import resolve, rulings  # noqa: E402

BRIEF = ROOT / "review" / "speaker_brief_kinyarwanda_v2.csv"


def render(phrase: str, relation: str) -> str:
    """Substitute one relation into a {REL} phrase, as build_families does.

    A relation is proper-noun shaped and written capitalised, but mid-sentence it
    is not a sentence start: "Iyo umwana wanjye ahumeka", not "Iyo Umwana wanjye".
    """
    head = phrase.startswith(REL_PLACEHOLDER)
    return phrase.replace(REL_PLACEHOLDER,
                          relation if head else relation[0].lower() + relation[1:])


def rows_for(domain: str, brief: Path = BRIEF) -> list[dict]:
    ruled = rulings()
    out: list[dict] = []
    for r in csv.DictReader(brief.open(encoding="utf-8")):
        if r["domain"] != domain or r["person"] != "third":
            continue
        if (r.get("applies") or "yes").strip().lower() == "no":
            continue
        # Rule whatever text is on the row: an authored phrase if there is one,
        # otherwise the draft awaiting a ruling.
        phrase = (r["your_phrasing"] or "").strip() or (r["suggested_kinyarwanda"] or "").strip()
        if not phrase:
            continue
        if REL_PLACEHOLDER not in phrase:
            continue
        allowed = resolve(r["concept_id"], domain, ruled)
        if allowed is None:
            continue  # HELD or do-not-generate: nothing to rule
        for relation in allowed:
            out.append({
                "concept_id": r["concept_id"],
                "relation": relation,
                "rendered": render(phrase, relation),
                "your_ruling": "",
            })
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("domain")
    ap.add_argument("-o", "--out", type=Path,
                    help="Write a CSV here. Without it, print to stdout.")
    args = ap.parse_args()

    rows = rows_for(args.domain)
    if not rows:
        print(f"no third-person {args.domain} rows with a {REL_PLACEHOLDER} phrase",
              file=sys.stderr)
        return 1

    ruled = rulings()
    by_concept: dict[str, int] = {}
    for r in rows:
        by_concept[r["concept_id"]] = by_concept.get(r["concept_id"], 0) + 1

    if args.out:
        from dataset.atomicio import atomic_write
        fields = ["concept_id", "relation", "rendered", "your_ruling"]
        with atomic_write(args.out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print(f"{len(rows)} rows -> {args.out}")
    else:
        for r in rows:
            print(f"  {r['concept_id']:6} {r['relation']:<22} {r['rendered']}")

    print(f"\n{len(by_concept)} concept(s), {len(rows)} rows:", file=sys.stderr)
    for cid, n in sorted(by_concept.items()):
        note = f"  <- ruled {ruled[cid]}" if cid in ruled else ""
        print(f"  {cid:6} {n} relation(s){note}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
