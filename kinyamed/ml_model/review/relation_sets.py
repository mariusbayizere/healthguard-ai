#!/usr/bin/env python
"""Resolve which relations a concept's third person may be about — one source of truth.

The rulings live in `routine_relation_sets.csv`, keyed by **concept id**. The
generator's `CONCEPT_RELATIONS` is keyed by **phrase string**, because
`vocabulary.py` has no concept ids in it. Nothing bridged the two, so the rulings
sat in a CSV that no code path read, and anything resolving relations fell back
to the domain default without noticing.

That is not a cosmetic gap. Five third-person phrases are already authored under
a ruling that is not in force:

    OB11  NO_RELATIONS     but has an authored {REL} phrase - see CONFLICTS
    CR07  CHILD_RELATIONS  would otherwise expand over all 8
    EX16  CHILD_RELATIONS  the one that was caught by hand
    EX29  CHILD_RELATIONS
    EX31  CHILD_RELATIONS

    python review/relation_sets.py                    # show every ruling and its status
    python review/relation_sets.py --materialise      # emit CONCEPT_RELATIONS for the v2 build

Use `resolve()` for anything that needs a concept's relations — rendering,
counting, review sheets. Use `materialise()` at v2 build time to turn the
rulings into the phrase-keyed map the generator wants.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dataset.vocabulary import (CHILD_RELATIONS, DOMAIN_RELATIONS,  # noqa: E402
                                HOUSEHOLD_RELATIONS, NO_RELATIONS, RELATIONS,
                                REL_PLACEHOLDER)

RULINGS = ROOT / "review" / "routine_relation_sets.csv"
BRIEF = ROOT / "review" / "speaker_brief_kinyarwanda_v2.csv"

ALL_RELATIONS = RELATIONS["kinyarwanda"]

# Named sets a ruling may refer to. A ruling naming anything else is a typo, and
# a typo that silently fell back to the domain default is the whole bug here.
NAMED = {
    "CHILD_RELATIONS": CHILD_RELATIONS,
    "HOUSEHOLD_RELATIONS": HOUSEHOLD_RELATIONS,
    "NO_RELATIONS": NO_RELATIONS,
    "ALL_RELATIONS": ALL_RELATIONS,
}

# Rulings that are deliberately not a relation set. Both mean "do not generate a
# third person from this concept", but for different reasons, and the difference
# is worth keeping: HELD is awaiting a decision, DO_NOT_GENERATE has had one.
HELD = "HELD"
DO_NOT_GENERATE = "NONE — do not generate"
SENTINELS = {HELD, DO_NOT_GENERATE}


def rulings(path: Path = RULINGS) -> dict[str, str]:
    """concept_id -> the raw ruling string, exactly as the speaker recorded it."""
    return {r["concept_id"].strip(): r["relation_set"].strip()
            for r in csv.DictReader(path.open(encoding="utf-8"))}


def resolve(concept_id: str, domain: str, ruled: dict[str, str] | None = None
            ) -> tuple[str, ...] | None:
    """Relations this concept's third person may be about.

    Returns a tuple of relations, or None where no third person should be
    generated at all (a sentinel ruling). Resolution order matches the
    generator's: concept ruling, then domain, then every relation.
    """
    ruled = rulings() if ruled is None else ruled
    name = ruled.get(concept_id)
    if name in SENTINELS:
        return None
    if name:
        if name not in NAMED:
            raise SystemExit(
                f"{concept_id}: ruling {name!r} is not a named relation set. "
                f"Known: {sorted(NAMED)} plus {sorted(SENTINELS)}. A typo here "
                "used to fall through to the domain default silently."
            )
        return NAMED[name]
    return DOMAIN_RELATIONS.get(domain, ALL_RELATIONS)


def _brief_rows(path: Path = BRIEF) -> list[dict]:
    return list(csv.DictReader(path.open(encoding="utf-8")))


def materialise(brief: Path = BRIEF, ruled: dict[str, str] | None = None
                ) -> tuple[dict[str, tuple[str, ...]], list[str]]:
    """Turn concept-keyed rulings into the phrase-keyed map the generator wants.

    Returns `(mapping, conflicts)`. **The caller must treat a non-empty
    `conflicts` as fatal.** A conflict is a ruling that, if applied as written,
    would silently discard an authored phrase's output — which is the failure
    this module exists to prevent, so it is reported rather than obeyed.

    Only concepts whose third-person phrase actually exists can appear in the
    mapping; the map is keyed on the phrase string. Concepts still unauthored
    are not an error, they simply generate nothing yet.
    """
    ruled = rulings() if ruled is None else ruled
    mapping: dict[str, tuple[str, ...]] = {}
    conflicts: list[str] = []

    third = {r["concept_id"]: r for r in _brief_rows(brief) if r["person"] == "third"}

    for concept_id, name in ruled.items():
        row = third.get(concept_id)
        phrase = (row or {}).get("your_phrasing", "").strip()
        applies = ((row or {}).get("applies") or "yes").strip().lower()
        authored = bool(phrase) and applies != "no"

        if name in SENTINELS:
            if authored:
                conflicts.append(
                    f"{concept_id}: ruled {name!r}, which generates no third person, "
                    f"but a third-person phrase is authored ({(row or {}).get('source','?')}): "
                    f"{phrase!r}. Applying the ruling would discard it silently. "
                    "Rule the conflict before materialising."
                )
            continue

        if not authored:
            continue  # nothing to key on yet; not an error

        allowed = resolve(concept_id, row["domain"], ruled)
        if allowed is None:
            continue
        if len(allowed) == 0:
            # NO_RELATIONS is a named set, not a sentinel, so it reaches here.
            # An empty set with an authored phrase is the same silent deletion
            # as a sentinel ruling: the phrase would map to () and contribute
            # nothing, with no error. Do not let it through.
            conflicts.append(
                f"{concept_id}: ruled NO_RELATIONS, so it generates no third person, "
                f"but a third-person phrase is authored ({row.get('source','?')}): "
                f"{phrase!r}. Mapping it would zero the phrase's output silently. "
                "Either the ruling or the phrase is wrong — rule it before materialising."
            )
            continue
        if REL_PLACEHOLDER not in phrase:
            conflicts.append(
                f"{concept_id}: ruled {name!r} but its third-person phrase carries no "
                f"{REL_PLACEHOLDER}, so the ruling can never apply: {phrase!r}"
            )
            continue
        if len(allowed) and not [r for r in ALL_RELATIONS if r in allowed]:
            conflicts.append(
                f"{concept_id}: ruling {name!r} names no relation that exists in "
                "RELATIONS['kinyarwanda']."
            )
            continue
        mapping[phrase] = tuple(allowed)

    return mapping, conflicts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--materialise", action="store_true",
                    help="Emit CONCEPT_RELATIONS for the v2 build.")
    args = ap.parse_args()

    ruled = rulings()
    mapping, conflicts = materialise(ruled=ruled)
    third = {r["concept_id"]: r for r in _brief_rows() if r["person"] == "third"}

    if not args.materialise:
        print(f"{len(ruled)} rulings in {RULINGS.name}\n")
        for concept_id, name in ruled.items():
            row = third.get(concept_id, {})
            phrase = (row.get("your_phrasing") or "").strip()
            applies = (row.get("applies") or "yes").lower()
            if name in SENTINELS:
                state = "no third person"
            elif phrase and applies != "no":
                state = f"IN FORCE on {len(resolve(concept_id, row['domain'], ruled))} relations"
            elif applies == "no":
                state = "row is applies=no"
            else:
                state = "phrase not authored yet"
            print(f"  {concept_id:6} {name:22} {state}")
        print()

    if conflicts:
        print(f"{len(conflicts)} CONFLICT(S) — these block materialisation:\n",
              file=sys.stderr)
        for c in conflicts:
            print(f"  ! {c}\n", file=sys.stderr)

    if args.materialise:
        if conflicts:
            print("refusing to emit while conflicts stand", file=sys.stderr)
            return 1
        print("CONCEPT_RELATIONS: dict[str, tuple[str, ...]] = {")
        for phrase, rels in sorted(mapping.items()):
            print(f"    {phrase!r}:")
            print(f"        {rels!r},")
        print("}")
    else:
        print(f"{len(mapping)} phrase(s) ready to materialise, "
              f"{len(conflicts)} conflict(s) blocking.")
    return 1 if conflicts else 0


if __name__ == "__main__":
    raise SystemExit(main())
