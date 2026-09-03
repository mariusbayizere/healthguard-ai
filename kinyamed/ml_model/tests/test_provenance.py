"""Provenance categories must be derived, exhaustive, and honest.

The old scheme had one bucket for everything the speaker did not type, so a
`ndi` -> `ari` transform of a sentence they wrote counted the same as a phrase I
composed. The reported speaker rate then fell every time third-person work landed
even though nothing about their involvement changed.

The property that makes the new split defensible is that it is a pure function of
the brief — recomputable by anyone, not a judgement recorded in a note.
"""

from __future__ import annotations

import csv
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "review"))

from provenance import (BRIEF, CATEGORIES, MACHINE_APPROVED,  # noqa: E402
                        MACHINE_DERIVED, NEWLY_COMPOSED, NOT_APPLICABLE,
                        SPEAKER_AUTHORED, SPEAKER_DERIVED, SPEAKERS_OWN_WORDS,
                        classified, classify)


def _rows():
    return list(csv.DictReader(BRIEF.open(encoding="utf-8")))


def test_every_authored_row_lands_in_a_known_category():
    for row, category in classified():
        if not (row["your_phrasing"] or "").strip():
            continue
        assert category in CATEGORIES, f"{row['concept_id']} {row['person']} -> {category!r}"


def test_the_stored_source_matches_what_the_classifier_derives():
    """The column is a cache of the function, not an independent claim."""
    rows = _rows()
    by_key = {(r["concept_id"], r["person"]): r for r in rows}
    for row in rows:
        derived = classify(row, by_key)
        if derived:
            assert (row["source"] or "").strip() == derived, (
                f"{row['concept_id']} {row['person']}: stored "
                f"{row['source']!r} but the classifier derives {derived!r}. "
                "Run: python review/provenance.py --write"
            )


def test_speaker_derived_is_only_ever_a_third_person():
    """A first-person phrase is not a transform; the speaker writes that form.

    IF05, OB02 and OB07 have a speaker-authored THIRD and a machine-drafted
    FIRST. A naive 'counterpart is speaker' test calls those speaker-derived and
    inflates the headline; the direction has to be checked.
    """
    for row, category in classified():
        if category == SPEAKER_DERIVED:
            assert row["person"] == "third", (
                f"{row['concept_id']} {row['person']} is speaker_derived but "
                "only a third person can be a person-transform"
            )


def test_a_derived_row_has_an_authored_counterpart_of_the_right_kind():
    rows = _rows()
    by_key = {(r["concept_id"], r["person"]): r for r in rows}
    for row, category in classified():
        if category not in (SPEAKER_DERIVED, MACHINE_DERIVED):
            continue
        other = by_key[(row["concept_id"], "first")]
        assert (other["your_phrasing"] or "").strip(), "derived from nothing"
        if category == SPEAKER_DERIVED:
            assert other["source"] == SPEAKER_AUTHORED
        else:
            assert other["source"] != SPEAKER_AUTHORED


def test_the_split_reports_the_unflattering_number_too():
    """machine_derived is new and is WORSE than the old scheme admitted.

    Those rows are transforms of phrases I composed, so neither person is speaker
    wording. The old scheme hid them inside machine_approved alongside the
    EX18-type rows. A split that only added a flattering category would not be
    worth adopting.
    """
    counts = Counter(c for r, c in classified()
                     if (r["your_phrasing"] or "").strip()
                     and (r.get("applies") or "yes").lower() != "no")
    assert counts[MACHINE_DERIVED] > 0, (
        "if this ever reaches zero the category is still worth reporting, but "
        "check it is not being mis-derived"
    )
    assert set(NEWLY_COMPOSED) & set(counts), "the honest bucket must be populated"


def test_the_roll_ups_partition_the_authored_rows():
    """Nothing may fall outside the two headline groups except `unresolved`."""
    authored = [(r, c) for r, c in classified()
                if (r["your_phrasing"] or "").strip()
                and (r.get("applies") or "yes").lower() != "no"]
    counts = Counter(c for _, c in authored)
    own = sum(counts.get(c, 0) for c in SPEAKERS_OWN_WORDS)
    fresh = sum(counts.get(c, 0) for c in NEWLY_COMPOSED)
    accounted = own + fresh + counts.get("unresolved", 0)
    assert accounted == len(authored), (
        f"{len(authored) - accounted} authored rows fall outside both roll-ups"
    )


def test_not_applicable_rows_are_never_counted_as_authored():
    for row, category in classified():
        if (row.get("applies") or "yes").strip().lower() == "no":
            assert category == NOT_APPLICABLE
