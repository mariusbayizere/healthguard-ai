"""The rulings in routine_relation_sets.csv must actually reach the generator.

They did not. `CONCEPT_RELATIONS` is keyed by phrase string and the rulings are
keyed by concept id, nothing bridged the two, and every consumer fell back to the
domain default without an error. That is how EX16 came to be rendered across
eight relations for ruling when its own ruling allows five.

These tests pin the bridge: that a ruling resolves, that materialisation refuses
to discard an authored phrase, and that the review renderer substitutes relations
exactly as the real generator does.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "review"))

from dataset import vocabulary as V  # noqa: E402
from relation_sets import (NAMED, SENTINELS, materialise,  # noqa: E402
                           resolve, rulings)
from render_third_person import render, rows_for  # noqa: E402


def test_every_ruling_names_a_known_set_or_sentinel():
    """A typo in the CSV used to fall through to the domain default silently."""
    for concept_id, name in rulings().items():
        assert name in NAMED or name in SENTINELS, (
            f"{concept_id} is ruled {name!r}, which is neither a named relation "
            f"set nor a sentinel. It would silently resolve to the domain default."
        )


def test_a_concept_ruling_beats_its_domain():
    """EX16 is gastrointestinal, which allows all eight; its ruling allows five."""
    assert resolve("EX16", "gastrointestinal") == V.CHILD_RELATIONS
    assert len(V.CHILD_RELATIONS) < len(V.RELATIONS["kinyarwanda"])


def test_an_unruled_concept_falls_back_to_its_domain():
    assert resolve("GI05", "gastrointestinal") == V.RELATIONS["kinyarwanda"]
    assert resolve("OB01", "obstetric") == V.DOMAIN_RELATIONS["obstetric"]


def test_a_sentinel_ruling_generates_no_third_person():
    assert resolve("PR02", "preventive") is None   # do not generate
    assert resolve("OB12", "obstetric") is None    # held


def test_materialise_refuses_to_zero_an_authored_phrase():
    """The failure this module exists to prevent, in both its forms.

    A concept ruled NO_RELATIONS whose third-person phrase is authored would map
    that phrase to an empty tuple and contribute nothing, with no error raised.
    NO_RELATIONS is a *named set*, not a sentinel, so it does not take the
    sentinel path — the first version of this guard missed exactly that and let
    OB11 through as ready to materialise.
    """
    ruled = dict(rulings())
    ruled["GI05"] = "NO_RELATIONS"   # GI05 third IS authored
    mapping, conflicts = materialise(ruled=ruled)

    assert any("GI05" in c for c in conflicts), (
        "an authored phrase ruled NO_RELATIONS must be reported, not silently zeroed"
    )
    gi05 = next(r["your_phrasing"].strip()
                for r in csv.DictReader((ROOT / "review" / "speaker_brief_kinyarwanda_v2.csv")
                                        .open(encoding="utf-8"))
                if r["concept_id"] == "GI05" and r["person"] == "third")
    assert gi05 not in mapping, "the phrase must not be mapped to an empty set"


def test_materialise_emits_nothing_that_would_change_a_phrase_to_no_rows():
    """Whatever it does emit must expand to at least one relation."""
    mapping, _ = materialise()
    for phrase, rels in mapping.items():
        assert len(rels) > 0, f"{phrase!r} would generate no rows"
        assert V.REL_PLACEHOLDER in phrase


def test_unauthored_rulings_are_not_an_error():
    """Most ruled concepts have no third-person phrase yet. That is fine."""
    ruled = rulings()
    mapping, conflicts = materialise(ruled=ruled)
    assert len(mapping) < len(ruled)
    for c in conflicts:
        assert "not authored" not in c


def test_review_render_matches_the_generator_substitution():
    """The renderer duplicates build_families' substitution; pin them together.

    Including the lowercasing rule: a relation is proper-noun shaped and written
    capitalised, but mid-sentence it is not a sentence start.
    """
    rel = "Umwana wanjye"
    head = V.REL_PLACEHOLDER + " arababara cyane mu nda."
    mid = "Iyo " + V.REL_PLACEHOLDER + " amaze kurya, yumva inda itameze neza."

    def as_generator(phrase: str, relation: str) -> str:
        is_head = phrase.startswith(V.REL_PLACEHOLDER)
        return phrase.replace(V.REL_PLACEHOLDER,
                              relation if is_head else relation[0].lower() + relation[1:])

    for phrase in (head, mid):
        assert render(phrase, rel) == as_generator(phrase, rel)

    assert render(head, rel).startswith("Umwana wanjye")
    assert "umwana wanjye" in render(mid, rel)
    assert "Umwana wanjye" not in render(mid, rel)


def test_the_renderer_honours_a_concept_ruling():
    """The EX16 bug, as a test: it must render on five relations, not eight."""
    rows = rows_for("gastrointestinal")
    per_concept: dict[str, set[str]] = {}
    for r in rows:
        per_concept.setdefault(r["concept_id"], set()).add(r["relation"])

    assert per_concept["EX16"] == set(V.CHILD_RELATIONS)
    assert len(per_concept["EX16"]) == 5
    # An unruled sibling in the same domain still gets the full set, so the
    # restriction is coming from the ruling and not from something global.
    assert len(per_concept["GI05"]) == len(V.RELATIONS["kinyarwanda"])


def test_a_held_row_neither_generates_nor_blocks():
    """OB11's shape: a ruling and an accepted phrase that contradict each other.

    Holding is how both are kept alive until the question is answered, so a held
    row must be excluded from the mapping (it must not generate) AND must not be
    reported as a conflict (it must not block the other rulings). Before this,
    OB11 blocked materialisation for every other concept.
    """
    brief = list(csv.DictReader((ROOT / "review" / "speaker_brief_kinyarwanda_v2.csv")
                                .open(encoding="utf-8")))
    ob11 = next(r for r in brief if r["concept_id"] == "OB11" and r["person"] == "third")
    assert ob11["hold"] == "yes", "this test is about OB11 being held"
    assert ob11["your_phrasing"].strip(), "and about it still carrying its accepted phrase"
    assert ob11["source"] == "machine_approved", (
        "the acceptance record must survive the hold; hold and provenance are "
        "orthogonal and overwriting one with the other loses information"
    )

    mapping, conflicts = materialise()
    assert ob11["your_phrasing"].strip() not in mapping, "a held row must not generate"
    assert not any("OB11" in c for c in conflicts), "a held row must not block"
    assert mapping, "the other rulings must still materialise"


@pytest.mark.parametrize("concept_id", ["CR07", "EX16", "EX29", "EX31"])
def test_the_already_authored_child_rulings_are_in_force_once_materialised(concept_id):
    """Four accepted phrases carry CHILD_RELATIONS. Materialisation must apply it."""
    mapping, conflicts = materialise()
    assert not conflicts, conflicts

    brief = list(csv.DictReader((ROOT / "review" / "speaker_brief_kinyarwanda_v2.csv")
                                .open(encoding="utf-8")))
    phrase = next(r["your_phrasing"].strip() for r in brief
                  if r["concept_id"] == concept_id and r["person"] == "third")
    assert mapping[phrase] == V.CHILD_RELATIONS
