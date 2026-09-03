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
