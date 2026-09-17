"""The bcrypt cost factor is real work, not a configured number (FR-05-11).

The suite runs at cost 4 so that creating fixture users does not add minutes to
every run (`tests/conftest.py`). The consequence, until 2026-09-17, was that
NOTHING exercised cost 12: production configuration was asserted, and the digest
it would actually produce was never computed. A setting whose effect is never
measured is a claim, and this file measures it.

TWO CHECKS, because either alone can pass while the property is false:

  * the digest's own embedded cost, which is deterministic and exact;
  * elapsed time, because a cost recorded in the digest is worth nothing unless
    the work was done. bcrypt doubles per increment, so cost 12 is 2^8 = 256
    times cost 4; the bound below is deliberately far looser than that, to be
    a real signal on a loaded laptop rather than a flaky one.

The timing bound is a floor on slowness. It can fail only if hashing got much
cheaper, which is exactly the regression worth catching: a library swapped for
a stub, a cost silently clamped, a digest copied rather than computed.
"""

from __future__ import annotations

import time

from app.core import security
from app.core.config import settings

PRODUCTION_COST = 12
# Cost 12 is ~0.2-0.5 s on the reference CPU (i5-6200U). 50 ms is a floor no
# real cost-12 hash can fall below, and well clear of scheduler noise.
MIN_SECONDS_AT_PRODUCTION_COST = 0.05
# 2^8 = 256 in theory. 20 leaves room for a loaded machine without admitting a
# cost that is off by more than an increment or two.
MIN_RATIO_OVER_COST_FOUR = 20


def _cost_of(digest: str) -> int:
    """bcrypt digests are $2b$<cost>$<salt+hash>."""
    return int(digest.split("$")[2])


def _time_one_hash(rounds: int, monkeypatch) -> tuple[str, float]:
    monkeypatch.setattr(settings, "BCRYPT_ROUNDS", rounds)
    started = time.perf_counter()
    digest = security.hash_password("Correct-Horse9-battery")
    return digest, time.perf_counter() - started


def test_the_digest_records_the_configured_cost(monkeypatch) -> None:
    digest, _ = _time_one_hash(PRODUCTION_COST, monkeypatch)
    assert _cost_of(digest) == PRODUCTION_COST


def test_hashing_at_production_cost_actually_costs(monkeypatch) -> None:
    """The work is done, not merely labelled."""
    _, elapsed = _time_one_hash(PRODUCTION_COST, monkeypatch)
    assert elapsed >= MIN_SECONDS_AT_PRODUCTION_COST, (
        f"a cost-{PRODUCTION_COST} hash took {elapsed:.4f}s, which is too fast "
        "to have done the work; the cost factor is not being applied"
    )


def test_production_cost_is_far_slower_than_the_suite_cost(monkeypatch) -> None:
    """Relative, so it holds on hardware faster or slower than the reference."""
    _, cheap = _time_one_hash(4, monkeypatch)
    _, dear = _time_one_hash(PRODUCTION_COST, monkeypatch)
    assert dear > cheap * MIN_RATIO_OVER_COST_FOUR, (
        f"cost 4 took {cheap:.4f}s and cost {PRODUCTION_COST} took {dear:.4f}s, "
        f"a ratio of {dear / cheap:.1f}x; {MIN_RATIO_OVER_COST_FOUR}x is the "
        "floor for a genuine eight-increment difference"
    )


def test_a_password_verifies_against_a_production_cost_digest(monkeypatch) -> None:
    """Raising the cost must not break the credential it protects."""
    password = "Correct-Horse9-battery"
    monkeypatch.setattr(settings, "BCRYPT_ROUNDS", PRODUCTION_COST)
    digest = security.hash_password(password)
    assert security.verify_password(password, digest)
    assert not security.verify_password("Wrong-Horse9-battery", digest)


def test_a_digest_made_at_the_suite_cost_still_verifies(monkeypatch) -> None:
    """The cost lives in the digest, so raising the setting cannot lock anyone out.

    This is why a cost increase needs no migration: existing digests carry their
    own cost and keep verifying.
    """
    password = "Correct-Horse9-battery"
    monkeypatch.setattr(settings, "BCRYPT_ROUNDS", 4)
    old = security.hash_password(password)
    monkeypatch.setattr(settings, "BCRYPT_ROUNDS", PRODUCTION_COST)
    assert security.verify_password(password, old)


def test_production_configuration_refuses_a_lower_cost() -> None:
    """The setting is a floor in production, not a default."""
    from app.core.config import Settings

    development = Settings(
        ENVIRONMENT="development",
        DATABASE_URL="postgresql://u:p@localhost:5432/db",
        SMS_API_KEY="x",
        BCRYPT_ROUNDS=4,
    )
    assert any(
        "BCRYPT_ROUNDS" in problem for problem in development.hardening_problems()
    )
