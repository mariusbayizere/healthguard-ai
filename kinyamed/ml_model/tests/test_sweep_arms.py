"""Every sweep arm must score on the same eval file, and say where it came from.

WHY THIS IS A TEST AND NOT A CONVENTION. The sweep compares held-out performance
across arms that differ in seed count. If two arms were scored on different eval
files the comparison would be meaningless, and nothing in the training pipeline
would notice: each run would verify its own manifest's digests and pass. The one
file the whole result rests on is exactly the one a convention is least adequate
to protect.

It also pins the derivation chain. Each arm records the parent manifest it was
derived from and that parent's digests, so an arm can be traced back to the
frozen v2 split rather than taken on trust.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SWEEP = ROOT / "dataset" / "sweep"
PARENT = ROOT / "dataset" / "processed" / "eval_manifest_phrase_v2.json"


def manifests() -> list[dict]:
    return [
        json.loads(p.read_text(encoding="utf-8"))
        for p in sorted(SWEEP.glob("manifest_*.json"))
    ]


def require_arms() -> list[dict]:
    found = manifests()
    if not found:
        pytest.skip("no sweep arms built yet")
    return found


def test_every_arm_scores_on_the_same_eval_file() -> None:
    """The assertion the whole sweep depends on."""
    arms = require_arms()
    digests = {m["files"]["eval"]["sha256"] for m in arms}
    paths = {m["files"]["eval"]["path"] for m in arms}
    assert len(digests) == 1, (
        f"{len(arms)} arms point at {len(digests)} different eval digests. "
        "Arms scored on different data cannot be compared, and each run would "
        f"still verify its own manifest and pass. Digests: {sorted(digests)}"
    )
    assert len(paths) == 1, f"arms point at different eval paths: {sorted(paths)}"


def test_the_shared_eval_is_the_frozen_parent_one() -> None:
    """Identical across arms is not enough; it must be the frozen split's eval."""
    arms = require_arms()
    if not PARENT.exists():
        pytest.skip("parent manifest missing")
    parent = json.loads(PARENT.read_text(encoding="utf-8"))
    expected = parent["files"]["eval"]["sha256"]
    for m in arms:
        assert m["files"]["eval"]["sha256"] == expected, (
            f"{m['sweep']['arm']} scores on an eval file that is not the frozen "
            "v2 eval split"
        )


def test_every_arm_records_its_derivation() -> None:
    arms = require_arms()
    for m in arms:
        chain = m.get("derived_from")
        assert chain, f"{m['sweep']['arm']} does not record what it derives from"
        for key in ("manifest", "manifest_sha256", "train_sha256", "eval_sha256"):
            assert chain.get(key), f"{m['sweep']['arm']} is missing derived_from.{key}"


def test_training_files_are_distinct_and_eval_is_not() -> None:
    """Arms must differ in training data and agree on evaluation data."""
    arms = require_arms()
    train = [m["files"]["train"]["sha256"] for m in arms]
    assert len(set(train)) == len(train), (
        "two arms share a training digest, so they are the same experiment twice"
    )


def test_every_arm_carries_the_provenance_line() -> None:
    for m in require_arms():
        note = m.get("provenance", "")
        assert "non-clinician" in note and "no second rater" in note, (
            f"{m['sweep']['arm']} does not carry the labelling provenance"
        )


def test_the_row_budget_is_identical_across_arms() -> None:
    """Total rows held constant is the control the sweep varies seeds against."""
    arms = require_arms()
    totals = {m["sweep"]["total_rows"] for m in arms}
    assert len(totals) == 1, (
        f"arms differ in total rows {sorted(totals)}; seed count is then not the "
        "only difference between them"
    )


def test_seed_counts_and_replicates_are_the_declared_design() -> None:
    arms = require_arms()
    seen = sorted({m["sweep"]["distinct_seeds"] for m in arms})
    assert seen == [10, 20, 40, 80, 120], f"unexpected seed counts: {seen}"
    for n in seen:
        reps = [m for m in arms if m["sweep"]["distinct_seeds"] == n]
        assert len(reps) == 3, f"{n} seeds has {len(reps)} replicates, expected 3"
        rng = {m["sweep"]["rng_seed"] for m in reps}
        assert len(rng) == 3, f"{n} seeds reuses an RNG seed: {sorted(rng)}"
