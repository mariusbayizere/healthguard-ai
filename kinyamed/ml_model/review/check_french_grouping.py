#!/usr/bin/env python
"""Run the project's phrase-grouping rule over the French candidates.

The French half of what `check_english_grouping.py` does for English, and it
imports the same rule from `dataset/split_dataset.py`, so it cannot drift from
what the splitter actually does.

**French is the language most likely to produce a spurious union of the three.**
Kinyarwanda packs meaning into inflected verbs; English packs some of it into
function words; French packs more into function words than either - `de`, `la`,
`a`, `que`, `et`, `je`, `ne`, `pas` recur in nearly every phrase, and the
ordered-subsequence rule counts them. A short French phrase falls inside a long
one more easily than its English counterpart does, so the shortest-candidate
floor printed at the end is worth reading every run.

    python review/check_french_grouping.py

Run it after every batch.
"""

from __future__ import annotations

import csv
import sys
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dataset.split_dataset import _is_subsequence, _match_form, _words  # noqa: E402

BRIEF = ROOT / "review" / "speaker_brief_french_v2.csv"

# Collisions the English MIRRORS from the Kinyarwanda on purpose, rather than
# wording around. Each is one of the five multi-concept phrase groups in
# review/kinyarwanda-phrase-group-collisions.md, which the Kinyarwanda session is
# working through. Contorting the English to avoid a source-side collision buys
# nothing and goes unmotivated the moment the source is fixed — the OB09 reword
# is the worked example of that.
#
# Listing them here keeps the check a signal. Without it this tool is red
# forever and the next real collision hides in the noise. DELETE AN ENTRY when
# the Kinyarwanda pair is reworded, and let the check confirm it.
# EMPTY, and that is the point. The one entry it held - EX09 inside CC03 - was
# retired on 2026-09-05 when the Kinyarwanda session reworded EX09, dissolving the
# collision at source. The English was reworded to track it and the check went
# clean on its own, which is the loop this list exists to close.
INHERITED: dict[tuple[str, str], str] = {}


def main() -> int:
    rows = list(csv.DictReader(BRIEF.open(encoding="utf-8")))
    # applies=no rows contribute no phrase to v2, so a collision with one is not
    # a collision. Including them reported EX32's own first person - stale v1 text
    # on a dropped row - as containing EX32's third.
    candidates = {f"{r['concept_id']}/{r['person']}": r["suggested_french"].strip()
                  for r in rows
                  if r["suggested_french"].strip() and r["applies"] != "no"}
    # The pool is the v2 English inventory, nothing else. v1 strings that survive
    # into v2 are here already, as the candidates of the rows carrying them; the
    # ones that do not survive cannot collide with anything, because v2 replaces
    # v1's SYMPTOMS rather than joining it. Including them reported a frozen v1
    # phrase on an applies=no row as colliding with its own concept's v2 draft.
    # v1's own partition is guarded by `make verify-full`, not by this.
    pool = candidates

    # A concept's own two persons belong in one group and are declared into one by
    # PHRASE_CONCEPTS regardless, so a union between them is not a finding. With
    # {REL} stripped, a third person is very often a subsequence of its own first
    # ("cannot finish a sentence..." inside "I cannot finish a sentence..."), and
    # reporting those would bury the cross-concept unions that are the point.
    def same_concept(ka: str, kb: str) -> bool:
        return ka.split("/")[0] == kb.split("/")[0]

    def inherited(ka: str, kb: str) -> str | None:
        a, b = ka.split("/")[0], kb.split("/")[0]
        return INHERITED.get((a, b)) or INHERITED.get((b, a))

    unions, contained, within = [], [], 0
    mirrored: list[tuple[str, str, str]] = []
    for (ka, a), (kb, b) in combinations(pool.items(), 2):
        fa, fb = _match_form(a), _match_form(b)
        wa, wb = _words(fa), _words(fb)
        joined = (fa != fb and (fa in fb or fb in fa)) or (
            wa and wb and (_is_subsequence(wa, wb) or _is_subsequence(wb, wa)))
        if not joined:
            continue
        if same_concept(ka, kb):
            within += 1
            continue
        why = inherited(ka, kb)
        if why:
            mirrored.append((ka, kb, why))
            continue
        if fa != fb and (fa in fb or fb in fa):
            contained.append((ka, a, kb, b) if fa in fb else (kb, b, ka, a))
        elif _is_subsequence(wa, wb):
            unions.append((ka, a, kb, b))
        else:
            unions.append((kb, b, ka, a))

    print(f"{len(pool)} French phrases in the v2 inventory so far")
    print(f"{within} unions between a concept's own two persons — expected, "
          f"and declared by PHRASE_CONCEPTS anyway")
    print(f"{len(mirrored)} mirrored from the Kinyarwanda on purpose:")
    for ka, kb, why in mirrored:
        print(f"   {ka} / {kb} — {why}")
    print()
    for label, pairs in (("containment", contained), ("ordered subsequence", unions)):
        print(f"{label}: {len(pairs)}")
        for ki, inner, ko, outer in pairs:
            print(f"   {ki:14s} {inner!r}")
            print(f"       inside {ko}: {outer!r}")
        print()

    # A short phrase is what makes a subsequence union likely, so watch the floor
    # rather than waiting for the union to appear.
    shortest = sorted(((len(_words(_match_form(p))), k, p) for k, p in candidates.items()))[:5]
    print("shortest candidates — the ones most likely to fall inside another:")
    for n, key, phrase in shortest:
        print(f"   {n:2d} words  {key:14s} {phrase!r}")
    return 1 if unions or contained else 0


if __name__ == "__main__":
    raise SystemExit(main())
