#!/usr/bin/env python
"""Read a brief into the two phrase-grouping declarations: PHRASE_VARIANTS and PHRASE_CONCEPTS.

A concept may be said two ways. The corpus wants both — a different patient
says the same thing differently, which is the variety the phrase inventory is
for — but it must carry them as one phrase group, or the phrase holdout can
train on one phrasing and evaluate on the other.

`dataset.vocabulary.PHRASE_VARIANTS` is that declaration and
`split_dataset.phrase_components` unions on it. This is the step that fills it
from what the speaker actually authored.

    python review/second_phrasings.py review/speaker_brief_kinyarwanda_v2.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

PRIMARY = "your_phrasing"
SECOND = "second_phrasing_optional"


def second_phrasings(brief: Path) -> dict[str, str]:
    """{second phrasing: primary phrasing} for every row carrying both."""
    pairs: dict[str, str] = {}
    with brief.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if (row.get("applies") or "yes").strip().lower() == "no":
                continue
            primary = (row.get(PRIMARY) or "").strip()
            second = (row.get(SECOND) or "").strip()
            if not second:
                continue
            if not primary:
                raise SystemExit(
                    f"{row.get('concept_id')} {row.get('person')}: a second phrasing "
                    f"with no primary. The pairing has nothing to join, and the "
                    "second would generate as an unrelated phrase."
                )
            if second == primary:
                raise SystemExit(
                    f"{row.get('concept_id')} {row.get('person')}: the second phrasing "
                    "is identical to the primary."
                )
            if second in pairs and pairs[second] != primary:
                raise SystemExit(
                    f"{second!r} is declared against two different primaries: "
                    f"{pairs[second]!r} and {primary!r}."
                )
            pairs[second] = primary
    return pairs


def concept_phrases(brief: Path) -> dict[str, str]:
    """{phrase: concept_id} for every authored phrase, both persons.

    Everything said about one concept must land in one phrase group. A similarity
    rule cannot do this: a third-person phrase begins with {REL} and a first-person
    one with a letter, so their shared prefix is 0 by construction and containment
    fails on the verb morphology. 60 of 61 concepts were split before this existed.

    Second phrasings are included too, so a concept's variant joins the same group
    by both routes - belt and braces, and it costs nothing.
    """
    mapping: dict[str, str] = {}
    with brief.open(encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if (row.get("applies") or "yes").strip().lower() == "no":
                continue
            concept = (row.get("concept_id") or "").strip()
            if not concept:
                continue
            for column in (PRIMARY, SECOND):
                phrase = (row.get(column) or "").strip()
                if not phrase:
                    continue
                if mapping.setdefault(phrase, concept) != concept:
                    raise SystemExit(
                        f"{phrase!r} is claimed by both {mapping[phrase]!r} and "
                        f"{concept!r}. One phrase cannot belong to two concepts; "
                        "if they are the same concept, collapse them."
                    )
    return mapping


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("brief", type=Path)
    args = ap.parse_args()

    concepts = concept_phrases(args.brief)
    groups = len(set(concepts.values()))
    print(f"PHRASE_CONCEPTS: {len(concepts)} phrase(s) across {groups} concept(s) "
          f"-> {len(concepts) - groups} union(s) a similarity rule cannot make\n")

    pairs = second_phrasings(args.brief)
    if not pairs:
        print(f"{args.brief.name}: no second phrasings recorded.")
        return 0
    print(f"{args.brief.name}: {len(pairs)} second phrasing(s)\n")
    print("PHRASE_VARIANTS = {")
    for second, primary in sorted(pairs.items()):
        print(f"    {second!r}:\n        {primary!r},")
    print("}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
