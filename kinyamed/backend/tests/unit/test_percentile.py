"""The Python percentile agrees with PostgreSQL's `percentile_cont`.

`wait_percentiles_by_urgency` used to compute p50/p90 in SQL. It now computes
them in Python so the suite does not require a PostgreSQL-only function, and
the docstring claims the two produce identical numbers. A claim like that is
worth exactly as much as the test behind it, so this runs both and compares.

The SQL half is skipped automatically on a backend without `percentile_cont`,
which is the whole point: the Python half still runs and still has to be right.
"""

from __future__ import annotations

import pytest
from app.repositories.queue_repo import _percentile
from sqlalchemy import Float, column, func, select, values

# Shapes that break naive implementations: an even count (the median falls
# between two samples), a single sample, a flat list, one with a long tail, and
# a count where the p90 rank lands exactly on an index.
DATASETS = [
    [10.0, 20.0],
    [7.5],
    [4.0, 4.0, 4.0, 4.0],
    [1.0, 2.0, 3.0, 4.0, 100.0],
    [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0],
    [3.0, 1.0, 2.0],  # unsorted input, sorted by the caller
]
FRACTIONS = [0.5, 0.9]


@pytest.mark.parametrize("data", DATASETS, ids=lambda d: f"n={len(d)}")
@pytest.mark.parametrize("fraction", FRACTIONS)
def test_matches_postgres_percentile_cont(db, data, fraction) -> None:
    """Both implementations, same input, same answer."""
    rows = values(column("v", Float), name="samples").data([(v,) for v in data])
    expected = db.scalar(
        select(func.percentile_cont(fraction).within_group(rows.c.v)).select_from(rows)
    )
    assert expected is not None

    actual = _percentile(sorted(data), fraction)
    assert actual == pytest.approx(float(expected), abs=1e-9), (
        f"Python percentile disagrees with percentile_cont on {data} at "
        f"{fraction}: {actual} vs {expected}. The docstring on "
        "wait_percentiles_by_urgency promises they match."
    )


def test_single_sample_is_that_sample() -> None:
    assert _percentile([42.0], 0.5) == 42.0
    assert _percentile([42.0], 0.9) == 42.0


def test_empty_returns_zero_but_callers_must_not_rely_on_it() -> None:
    """An acuity with no completed entries is OMITTED by the caller.

    Reporting 0.0 would read as "seen instantly", which is the opposite of
    "not measured". This return exists so the helper is total, not so the
    endpoint can report a zero.
    """
    assert _percentile([], 0.5) == 0.0


def test_interpolates_rather_than_picking_a_neighbour() -> None:
    """p50 of [10, 20] is 15, not 10 or 20.

    A nearest-rank implementation would return one of the samples. That is a
    legitimate definition of percentile, but it is NOT the one percentile_cont
    uses, and mixing the two across a migration would silently move every
    number on the dashboard.
    """
    assert _percentile([10.0, 20.0], 0.5) == 15.0
