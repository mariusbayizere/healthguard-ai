"""A concept's two phrasings must reach the corpus as one phrase group.

The corpus wants variety — a different patient says the same thing differently —
so neither phrasing is discarded. But phrase_components closes only over
substring containment, which catches a nested phrase and misses a divergent one.
The speaker's two indigestion phrasings share twenty-one characters and neither
contains the other, so nothing unions them and the phrase holdout could train on
one while evaluating the other.

These pin the declaration that prevents it, and the reader that fills it.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

EX16 = "iyo maze kurya numva inda itameze neza"
EX17 = "iyo maze kurya numva mu nda ntameze neza"


def test_the_two_indigestion_phrasings_are_not_substrings_of_each_other() -> None:
    """The premise. If this ever became false the declaration would be redundant."""
    assert EX16 not in EX17 and EX17 not in EX16
    shared = 0
    for a, b in zip(EX16, EX17):
        if a != b:
            break
        shared += 1
    assert shared > 15, "the shared prefix is what makes splitting them a leak"


def _components(monkeypatch, phrases: list[str], variants: dict[str, str]) -> dict[str, str]:
    import dataset.split_dataset as S
    import dataset.vocabulary as V

    monkeypatch.setattr(S, "all_symptom_phrases", lambda: {"kinyarwanda": tuple(phrases)})
    monkeypatch.setattr(S, "PHRASE_VARIANTS", variants)
    monkeypatch.setattr(V, "PHRASE_VARIANTS", variants, raising=False)
    return S.phrase_components()


def test_divergent_phrasings_split_without_the_declaration(monkeypatch) -> None:
    """Without it they are two groups — which is the bug, shown rather than asserted away."""
    groups = _components(monkeypatch, [EX16, EX17], {})
    assert groups[EX16] != groups[EX17]


def test_a_declared_second_phrasing_shares_its_primary_group(monkeypatch) -> None:
    groups = _components(monkeypatch, [EX16, EX17], {EX17: EX16})
    assert groups[EX16] == groups[EX17], (
        "a declared pairing must put both phrasings in one phrase group, or the "
        "holdout can train on one and evaluate on the other"
    )


def test_a_pairing_naming_an_absent_phrase_raises(monkeypatch) -> None:
    """Silence would leave the pair in separate groups — the exact failure the
    declaration exists to prevent. It must refuse instead."""
    with pytest.raises(SystemExit, match="not in the symptom inventory"):
        _components(monkeypatch, [EX16], {EX17: EX16})


def test_reader_extracts_pairs_and_rejects_malformed_ones(tmp_path: Path) -> None:
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from review.second_phrasings import second_phrasings

    def brief(rows: list[dict]) -> Path:
        path = tmp_path / f"brief{len(list(tmp_path.iterdir()))}.csv"
        fields = ["concept_id", "person", "applies", "your_phrasing", "second_phrasing_optional"]
        with path.open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        return path

    ok = brief([
        {"concept_id": "EX16", "person": "first", "applies": "yes",
         "your_phrasing": EX16, "second_phrasing_optional": EX17},
        {"concept_id": "GI02", "person": "first", "applies": "yes",
         "your_phrasing": "Ndaruka amaraso.", "second_phrasing_optional": ""},
    ])
    assert second_phrasings(ok) == {EX17: EX16}

    # applies=no rows contribute nothing
    skipped = brief([{"concept_id": "GI08", "person": "first", "applies": "no",
                      "your_phrasing": EX16, "second_phrasing_optional": EX17}])
    assert second_phrasings(skipped) == {}

    orphan = brief([{"concept_id": "EX16", "person": "first", "applies": "yes",
                     "your_phrasing": "", "second_phrasing_optional": EX17}])
    with pytest.raises(SystemExit, match="no primary"):
        second_phrasings(orphan)

    same = brief([{"concept_id": "EX16", "person": "first", "applies": "yes",
                   "your_phrasing": EX16, "second_phrasing_optional": EX16}])
    with pytest.raises(SystemExit, match="identical"):
        second_phrasings(same)


def test_the_real_brief_parses(ml_root: Path) -> None:
    """Whatever the brief holds today, the reader must cope with it."""
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from review.second_phrasings import second_phrasings

    brief = ml_root / "review/speaker_brief_kinyarwanda_v2.csv"
    if not brief.exists():                                  # pragma: no cover
        pytest.skip("brief not present")
    assert isinstance(second_phrasings(brief), dict)
