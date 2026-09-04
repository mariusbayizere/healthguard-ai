"""Leakage checks on the phrase holdout.

The trap this suite exists for: a held-out phrase nested inside a longer
training phrase. An exact-match overlap check reports zero leakage while every
training row built on the longer phrase contains the held-out string verbatim.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from dataset.split_dataset import (
    PREFIX_UNION_CHARS,
    _find_at_word_boundary,
    _match_form,
    attribute_phrase,
    phrase_components,
    substring_violations,
)
from dataset.validate_dataset import all_symptom_phrases


def test_nested_phrases_share_a_group() -> None:
    """Nested phrases must be inseparable, or they can land on opposite sides."""
    components = phrase_components()
    nested = [
        (inner, outer)
        for inner in components
        for outer in components
        if inner != outer and inner in outer
    ]
    assert nested, "fixture problem: the corpus has no nested phrases to test"
    for inner, outer in nested:
        assert components[inner] == components[outer], (
            f"{inner!r} is a substring of {outer!r} but they are in different "
            "groups, so a split could separate them"
        )


def test_substring_violations_detects_containment_both_ways() -> None:
    train = {"a mild headache that is not severe"}
    held = {"a mild headache"}
    # held is inside train: leakage, even though the strings are not equal.
    assert substring_violations(train, held)
    # and the reverse direction must be caught too
    assert substring_violations(held, train)


def test_substring_violations_is_quiet_on_disjoint_phrases() -> None:
    assert substring_violations({"chest pain"}, {"une toux legere"}) == []


def test_exact_match_check_would_have_missed_the_nested_case() -> None:
    """Documents why this suite exists rather than an equality check."""
    train = {"ububabare bukabije mu nda ndi utwite kandi ndavuye amaraso"}
    held = {"ububabare bukabije mu nda"}
    assert not (train & held), "premise: exact overlap is empty"
    assert substring_violations(train, held), "but the substring check catches it"


def test_phrase_attribution_prefers_the_longest_match() -> None:
    index = all_symptom_phrases()
    language = "kinyarwanda"
    candidates = index[language]
    longest = candidates[0]
    text = f"Muraho, {longest} kandi ndabyifuza."
    family = f"{language}->{language}:CRITICAL:cardiac_respiratory"
    assert attribute_phrase(text, family, index) == longest


@pytest.mark.parametrize("strategy", ["phrase", "family"])
def test_frozen_manifest_records_its_leakage_position(strategy: str, ml_root: Path) -> None:
    """Both manifests must state their leakage explicitly, whatever the value.

    The family split legitimately has phrase overlap by design; the point is
    that the number is recorded and reviewable, not that it is zero.
    """
    path = ml_root / f"dataset/processed/eval_manifest_{strategy}_v1.json"
    if not path.exists():
        pytest.skip(f"{path.name} is built by `make dataset`; not present here")
    leakage = json.loads(path.read_text())["leakage"]
    for field in (
        "exact_text_overlap",
        "phrase_overlap",
        "substring_violations",
        "eval_rows_leaked_fraction",
    ):
        assert field in leakage, f"{strategy} manifest does not record {field}"
    assert leakage["exact_text_overlap"] == 0, "identical rows on both sides of the split"


def test_phrase_split_has_no_substring_leakage(ml_root: Path) -> None:
    """The phrase split is the one that must be leakage-free to mean anything."""
    path = ml_root / "dataset/processed/eval_manifest_phrase_v1.json"
    if not path.exists():
        pytest.skip("phrase manifest is built by `make dataset`; not present here")
    leakage = json.loads(path.read_text())["leakage"]
    assert leakage["substring_violations"] == 0
    assert leakage["phrase_overlap"] == 0
    assert leakage["eval_rows_leaked_fraction"] == 0.0


def test_held_out_phrases_are_absent_from_sample_training_text(
    sample_csv: Path, tmp_path: Path, ml_root: Path
) -> None:
    """End-to-end on the committed sample: scan real training rows, not phrase sets."""
    import subprocess
    import sys

    # cwd is explicit: the script resolves its imports relative to the ml_model
    # directory, so without this the test passes or fails depending on where
    # pytest happened to be invoked from.
    subprocess.run(
        [sys.executable, "dataset/split_dataset.py", "--strategy", "phrase",
         "--input", str(sample_csv), "--out-dir", str(tmp_path)],
        cwd=ml_root, check=True, capture_output=True,
    )
    report = json.loads((tmp_path / "split_phrase_holdout.json").read_text())
    held = set(report["holdout_groups"])
    components = phrase_components()
    held_phrases = {p for p, root in components.items() if root in held}

    with (tmp_path / "train_phrase_holdout.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            for phrase in held_phrases:
                assert phrase not in row["text"], (
                    f"held-out phrase {phrase!r} appears verbatim in a training row"
                )


# ── phrase_components: containment must see through the utterance form ──────


def _shared_prefix(left: str, right: str) -> int:
    count = 0
    for a, b in zip(left, right):
        if a != b:
            break
        count += 1
    return count


@pytest.mark.parametrize(
    "inner,outer",
    [
        # terminal stop: the exact pair I asserted was unioned during a ruling
        ("{REL} arababara cyane mu nda.",
         "{REL} arababara cyane mu nda kandi ububabare ntibuhagarara."),
        ("{REL} ahumeka bimugora cyane.",
         "{REL} ahumeka bimugora cyane kandi iminwa ye yahindutse ubururu."),
        # capitalisation
        ("guhumeka birangora cyane",
         "Guhumeka birangora cyane ku buryo ntabasha no kuvuga neza."),
        ("inda irandya cyane",
         "Inda irandya cyane kandi ububabare ntibuhagarara."),
    ],
)
def test_containment_sees_through_stops_and_capitals(inner: str, outer: str) -> None:
    """A raw `in` misses these; every v2 phrase is capitalised and stop-terminated.

    At render time _drop_terminal_stop removes exactly that period whenever a
    continuation follows, so the rendered rows DO contain one another. Comparing
    raw strings left five authored pairs silently in separate groups, which is the
    fourth time a terminal stop has defeated a string match in this codebase.
    """
    assert inner not in outer, "fixture problem: this pair needs to defeat a raw `in`"
    assert _match_form(inner) in _match_form(outer)


def test_no_authored_pair_is_a_normalised_containment_in_separate_groups() -> None:
    """The property, over the real inventory rather than a fixture."""
    components = phrase_components()
    for inner in components:
        for outer in components:
            if inner == outer:
                continue
            if _match_form(inner) and _match_form(inner) in _match_form(outer):
                assert components[inner] == components[outer], (
                    f"{inner!r} normalises into {outer!r} but they are in "
                    "different groups, so a split could separate them"
                )


# ── phrase_components: the prefix threshold ─────────────────────────────────


def test_a_long_shared_prefix_unions_even_without_containment() -> None:
    """Containment misses a divergent pair with a long shared head.

    "{REL} ari kuva amaraso menshi kandi ntahagarara." against
    "{REL} ari kuva amaraso menshi mu mazuru kandi ntahagarara." - the insertion
    is mid-phrase, so neither contains the other, and both share 30 characters.
    """
    components = phrase_components()
    checked = 0
    for left in components:
        for right in components:
            if left >= right:
                continue
            a, b = _match_form(left), _match_form(right)
            if a in b or b in a:
                continue
            if _shared_prefix(a, b) >= PREFIX_UNION_CHARS:
                checked += 1
                assert components[left] == components[right], (
                    f"{left!r} and {right!r} share >= {PREFIX_UNION_CHARS} "
                    "characters of prefix but are in different groups"
                )
    # v1 alone has no such pairs; this asserts the rule is wired, not that v1 trips it.
    assert checked >= 0


def test_the_threshold_stays_above_the_v1_safe_floor() -> None:
    """Below 25 the v1 partition changes and the frozen digests break.

    Measured in docs/phrase-group-closure.md: 25 and above leave v1's partition
    byte-identical, 22 and below do not. The margin is not decorative - lowering
    this constant is what would silently invalidate the frozen phrase split.
    """
    assert PREFIX_UNION_CHARS >= 25


def test_v1_grouping_is_unchanged_by_both_rules() -> None:
    """v1's phrases are fragments: no terminal stops, no capitals, no long heads."""
    from collections import Counter

    components = phrase_components()
    assert len(components) == 184
    assert len(Counter(components.values())) == 180
    assert not [p for p in components if p.strip()[-1:] in ".!?"]
    assert not [p for p in components if p[:1].isupper()]


# ── phrase_components: a concept's phrases are one group ────────────────────


def test_concept_union_is_empty_for_v1_and_leaves_it_untouched():
    """v1 has no concept ids and one phrase per concept, so nothing to join."""
    from collections import Counter

    from dataset import vocabulary as V
    assert V.PHRASE_CONCEPTS == {}
    components = phrase_components()
    assert len(components) == 184
    assert len(Counter(components.values())) == 180


def test_a_concepts_two_persons_join_one_group():
    """The leak no similarity rule can close.

    A third-person phrase begins with {REL} and a first-person one with a letter,
    so their shared prefix is 0 BY CONSTRUCTION - PREFIX_UNION_CHARS can never
    catch the pair however low it is set - and containment fails on the verb
    morphology. 60 of 61 concepts with both persons authored were split.
    """
    from dataset import vocabulary as V
    from dataset import split_dataset as S

    first = "Iminwa yanjye yahindutse ubururu."
    third = "{REL} iminwa ye yahindutse ubururu."
    # the premise: neither existing rule joins them
    assert _match_form(first) not in _match_form(third)
    assert _match_form(third) not in _match_form(first)
    assert _shared_prefix(_match_form(first), _match_form(third)) == 0

    real = dict(V.PHRASE_CONCEPTS)
    try:
        V.PHRASE_CONCEPTS.clear()
        V.PHRASE_CONCEPTS.update({first: "CR03", third: "CR03"})
        S.PHRASE_CONCEPTS = V.PHRASE_CONCEPTS
        # both phrases are absent from v1's inventory, so the declaration must raise
        with pytest.raises(SystemExit, match="not in the symptom inventory"):
            phrase_components()
    finally:
        V.PHRASE_CONCEPTS.clear()
        V.PHRASE_CONCEPTS.update(real)
        S.PHRASE_CONCEPTS = V.PHRASE_CONCEPTS


def test_a_declaration_naming_an_absent_phrase_raises():
    """Silence there would leave the concept's other phrases unjoined.

    That is the same failure shape as the empty CONCEPT_RELATIONS: a ruling
    recorded where no code path reads it, reopening the leak without an error.
    """
    from dataset import vocabulary as V
    from dataset import split_dataset as S

    real = dict(V.PHRASE_CONCEPTS)
    try:
        V.PHRASE_CONCEPTS.clear()
        V.PHRASE_CONCEPTS["a phrase that is not in the inventory"] = "XX99"
        S.PHRASE_CONCEPTS = V.PHRASE_CONCEPTS
        with pytest.raises(SystemExit, match="XX99"):
            phrase_components()
    finally:
        V.PHRASE_CONCEPTS.clear()
        V.PHRASE_CONCEPTS.update(real)
        S.PHRASE_CONCEPTS = V.PHRASE_CONCEPTS


def test_real_v1_phrases_union_when_declared_one_concept():
    """The mechanism itself, on phrases that ARE in the inventory."""
    from dataset import vocabulary as V
    from dataset import split_dataset as S

    inventory = sorted(phrase_components())
    a, b = inventory[0], inventory[-1]
    assert phrase_components()[a] != phrase_components()[b], "fixture needs two groups"

    real = dict(V.PHRASE_CONCEPTS)
    try:
        V.PHRASE_CONCEPTS.clear()
        V.PHRASE_CONCEPTS.update({a: "ZZ01", b: "ZZ01"})
        S.PHRASE_CONCEPTS = V.PHRASE_CONCEPTS
        joined = phrase_components()
        assert joined[a] == joined[b], "one concept must mean one phrase group"
    finally:
        V.PHRASE_CONCEPTS.clear()
        V.PHRASE_CONCEPTS.update(real)
        S.PHRASE_CONCEPTS = V.PHRASE_CONCEPTS


# ── attribute_phrase: a match may not begin inside a word ───────────────────


def test_a_match_may_not_begin_inside_a_word():
    """"Ndashaka" ends with "ashaka" — the collision that turned CI red.

    The third-person phrase's post-{REL} segment was a substring of the
    first-person phrase, and being the longer index entry it captured the first
    person's rows. Four authored pairs collided and six commits reached main red,
    because the local command in use was skipping this file.

    Fourth silent failure in attribute_phrase, after case sensitivity, the welded
    {REL} halves and the terminal stop.
    """
    assert _find_at_word_boundary("ndashaka inama", "ashaka inama") == -1
    assert _find_at_word_boundary("mama ashaka inama", "ashaka inama") == 5
    # a match must also END on a boundary
    assert _find_at_word_boundary("mama ashakawe", "ashaka") == -1
    # an apostrophe is not a word character: Kinyarwanda writes n'uduheri
    assert _find_at_word_boundary("afite umuriro n'uduheri", "uduheri") > 0


def test_every_authored_first_person_attributes_to_itself():
    """The real-corpus guard, over every first/third pair the brief holds.

    A first-person phrase rendered plainly must attribute to ITSELF, never to its
    concept's third person. This is the property the four colliding pairs broke,
    checked against the brief rather than a fixture so a new Nd- verb cannot
    reintroduce it.
    """
    from dataset.split_dataset import attribute_phrase

    brief = (Path(__file__).resolve().parent.parent
             / "review" / "speaker_brief_kinyarwanda_v2.csv")
    rows = list(csv.DictReader(brief.open(encoding="utf-8")))
    by_concept: dict[str, dict[str, str]] = {}
    for row in rows:
        phrase = (row["your_phrasing"] or "").strip()
        if phrase and (row.get("applies") or "yes").lower() != "no":
            by_concept.setdefault(row["concept_id"], {})[row["person"]] = phrase

    inventory = sorted({p for v in by_concept.values() for p in v.values()},
                       key=len, reverse=True)
    index = {"kinyarwanda": inventory}
    family = "kinyarwanda->kinyarwanda:ROUTINE:preventive"

    checked = 0
    for concept, persons in by_concept.items():
        first = persons.get("first")
        if not first:
            continue
        checked += 1
        got = attribute_phrase(first, family, index)
        assert got == first, (
            f"{concept} first person {first!r} attributed to {got!r}. "
            "A first-person row would be recorded under another phrase."
        )
    assert checked > 50, "fixture problem: the brief should hold many first persons"
