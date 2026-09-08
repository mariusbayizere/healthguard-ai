"""Swahili relation sets — SPEAKER-AUTHORED terms, mirrored set membership.

STAGING FILE, NOT THE INTENDED HOME, exactly as `english_relations.py` and
`french_relations.py` are. These belong beside the Kinyarwanda sets in
`dataset/vocabulary.py`; they are here because `dataset/` is not edited while
v2 is frozen. They land in v3.

PROVENANCE IS SPLIT, AND THE SPLIT MATTERS
-------------------------------------------
- The WORDS are speaker-authored. A Kiswahili speaker returned all twelve with
  regional variants and notes on 2026-09-08. Unlike the English and French
  staging files, whose wording came from v1's machine-drafted SUBJECTS slot,
  nothing here is a machine draft.
- The SET MEMBERSHIP is the Kinyarwanda speaker's ruling, mirrored one for one
  in the same order. No membership decision was re-made here.

So a Swahili third-person row carries speaker-authored relation wording under a
mirrored membership ruling, and the paper should say exactly that rather than
calling the whole thing speaker-authored or machine_reviewed.
"""

from __future__ import annotations

# The twelve, as returned. `VARIANT` holds the regional alternative where the
# speaker gave a different one; where they gave the same string twice it is
# recorded as no variant rather than as a duplicate.
TERMS: dict[str, str] = {
    "My child": "Mwanangu",
    "My wife": "Mke wangu",
    "My husband": "Mume wangu",
    "My mother": "Mama yangu",
    "My father": "Baba yangu",
    "My sister": "Dada yangu",
    "My neighbour": "Jirani yangu",
    "My grandmother": "Bibi yangu",
    "My son": "Mwanangu wa kiume",
    "My daughter": "Mwanangu wa kike",
    "My grandchild": "Mjukuu wangu",
    "My neighbour's child": "Mtoto wa jirani yangu",
}

VARIANT: dict[str, str] = {
    "My child": "Mtoto wangu",
    "My grandmother": "Nyanya yangu",
    "My son": "Mtoto wangu wa kiume",
    "My daughter": "Mtoto wangu wa kike",
}

# NOT YET RULED: whether the variants generate as additional relation instances
# or are recorded only. Generating both would roughly double the third-person
# instance count for CHILD_RELATIONS and change corpus sizing, so it is a
# decision, not a default. See docs/blocked.md.
GENERATE_VARIANTS = False

# SEVEN, NOT EIGHT. Kinyarwanda's eighth relation is `Umukecuru`, a general term
# for an ELDERLY WOMAN rather than for the speaker's own grandmother. v1's
# English rendered it "My grandmother", so that is the row the speaker was given,
# and they returned `Bibi yangu` / `Nyanya yangu` -- both possessive, both
# meaning the speaker's grandmother. That answers a question we did not ask.
#
# RULED 2026-09-08. THE LINE IS REFERENT, NOT CORRECTNESS: `Nyanya` and `Bibi`
# name the same person, so both are real variants of a given term and both are
# kept. `Umukecuru` names a DIFFERENT person, and no term for that person was
# returned, so the slot is empty. Keeping a variant and leaving an unfilled slot
# unfilled are the same principle, not opposing ones.
# Drop the slot rather than map grandmother onto elderly woman. No Kiswahili elderly-woman term was supplied and inventing one would
# breach standing rule 1. The returned words are kept in TERMS and in the
# worksheet -- they are not discarded, they are simply not wired into a set that
# means something else.
ALL_RELATIONS: tuple[str, ...] = tuple(
    TERMS[k] for k in ("My child", "My wife", "My husband", "My mother",
                       "My father", "My sister", "My neighbour"))

CHILD_RELATIONS_SW: tuple[str, ...] = tuple(
    TERMS[k] for k in ("My child", "My son", "My daughter", "My grandchild",
                       "My neighbour's child"))

HOUSEHOLD_RELATIONS_SW: tuple[str, ...] = tuple(
    TERMS[k] for k in ("My wife", "My husband", "My mother", "My father",
                       "My sister", "My child"))

ADULT_RELATIONS_SW: tuple[str, ...] = tuple(
    r for r in ALL_RELATIONS if r != TERMS["My child"])

NO_RELATIONS_SW: tuple[str, ...] = ()

# FLAGGED, NOT DECIDED, AND NOW CONFIRMED IN A THIRD LANGUAGE. The speaker's own
# note on this term is "Haina jinsia" — it has no gender. The Kinyarwanda
# speaker ruled the neighbour INTO the obstetric set knowingly, and Kinyarwanda
# cannot mark gender on it either. English resolves it with a later "she" and
# French with "voisine"; Swahili has neither route, so the restriction "only
# relations that can be pregnant" is weaker here than in any other arm.
# Inherited rather than narrowed, because narrowing is the Kinyarwanda speaker's
# ruling to change.
DOMAIN_RELATIONS_SW: dict[str, tuple[str, ...]] = {
    "obstetric": tuple(TERMS[k] for k in ("My wife", "My mother", "My sister",
                                          "My neighbour")),
    "paediatric": CHILD_RELATIONS_SW,
}

OBSTETRIC_RELATIONS_NO_MOTHER: tuple[str, ...] = tuple(
    r for r in DOMAIN_RELATIONS_SW["obstetric"] if r != TERMS["My mother"])

NAMED: dict[str, tuple[str, ...]] = {
    "ALL_RELATIONS": ALL_RELATIONS,
    "CHILD_RELATIONS": CHILD_RELATIONS_SW,
    "HOUSEHOLD_RELATIONS": HOUSEHOLD_RELATIONS_SW,
    "ADULT_RELATIONS": ADULT_RELATIONS_SW,
    "OBSTETRIC_RELATIONS": DOMAIN_RELATIONS_SW["obstetric"],
    "OBSTETRIC_RELATIONS_NO_MOTHER": OBSTETRIC_RELATIONS_NO_MOTHER,
    "NO_RELATIONS": NO_RELATIONS_SW,
}


def check_mirrors_kinyarwanda() -> list[str]:
    """Every set must have the same size as the Kinyarwanda ruling it mirrors.

    Size is the only property checkable without a translation memory, and it
    catches the failure that matters: a set that silently gained or lost a
    member relative to the ruling it claims to mirror.
    """
    # ALL and ADULT are one smaller than the Kinyarwanda rulings BY DECISION,
    # not by drift: the Umukecuru slot is unfilled. Declared here so the mirror
    # check still fails on an accidental change while passing on this one.
    expected = {"ALL_RELATIONS": 7, "CHILD_RELATIONS": 5, "HOUSEHOLD_RELATIONS": 6,
                "ADULT_RELATIONS": 6, "OBSTETRIC_RELATIONS": 4}
    DELIBERATE_DIVERGENCE = {"ALL_RELATIONS": "Umukecuru slot unfilled: no "
                             "Kiswahili elderly-woman term was supplied",
                             "ADULT_RELATIONS": "follows ALL_RELATIONS"}
    problems = [f"{name}: {len(NAMED[name])} members, Kinyarwanda ruling has {n}"
                for name, n in expected.items() if len(NAMED[name]) != n]
    if ADULT_RELATIONS_SW != tuple(r for r in ALL_RELATIONS if r != TERMS["My child"]):
        problems.append("ADULT_RELATIONS must be ALL_RELATIONS minus the child, in order")
    if len(set(TERMS.values())) != len(TERMS):
        problems.append("two relations share a surface form; they would be "
                        "indistinguishable after substitution")
    return problems


def containment_within_sets() -> list[str]:
    """Relations inside one set where one term contains another.

    NOT a leakage failure: both expansions of one phrase belong to that phrase's
    group, so the holdout cannot split them. It is reported because it affects
    NEAR-DUPLICATE measurement at generation time -- two rows differing only by
    "wa kiume" are close neighbours, and the corpus should know how many it has.
    """
    out = []
    for name, members in NAMED.items():
        for a in members:
            for b in members:
                if a != b and a in b:
                    out.append(f"{name}: {a!r} is contained in {b!r}")
    return out


if __name__ == "__main__":
    issues = check_mirrors_kinyarwanda()
    for issue in issues:
        print(f"  MIRROR: {issue}")
    print("Swahili relation sets mirror the Kinyarwanda rulings"
          if not issues else f"{len(issues)} mirror problems")
    for line in containment_within_sets():
        print(f"  CONTAINMENT: {line}")
