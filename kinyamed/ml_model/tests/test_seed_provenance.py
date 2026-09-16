"""dataset/seed_provenance.py: how many distinct source seeds a split has, and how many
it shares with the split it will be compared against.

This is the first number a reviewer asks of any metric computed on generated data, so it
goes at the top of every report that carries one. Synthetic fixtures only.
"""

from __future__ import annotations

import csv

import pytest
from dataset import seed_provenance as sp


def _write(path, rows, column="phrase"):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["text", "language", "label", column]
        )
        writer.writeheader()
        writer.writerows(rows)
    return path


def _rows(seeds, per_seed=3, language="kinyarwanda"):
    return [
        {
            "text": f"placeholder {s} row{k}",
            "language": language,
            "label": "CRITICAL",
            "phrase": s,
        }
        for s in seeds
        for k in range(per_seed)
    ]


def test_it_counts_distinct_seeds_and_rows_per_seed(tmp_path):
    path = _write(tmp_path / "train.csv", _rows(["a", "b", "c"], per_seed=4))
    summary = sp.summarise(path, seed_column="phrase")
    assert summary.rows == 12
    assert summary.distinct_seeds == 3
    assert summary.rows_per_seed_max == 4
    assert summary.largest_seed_share == pytest.approx(4 / 12)


def test_it_reports_the_overlap_between_two_splits(tmp_path):
    train = _write(tmp_path / "train.csv", _rows(["a", "b", "c"]))
    test = _write(tmp_path / "test.csv", _rows(["c", "d"]))
    overlap = sp.overlap(train, test, seed_column="phrase")
    assert overlap.shared_seeds == ["c"]
    assert overlap.test_seeds == 2
    assert overlap.shared_test_rows == 3


def test_disjoint_splits_report_no_shared_seed(tmp_path):
    train = _write(tmp_path / "train.csv", _rows(["a", "b"]))
    test = _write(tmp_path / "test.csv", _rows(["c"]))
    assert sp.overlap(train, test, seed_column="phrase").shared_seeds == []


def test_the_banner_states_shared_provenance_even_when_no_seed_is_shared(tmp_path):
    """Disjoint seeds are not independent data: both splits come from one generator and
    one inventory, so a metric measured across them is within-distribution."""
    train = _write(tmp_path / "train.csv", _rows(["a", "b"]))
    test = _write(tmp_path / "test.csv", _rows(["c"]))
    banner = sp.banner(train, test, seed_column="phrase")
    assert "2" in banner and "1" in banner
    assert "same generator" in banner.lower()
    assert "within" in banner.lower()


def test_per_language_counts_are_reported(tmp_path):
    rows = _rows(["a", "b"]) + _rows(["c"], language="english")
    path = _write(tmp_path / "train.csv", rows)
    summary = sp.summarise(path, seed_column="phrase")
    assert summary.seeds_per_language == {"kinyarwanda": 2, "english": 1}
