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
    assert rate_limited.get("/health/ready").status_code == 200


# ── Client identity: X-Forwarded-For is only believed from a trusted proxy ──
#
# The limiter used to key on the first X-Forwarded-For entry from ANY caller.
# Measured in the Phase 0 audit: after exhausting the limit, 30 of 30 requests
# with a rotated header were accepted. These tests build a fresh app per test so
# limiter state cannot leak between them.


def _limited_app(monkeypatch, *, trusted: str = ""):
    from app.core.middleware import register_middleware
    from fastapi import FastAPI

    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_REQUESTS", 3)
    monkeypatch.setattr(settings, "RATE_LIMIT_WINDOW_SECONDS", 60)
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", trusted)

    app = FastAPI()
    register_middleware(app)

    @app.get("/api/v1/thing")
    def thing() -> dict[str, bool]:
        return {"ok": True}

    return app


def test_a_rotated_forwarded_for_does_not_bypass_the_limit(monkeypatch):
    from fastapi.testclient import TestClient

    client = TestClient(_limited_app(monkeypatch), client=("203.0.113.9", 5000))
    assert [client.get("/api/v1/thing").status_code for _ in range(3)] == [200] * 3

    spoofed = [
        client.get(
            "/api/v1/thing", headers={"X-Forwarded-For": f"10.9.{i}.1"}
        ).status_code
        for i in range(30)
    ]
    assert spoofed == [429] * 30, "a client-supplied X-Forwarded-For reset the limit"


def test_forwarded_for_from_an_untrusted_peer_is_ignored(monkeypatch):
    """Two callers behind no proxy, claiming the same forwarded address, are two callers."""
    from fastapi.testclient import TestClient

    app = _limited_app(monkeypatch)
    first = TestClient(app, client=("203.0.113.10", 5000))
    second = TestClient(app, client=("203.0.113.11", 5000))
    claim = {"X-Forwarded-For": "198.51.100.7"}

    for _ in range(3):
        assert first.get("/api/v1/thing", headers=claim).status_code == 200
    assert second.get("/api/v1/thing", headers=claim).status_code == 200


def test_a_trusted_proxy_forwards_the_real_client(monkeypatch):
    from fastapi.testclient import TestClient

    app = _limited_app(monkeypatch, trusted="10.0.0.0/8")
    proxy = TestClient(app, client=("10.0.0.5", 5000))

    alice = {"X-Forwarded-For": "198.51.100.7"}
    bob = {"X-Forwarded-For": "198.51.100.8"}
    assert [
        proxy.get("/api/v1/thing", headers=alice).status_code for _ in range(4)
    ] == [
        200,
        200,
        200,
        429,
    ]
    assert proxy.get("/api/v1/thing", headers=bob).status_code == 200, (
        "every client behind the proxy shared one bucket"
    )


def test_a_client_cannot_spoof_through_a_trusted_proxy(monkeypatch):
    """A proxy APPENDS the address it saw; what the client wrote sits to its left.

    The client is the right-most address that is not a trusted proxy, so a
    rotated left-hand value changes nothing.
    """
    from fastapi.testclient import TestClient

    proxy = TestClient(
        _limited_app(monkeypatch, trusted="10.0.0.0/8"), client=("10.0.0.5", 5000)
    )
    statuses = [
        proxy.get(
            "/api/v1/thing", headers={"X-Forwarded-For": f"1.2.3.{i}, 198.51.100.7"}
        ).status_code
        for i in range(10)
    ]
    assert statuses == [200, 200, 200] + [429] * 7


def test_an_invalid_trusted_proxy_setting_fails_at_startup():
    from app.core.config import Settings
    from pydantic import ValidationError

    with pytest.raises(ValidationError, match="TRUSTED_PROXIES"):
        Settings(TRUSTED_PROXIES="not-an-address")
