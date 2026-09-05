#!/usr/bin/env python
"""English relation sets, held here until they can land in `dataset/vocabulary.py`.

THIS IS A STAGING FILE, NOT THE INTENDED HOME. The relation sets belong beside
the Kinyarwanda ones in `dataset/vocabulary.py`; they are here because English
work must not touch `dataset/` while Kinyarwanda authoring is in flight. The
handover note in `review/english-review-pass.md` carries the exact diff to apply.

Nothing in `dataset/` imports this, so nothing generates from it. It exists so
that the English brief can record which relation set a third-person row expands
over, and so the wording is decided and reviewable now rather than invented at
build time.

MIRRORED, NOT RE-DECIDED. Every set is the speaker's Kinyarwanda ruling with the
members translated one for one, in the same order, using the wording v1's own
SUBJECTS slot already chose - Umukecuru is "My grandmother" there, so it is that
here rather than a fresh translation.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dataset.vocabulary import (  # noqa: E402
    ADULT_RELATIONS,
    CHILD_RELATIONS,
    DOMAIN_RELATIONS,
    HOUSEHOLD_RELATIONS,
    RELATIONS,
)

# The eight, in the Kinyarwanda order.
#
# Every English relation is third-person singular, so one authored sentence fits
# all eight with no verb agreement to vary. That is why mirroring the person
# split is nearly free in English and expensive in Kinyarwanda, where the object
# marker changes with the person - CR01 and CR05 are held on exactly that.
ALL_RELATIONS: tuple[str, ...] = (
    "My child", "My wife", "My husband", "My mother",
    "My father", "My sister", "My neighbour", "My grandmother",
)

CHILD_RELATIONS_EN: tuple[str, ...] = (
    "My child", "My son", "My daughter",
    "My grandchild", "My neighbour's child",
)

HOUSEHOLD_RELATIONS_EN: tuple[str, ...] = (
    "My wife", "My husband", "My mother", "My father",
    "My sister", "My child",
)

ADULT_RELATIONS_EN: tuple[str, ...] = (
    "My wife", "My husband", "My mother", "My father",
    "My sister", "My neighbour", "My grandmother",
)

NO_RELATIONS_EN: tuple[str, ...] = ()

# The speaker's domain rulings, mirrored.
#
# FLAGGED, NOT DECIDED: "My neighbour" is gender-neutral in English, exactly as
# Umuturanyi wanjye is in Kinyarwanda, and the speaker still ruled it into the
# obstetric four. English inherits the ruling rather than quietly narrowing it.
# What English adds is a way to resolve it that Kinyarwanda does not have - a
# feminine pronoun later in the sentence - which is why the obstetric drafts use
# "she"/"her". That is a drafting choice inside the ruling, not a change to it.
DOMAIN_RELATIONS_EN: dict[str, tuple[str, ...]] = {
    "obstetric": ("My wife", "My mother", "My sister", "My neighbour"),
    "paediatric": CHILD_RELATIONS_EN,
}

# RULED 2026-09-04: OB12 (breastfeeding advice) drops the mother. With Mama
# substituted, "{REL} wants advice on how to breastfeed her baby" says the
# speaker's own mother has recently delivered. Derived from the obstetric four
# rather than retyped, so it cannot drift from them.
#
# The ruling is about the CONCEPT, so it belongs in the Kinyarwanda
# `routine_relation_sets.csv` too — see PENDING_RULINGS below.
OBSTETRIC_RELATIONS_NO_MOTHER: tuple[str, ...] = tuple(
    r for r in DOMAIN_RELATIONS_EN["obstetric"] if r != "My mother"
)

# Rulings made during the English pass that have NOT yet been written into
# `review/routine_relation_sets.csv`, which is the Kinyarwanda record and this
# session must not edit. This map is a TEMPORARY second source of truth and is
# exactly the drift trap this project keeps hitting - empty it as soon as the
# ruling lands in the CSV, and delete the map when it is empty for good.
PENDING_RULINGS: dict[str, str] = {
    "OB12": "OBSTETRIC_RELATIONS_NO_MOTHER",
}

# RULED 2026-09-04: SINGULAR "THEIR" ON EVERY NON-OBSTETRIC THIRD PERSON.
#
# A third-person phrase that needs a possessive forces a gender choice English
# cannot avoid and Kinyarwanda never faces - `umunwa we` is neutral. ALL_RELATIONS
# spans both genders, so "his" or "her" is wrong for half the expansions.
#
# Singular "their" is the ruling. It reads naturally after "My child" and slightly
# oddly after "My father"; the alternatives were dropping the possessive, which is
# not natural English, or splitting each phrase per gender, which doubles a phrase
# for no clinical gain.
#
# OBSTETRIC IS THE EXCEPTION AND KEEPS "she": there the gendered pronoun is not a
# compromise but the one place English can express a restriction Kinyarwanda can
# only imply - it resolves the gender-neutral "My neighbour" to a patient who can
# be pregnant.
THIRD_PERSON_POSSESSIVE = "their"
OBSTETRIC_POSSESSIVE = "her"

NAMED: dict[str, tuple[str, ...]] = {
    "OBSTETRIC_RELATIONS_NO_MOTHER": OBSTETRIC_RELATIONS_NO_MOTHER,
    "ALL_RELATIONS": ALL_RELATIONS,
    "CHILD_RELATIONS": CHILD_RELATIONS_EN,
    "HOUSEHOLD_RELATIONS": HOUSEHOLD_RELATIONS_EN,
    "ADULT_RELATIONS": ADULT_RELATIONS_EN,
    "OBSTETRIC_RELATIONS": DOMAIN_RELATIONS_EN["obstetric"],
    "NO_RELATIONS": NO_RELATIONS_EN,
}


def check_mirrors_kinyarwanda() -> list[str]:
    """Every English set must have the same size as the Kinyarwanda one it mirrors.

    Size is the only property checkable without a translation memory, and it is
    the one that catches the failure that matters: a set that silently gained or
    lost a member relative to the ruling it claims to mirror.
    """
    pairs = [
        ("ALL_RELATIONS", ALL_RELATIONS, RELATIONS["kinyarwanda"]),
        ("CHILD_RELATIONS", CHILD_RELATIONS_EN, CHILD_RELATIONS),
        ("HOUSEHOLD_RELATIONS", HOUSEHOLD_RELATIONS_EN, HOUSEHOLD_RELATIONS),
        ("ADULT_RELATIONS", ADULT_RELATIONS_EN, ADULT_RELATIONS),
        ("OBSTETRIC_RELATIONS", DOMAIN_RELATIONS_EN["obstetric"],
         DOMAIN_RELATIONS["obstetric"]),
    ]
    problems = [
        f"{name}: English has {len(en)} members, Kinyarwanda has {len(ky)}"
        for name, en, ky in pairs if len(en) != len(ky)
    ]
    # ADULT_RELATIONS is pinned as ALL minus the child, in order, on the
    # Kinyarwanda side. The same must hold here or the two drift apart.
    expected = tuple(r for r in ALL_RELATIONS if r != "My child")
    if ADULT_RELATIONS_EN != expected:
        problems.append("ADULT_RELATIONS must be ALL_RELATIONS minus the child, in order")
    return problems


if __name__ == "__main__":
    issues = check_mirrors_kinyarwanda()
    for issue in issues:
        print(issue)
    print("English relation sets mirror the Kinyarwanda rulings"
          if not issues else f"{len(issues)} problems")
    raise SystemExit(1 if issues else 0)
