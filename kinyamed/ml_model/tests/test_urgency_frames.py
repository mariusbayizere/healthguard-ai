"""A class may narrow its frame slots — without that touching v1.

A frame can contradict the label the row is trained on: a ROUTINE phrase closing
"I need help quickly", a CRITICAL phrase closing "Thank you." The fix is to let
an urgency class narrow its contexts and closers.

The constraint that shapes the design is v1. v1's CRITICAL families draw on all
five closers, so applying a restriction changes their combination counts, changes
what `rng.sample` draws, and breaks the frozen digests. The maps are therefore
EMPTY by default and populated at v2 build time, exactly as PHRASE_FORMS and
CONCEPT_RELATIONS are.

These tests pin: empty means untouched, populated means restricted, and the
restricted class can still fill its bucket.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dataset import generate_large_dataset as G  # noqa: E402
from dataset import vocabulary as V  # noqa: E402

CLASS_SHARE = G.CLASS_SHARES["CRITICAL"]
V2_TARGET = 1_728_000


def _sizes():
    """(family count, total combinations, CRITICAL combinations)."""
    families = G.build_families()
    crit = sum(f.combinations for f in families if f.urgency == "CRITICAL")
    return len(families), sum(f.combinations for f in families), crit


def test_empty_maps_leave_the_families_exactly_as_they_were():
    """The v1 guarantee. Empty must mean *no* narrowing, not 'narrowed to nothing'."""
    assert V.CONTEXTS_BY_URGENCY == {}
    assert V.CLOSERS_BY_URGENCY == {}
    n, total, crit = _sizes()
    # v1's shape, which verify-full checks byte-for-byte downstream of this.
    assert (n, total) == (160, 6_900_000)
    assert crit == 2_550_000


def test_restricting_critical_shrinks_only_critical():
    """Populating the map narrows the intended class and nothing else."""
    _, total_before, crit_before = _sizes()
    kept = tuple(c for c in V.CLOSERS["kinyarwanda"]
                 if c not in V.V2_CRITICAL_CLOSER_EXCLUSIONS)
    assert len(kept) == len(V.CLOSERS["kinyarwanda"]) - 1, "expected to drop exactly one"

    V.CLOSERS_BY_URGENCY["CRITICAL"] = {"kinyarwanda": kept}
    G.CLOSERS_BY_URGENCY = V.CLOSERS_BY_URGENCY
    try:
        _, total_after, crit_after = _sizes()
        # Only the kinyarwanda-framed CRITICAL families shrink, and by 4/5.
        assert crit_after < crit_before
        assert total_after < total_before
        non_crit_before = total_before - crit_before
        non_crit_after = total_after - crit_after
        assert non_crit_after == non_crit_before, "a restriction leaked into another class"
    finally:
        V.CLOSERS_BY_URGENCY.clear()
        G.CLOSERS_BY_URGENCY = V.CLOSERS_BY_URGENCY

    assert _sizes() == (160, total_before, crit_before), "cleanup must restore v1"


def test_the_excluded_closer_is_the_casual_one():
    """The ruling, as a test: CRITICAL drops the sign-off, keeps the question."""
    excluded = V.V2_CRITICAL_CLOSER_EXCLUSIONS
    assert ". Murakoze." in excluded, "the bare thank-you reads casual after an emergency"
    assert ". Nkora iki?" not in excluded, "'What do I do?' is a real question in an emergency"
    assert ". Ndakeneye ubufasha vuba." not in excluded
    assert ". Mfasha muganga." not in excluded
    for closer in excluded:
        assert closer in V.CLOSERS["kinyarwanda"], f"{closer!r} is not a closer"


def test_critical_still_clears_its_bucket_after_the_restriction():
    """Capacity, not language, is what decides whether a restriction is safe.

    ROUTINE could not survive the equivalent cut — it has 3.24x headroom and the
    restriction would take it to 1.16x, or below 1.0 if the openers went too.
    CRITICAL has roughly 9x, so dropping one closer of five is affordable. The
    numbers are in docs/urgency-frame-coupling.md; this asserts the conclusion.
    """
    frame_full = (len(V.OPENERS["kinyarwanda"]) * len(V.ONSETS["kinyarwanda"])
                  * len(V.CONTEXTS["kinyarwanda"]) * len(V.CLOSERS["kinyarwanda"]))
    kept = len(V.CLOSERS["kinyarwanda"]) - len(V.V2_CRITICAL_CLOSER_EXCLUSIONS)
    frame_restricted = frame_full // len(V.CLOSERS["kinyarwanda"]) * kept

    # Projected CRITICAL phrase instances at full v2, from the brief. Held at a
    # floor rather than recomputed here so this test does not depend on drafting
    # progress; see the design doc for the derivation.
    instances = 350
    families_drawing_on_one_inventory = len(V.LANGUAGES) + len(V.MIXED_PAIRS)

    need = V2_TARGET * CLASS_SHARE
    have = instances * frame_restricted * families_drawing_on_one_inventory
    assert have > need, f"CRITICAL would not fill its bucket: {have:,} < {need:,.0f}"
    assert have / need > 5, "headroom should stay comfortable, not merely positive"
