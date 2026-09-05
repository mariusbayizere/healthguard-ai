#!/usr/bin/env python
"""French relation sets, held here until they can land in `dataset/vocabulary.py`.

THIS IS A STAGING FILE, NOT THE INTENDED HOME — the same arrangement
`english_relations.py` describes, and for the same reason: French work must not
touch `dataset/` while Kinyarwanda authoring is in flight. Nothing in `dataset/`
imports this, so nothing generates from it.

MIRRORED, NOT RE-DECIDED. Every set is the speaker's Kinyarwanda ruling with the
members translated one for one, in the same order, using the wording v1's own
`SUBJECTS` slot already chose — `Umukecuru` is `Ma grand-mere` there, so it is
that here rather than a fresh translation.

WHERE FRENCH IS NOT ENGLISH
---------------------------
The English arm could mirror the person split almost for free: "every English
relation is third-person singular, so one authored sentence fits all eight with
no verb agreement to vary". **That sentence is false in French**, and the
difference drives three rulings below.

    FR-1  agreement      an adjective or past participle agreeing with {REL}
                         is wrong for half the expansions. Structural fix.
    FR-2  possessive     son/sa/ses agrees with the POSSESSED noun, so French
                         needs no ruling here at all — the mirror image of the
                         English singular-"their" problem.
    FR-3  orthography    v1 French is unaccented ASCII, everywhere, undeclared.
                         v2 follows it. See `french-review-pass.md`.

FR-1 is the one that costs something, and it is the same shape as the
Kinyarwanda object-marker problem that holds CR01 and CR05: a third-person
phrase cannot be produced from a first-person one by substitution alone.
"""

from __future__ import annotations

import re
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

# The eight, in the Kinyarwanda order, from v1 `SUBJECTS["french"]`.
ALL_RELATIONS: tuple[str, ...] = (
    "Mon enfant", "Ma femme", "Mon mari", "Ma mere",
    "Mon pere", "Ma soeur", "Mon voisin", "Ma grand-mere",
)

# Only `Mon enfant` is a v1 subject; the other four are drafted, exactly as
# their English counterparts (`My son`, `My daughter`, ...) were.
CHILD_RELATIONS_FR: tuple[str, ...] = (
    "Mon enfant", "Mon fils", "Ma fille",
    "Mon petit-enfant", "L'enfant de mon voisin",
)

HOUSEHOLD_RELATIONS_FR: tuple[str, ...] = (
    "Ma femme", "Mon mari", "Ma mere", "Mon pere",
    "Ma soeur", "Mon enfant",
)

ADULT_RELATIONS_FR: tuple[str, ...] = (
    "Ma femme", "Mon mari", "Ma mere", "Mon pere",
    "Ma soeur", "Mon voisin", "Ma grand-mere",
)

NO_RELATIONS_FR: tuple[str, ...] = ()

# RULED here, and it is the French counterpart of the English `she`/`her` choice.
#
# The speaker ruled `Umuturanyi wanjye` — gender-neutral — into the obstetric
# four. English inherits the ruling and resolves the gender downstream, with a
# feminine pronoun later in the sentence. FRENCH CANNOT WAIT THAT LONG: the
# relation is itself a noun phrase and `Mon voisin` is masculine, so
# `Mon voisin est enceinte` states that a man is pregnant before any pronoun
# gets a chance to fix it. `Ma voisine` is the same relation with the gender the
# ruling already implies, resolved at the only place French offers.
#
# This is a drafting choice INSIDE the ruling, not a narrowing of it — the same
# standing the English `she` has. It is recorded because it is the one member of
# any French set that is not a one-for-one carry of the Kinyarwanda wording.
OBSTETRIC_RELATIONS_FR: tuple[str, ...] = (
    "Ma femme", "Ma mere", "Ma soeur", "Ma voisine",
)

DOMAIN_RELATIONS_FR: dict[str, tuple[str, ...]] = {
    "obstetric": OBSTETRIC_RELATIONS_FR,
    "paediatric": CHILD_RELATIONS_FR,
}

# Mirrors `english_relations.OBSTETRIC_RELATIONS_NO_MOTHER`. OB12 drops the
# mother: with `Ma mere` substituted, "{REL} veut des conseils pour allaiter son
# bebe" says the speaker's own mother has recently delivered. Derived rather
# than retyped, so it cannot drift from the four.
OBSTETRIC_RELATIONS_NO_MOTHER_FR: tuple[str, ...] = tuple(
    r for r in OBSTETRIC_RELATIONS_FR if r != "Ma mere"
)

# Rulings made during a per-language pass that are NOT yet in
# `review/routine_relation_sets.csv`, the Kinyarwanda record this session must
# not edit. Same temporary second source of truth `english_relations.py` warns
# about; it holds the same single entry, and for the same concept.
PENDING_RULINGS: dict[str, str] = {
    "OB12": "OBSTETRIC_RELATIONS_NO_MOTHER",
}

# FR-1. Grammatical gender of every relation, for the agreement check below.
# `Mon enfant` is masculine as a NOUN whatever the child's sex, which is what
# agreement follows; the same is true of `Mon petit-enfant` and
# `L'enfant de mon voisin`.
GENDER: dict[str, str] = {
    "Mon enfant": "m", "Ma femme": "f", "Mon mari": "m", "Ma mere": "f",
    "Mon pere": "m", "Ma soeur": "f", "Mon voisin": "m", "Ma grand-mere": "f",
    "Mon fils": "m", "Ma fille": "f", "Mon petit-enfant": "m",
    "L'enfant de mon voisin": "m", "Ma voisine": "f",
}

# FR-2. Recorded as a non-problem so nobody re-opens it. French possessive
# determiners agree with the POSSESSED noun: `ses levres` is right for all eight
# relations, `sa tension` for all eight, `son ventre` for all eight. The English
# arm had to rule singular "their" over a real ambiguity; French has none, and
# the obstetric `she` that English needed is carried here by `Ma voisine`
# instead.
THIRD_PERSON_POSSESSIVE = "son/sa/ses — agrees with the possessed noun, not {REL}"

NAMED: dict[str, tuple[str, ...]] = {
    "OBSTETRIC_RELATIONS_NO_MOTHER": OBSTETRIC_RELATIONS_NO_MOTHER_FR,
    "ALL_RELATIONS": ALL_RELATIONS,
    "CHILD_RELATIONS": CHILD_RELATIONS_FR,
    "HOUSEHOLD_RELATIONS": HOUSEHOLD_RELATIONS_FR,
    "ADULT_RELATIONS": ADULT_RELATIONS_FR,
    "OBSTETRIC_RELATIONS": OBSTETRIC_RELATIONS_FR,
    "NO_RELATIONS": NO_RELATIONS_FR,
}

# ---------------------------------------------------------------------------
# FR-1, as a check rather than as a paragraph.
# ---------------------------------------------------------------------------
#
# A LEAD GENERATOR, NOT A VERDICT — the same standing `concept_drift()` and the
# 1sg-marker scan have in the English arm. It cannot parse French; it knows the
# constructions that put an inflecting word in agreement with the subject, and
# the inflecting words this corpus actually uses.
#
# Every entry below appears in a real draft or in v1. The list is short on
# purpose: a long speculative list would flag noise and get ignored.
# EPICENE ADJECTIVES ARE NOT IN THIS LIST, and leaving them out is the point.
# `faible`, `maigre`, `malade`, `incapable` and `diabetique` take one form for
# both genders, so they are exactly the words a French phrase should be built on
# when the subject's gender is unknown. Listing them would flag the fix as the
# defect.
INFLECTING = {
    "essouffle", "somnolent", "allonge", "depiste", "mordu", "inconscient",
    "confus", "fatigue", "inquiet", "enceinte", "assis", "couche", "tombe",
    "blesse", "brule", "gueri", "guerie", "epuise", "pret", "ne", "premier",
    "enfle", "deforme", "perdu", "reveille", "gonfle", "sourd", "gros",
    # Irregular feminines, which are the ones a translator's ear misses because
    # they do not look like they inflect. `mou`/`molle` caught PA03: the sheet
    # draft's "mon enfant est mou" is wrong for `Ma fille`, and CHILD_RELATIONS
    # contains her.
    "mou", "sec", "blanc", "vieux", "nouveau", "fou", "doux", "franc",
}

# `etre` + X agrees. `avoir` + noun does not, which is why almost every draft
# below is built on `a` / `ai`.
_ETRE = re.compile(
    r"\b(?:est|sont|suis|es|etait|sera|a\s+ete|ai\s+ete|semble|parait|reste|devient|"
    r"devenu\w*|deviennent)\s+(?:tres\s+|trop\s+|un\s+peu\s+|pas\s+|plus\s+)*([a-z'-]+)",
    re.IGNORECASE,
)


def obstetric_scope(rows: "list[dict]") -> "dict[str, bool]":
    """concept id -> whether that CONCEPT's speaker is known to be female.

    THE SCOPE IS PER CONCEPT, NOT PER ROW, and that is the whole point. A
    first-person row carries no relation set — the field is empty by
    construction — so asking a first-person row whether it is obstetric can only
    be answered from the domain, and the domain is wrong for `PR05`: a
    PREVENTIVE concept ruled `OBSTETRIC_RELATIONS` because it is about
    pregnancy. Its first person says `Je suis enceinte` and a row-local check
    flags it as an FR-1 defect. Reading the ruling off the concept's OTHER
    person is what makes the exemption land where the concept is.

    Obstetric rows are the one place a feminine form is not a defect but the
    concept, in both persons.
    """
    scope: dict[str, bool] = {}
    for row in rows:
        cid = row["concept_id"]
        obstetric = (row.get("domain") == "obstetric"
                     or row.get("relation_set", "").startswith("OBSTETRIC_RELATIONS"))
        scope[cid] = scope.get(cid, False) or obstetric
    return scope


def agreement_risks(phrase: str, obstetric: bool = False) -> list[str]:
    """Words in `phrase` that would have to agree with a subject of either gender.

    Pass `obstetric=True` for a row whose concept is obstetric-scoped — see
    `obstetric_scope`. `OBSTETRIC_RELATIONS` is uniformly feminine once
    `Ma voisine` resolves the neighbour, and an obstetric first person is a
    pregnant woman, so there an agreeing form is not only safe but required:
    `enceinte` IS the concept.

    Every other first-person row is checked, because the patient's own gender is
    exactly as unknown as `{REL}`'s. That is where the v1 defect lives: the
    CONTEXTS slot ships ` et je suis inquiet` on 41,872 shipped rows, masculine,
    with no feminine counterpart anywhere in the corpus.
    """
    if obstetric:
        return []
    found: list[str] = []
    for match in _ETRE.finditer(phrase):
        word = match.group(1).lower().strip("',-")
        if word in INFLECTING:
            found.append(f"{match.group(0).strip()!r} — agrees with the subject")
    # A bare participle opening a phrase ("mordu par un serpent") agrees too.
    head = phrase.split()[0].lower().strip(",.'") if phrase.split() else ""
    if head in INFLECTING:
        found.append(f"opens with {head!r} — a participle agreeing with an unstated subject")
    return found


def check_mirrors_kinyarwanda() -> list[str]:
    """Every French set must have the same size as the Kinyarwanda one it mirrors.

    Size is the only property checkable without a translation memory, and it is
    the one that catches the failure that matters: a set that silently gained or
    lost a member relative to the ruling it claims to mirror. Copied in intent
    from `english_relations.check_mirrors_kinyarwanda`, so the two arms fail the
    same way.
    """
    pairs = [
        ("ALL_RELATIONS", ALL_RELATIONS, RELATIONS["kinyarwanda"]),
        ("CHILD_RELATIONS", CHILD_RELATIONS_FR, CHILD_RELATIONS),
        ("HOUSEHOLD_RELATIONS", HOUSEHOLD_RELATIONS_FR, HOUSEHOLD_RELATIONS),
        ("ADULT_RELATIONS", ADULT_RELATIONS_FR, ADULT_RELATIONS),
        ("OBSTETRIC_RELATIONS", OBSTETRIC_RELATIONS_FR, DOMAIN_RELATIONS["obstetric"]),
    ]
    problems = [
        f"{name}: French has {len(fr)} members, Kinyarwanda has {len(ky)}"
        for name, fr, ky in pairs if len(fr) != len(ky)
    ]
    expected = tuple(r for r in ALL_RELATIONS if r != "Mon enfant")
    if ADULT_RELATIONS_FR != expected:
        problems.append("ADULT_RELATIONS must be ALL_RELATIONS minus the child, in order")
    # The obstetric four are ALL_RELATIONS members with the neighbour resolved to
    # the feminine. Anything else there is a re-decided ruling, not a mirrored one.
    allowed = set(ALL_RELATIONS) | {"Ma voisine"}
    stray = [r for r in OBSTETRIC_RELATIONS_FR if r not in allowed]
    if stray:
        problems.append(f"OBSTETRIC_RELATIONS has non-mirrored members: {stray}")
    if any(GENDER[r] != "f" for r in OBSTETRIC_RELATIONS_FR):
        problems.append("OBSTETRIC_RELATIONS is not uniformly feminine; FR-1's "
                        "obstetric exemption depends on it")
    missing = [r for s in NAMED.values() for r in s if r not in GENDER]
    if missing:
        problems.append(f"no gender recorded for {sorted(set(missing))}")
    return problems


if __name__ == "__main__":
    issues = check_mirrors_kinyarwanda()
    for issue in issues:
        print(issue)
    print("French relation sets mirror the Kinyarwanda rulings"
          if not issues else f"{len(issues)} problems")
    for name, members in NAMED.items():
        genders = "".join(GENDER[r] for r in members)
        print(f"  {name:34} {len(members)}  {genders or '-'}")
    raise SystemExit(1 if issues else 0)
