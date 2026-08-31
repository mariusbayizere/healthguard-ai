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
