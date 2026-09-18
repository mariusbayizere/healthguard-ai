"""G6 must be able to reach every verdict. The version before it could reach one.

Until 2026-09-18 `_g6` returned a hardcoded NOT COMPUTABLE string and read no
column. It gave the same answer for a corpus that records reporter and age group
as for one that records neither, which means it was not measuring anything. The
generated corpus lacked both fields, so the stub's answer happened to be true
and nobody looked; the labelled corpus has both, and the stub would still have
said the corpus carries neither.

These tests pin the property that was missing: the verdict must depend on the
input. Each of PASS, FAIL and NOT COMPUTABLE is reachable, and the reason
attached to NOT COMPUTABLE has to name what is missing rather than assert it.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

gates = pytest.importorskip("dataset.corpus_gates")


def g6(rows):
    return gates._g6(rows)


def test_not_computable_when_the_columns_are_absent() -> None:
    """The generated corpus's case. Still NOT COMPUTABLE, but now derived."""
    result = g6([{"text": "x", "seed_id": "1"}])
    assert result.passed is None
    assert "reporter" in result.detail and "age_group" in result.detail


def test_fails_when_a_row_is_missing_one_of_the_fields() -> None:
    """An incomplete record is a failure, not an uncomputable question."""
    rows = [
        {"reporter": "Self", "age_group": "adult"},
        {"reporter": "", "age_group": "adult"},
    ]
    result = g6(rows)
    assert result.passed is False
    assert "1/2" in result.detail


def test_not_computable_but_specific_when_no_pairs_are_ratified() -> None:
    """The labelled corpus's case: both fields present, no ruling to check them."""
    rows = [{"reporter": "Self", "age_group": "adult"}] * 3
    result = g6(rows)
    assert result.passed is None
    # It must name the observed pairs, so the reader can go and ratify them.
    assert "Self x adult" in result.detail
    assert "PERMITTED_REPORTER_AGE" in result.detail


def test_passes_when_every_observed_pair_is_ratified(monkeypatch) -> None:
    monkeypatch.setattr(gates, "PERMITTED_REPORTER_AGE", frozenset({("Self", "adult")}))
    result = g6([{"reporter": "Self", "age_group": "adult"}] * 4)
    assert result.passed is True
    assert result.verdict == "PASS"


def test_fails_on_a_pair_outside_the_ratified_set(monkeypatch) -> None:
    """An infant cannot self-report; once the ruling exists, the gate enforces it."""
    monkeypatch.setattr(
        gates, "PERMITTED_REPORTER_AGE", frozenset({("Carer", "infant")})
    )
    rows = [{"reporter": "Carer", "age_group": "infant"}] * 3 + [
        {"reporter": "Self", "age_group": "infant"}
    ]
    result = g6(rows)
    assert result.passed is False
    assert "Self x infant" in result.detail


def test_the_verdict_actually_depends_on_the_input() -> None:
    """The property the stub lacked, asserted directly."""
    verdicts = {
        g6([{"text": "x"}]).verdict,
        g6([{"reporter": "Self", "age_group": "adult"}]).verdict,
        g6([{"reporter": "", "age_group": "adult"}]).verdict,
    }
    assert len(verdicts) > 1, (
        "G6 returns the same verdict for every input, which is what the "
        "hardcoded version did"
    )


def test_permitted_pairs_start_empty_and_that_is_deliberate() -> None:
    """Nobody has ruled on which pairs are coherent; the gate must not guess."""
    assert gates.PERMITTED_REPORTER_AGE == frozenset()
