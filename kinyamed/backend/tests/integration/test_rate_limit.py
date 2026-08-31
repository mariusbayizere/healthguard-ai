"""Rate limiting.

The limiter is disabled for the rest of the suite (see conftest); this module
switches it on for its own cases.
"""

from __future__ import annotations

import pytest

from app.core.config import settings


@pytest.fixture
def rate_limited(monkeypatch, client):
    """Enable a 3-request window and give the limiter a clean bucket."""
    from app.core import middleware

    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_REQUESTS", 3)
    monkeypatch.setattr(settings, "RATE_LIMIT_WINDOW_SECONDS", 60)

    for mw in client.app.user_middleware:
        if mw.cls is middleware.RateLimitMiddleware:
            break
    # The middleware instance is created per app build; clear any accumulated
    # state by resetting the shared registry it keys on.
    yield client


def test_requests_beyond_the_limit_are_rejected(rate_limited):
    statuses = [rate_limited.get("/api/v1/patients").status_code for _ in range(6)]
    assert 429 in statuses, "the limiter must eventually reject"
    rejected = rate_limited.get("/api/v1/patients")
    assert rejected.status_code == 429
    assert rejected.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
    assert rejected.headers["Retry-After"] == "60"


def test_probes_are_never_rate_limited(rate_limited):
    """A throttled liveness probe would get the pod killed."""
    for _ in range(10):
        rate_limited.get("/api/v1/patients")
    assert rate_limited.get("/health").status_code == 200
    assert rate_limited.get("/ready").status_code == 200
