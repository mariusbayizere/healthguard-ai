"""Authentication endpoints have their own, much tighter budget (FR-05-09).

Before 2026-09-17 there was one global bucket of 120 requests per 60 seconds
covering every route, so a password-guessing client had 120 attempts a minute
and shared that allowance with ordinary traffic. The requirement is ten
attempts per fifteen minutes per IP, and that only means something if the
counter is separate: a burst of queue polling must not consume the login budget,
and exhausting the login budget must not lock a clinician out of the queue.

ATTRIBUTION IS THE WHOLE GAME. A limiter keyed on an address the caller can
choose is not a limiter. These tests pin the X-Forwarded-For rule on the auth
path specifically: the header is believed only when the TCP peer is a
configured trusted proxy, and the client is then the right-most hop that is not
itself a proxy.
"""

from __future__ import annotations

import pytest
from app.core.config import settings

LOGIN = "/api/v1/auth/login"
CREDENTIALS = {"email": "nobody@kinyamed.rw", "password": "Wrong-Password9"}


@pytest.fixture
def auth_limited(monkeypatch, anon_client):
    """Enable both limiters with small, distinguishable budgets."""
    from app.core import middleware

    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    monkeypatch.setattr(settings, "RATE_LIMIT_REQUESTS", 50)
    monkeypatch.setattr(settings, "RATE_LIMIT_WINDOW_SECONDS", 60)
    monkeypatch.setattr(settings, "AUTH_RATE_LIMIT_REQUESTS", 10)
    monkeypatch.setattr(settings, "AUTH_RATE_LIMIT_WINDOW_SECONDS", 900)
    middleware.reset_rate_limit_state()
    yield anon_client
    middleware.reset_rate_limit_state()


def _attempt(client, **kwargs):
    return client.post(LOGIN, json=CREDENTIALS, **kwargs)


# ── The budget ───────────────────────────────────────────────────────────


def test_the_eleventh_attempt_in_the_window_is_refused(auth_limited) -> None:
    statuses = [_attempt(auth_limited).status_code for _ in range(10)]
    assert 429 not in statuses, f"refused inside the budget of 10: {statuses}"

    refused = _attempt(auth_limited)
    assert refused.status_code == 429
    assert refused.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"


def test_the_refusal_carries_the_auth_window_not_the_global_one(auth_limited) -> None:
    """Retry-After must describe the budget that was actually exhausted."""
    for _ in range(11):
        last = _attempt(auth_limited)
    assert last.status_code == 429
    assert last.headers["Retry-After"] == "900"


def test_failed_attempts_count(auth_limited) -> None:
    """Brute force is made of failures; counting only successes counts nothing."""
    for _ in range(10):
        response = _attempt(auth_limited)
        assert response.status_code == 401
    assert _attempt(auth_limited).status_code == 429


# ── Separation from the general bucket ───────────────────────────────────


def test_ordinary_traffic_does_not_consume_the_login_budget(auth_limited) -> None:
    for _ in range(30):
        auth_limited.get("/api/v1/patients")
    assert _attempt(auth_limited).status_code != 429


def test_exhausting_the_login_budget_does_not_block_other_routes(auth_limited) -> None:
    """A clinician mistyping a password must not lose access to the queue."""
    for _ in range(11):
        _attempt(auth_limited)
    assert auth_limited.get("/api/v1/patients").status_code != 429


def test_refreshing_a_session_is_not_an_authentication_attempt(auth_limited) -> None:
    """Refresh runs on a timer, once per access-token lifetime per session.

    Counting it against ten-per-fifteen-minutes would throttle a clinician with
    several tabs open for doing nothing wrong.
    """
    for _ in range(11):
        _attempt(auth_limited)
    refused = auth_limited.post("/api/v1/auth/refresh")
    assert refused.status_code != 429


# ── Attribution ──────────────────────────────────────────────────────────


def test_a_spoofed_forwarded_header_does_not_buy_a_fresh_budget(
    auth_limited, monkeypatch
) -> None:
    """The TCP peer is not a trusted proxy here, so the header is ignored."""
    monkeypatch.setattr(settings, "TRUSTED_PROXIES", "")
    for index in range(11):
        last = _attempt(auth_limited, headers={"X-Forwarded-For": f"10.0.0.{index}"})
    assert last.status_code == 429, (
        "a caller rotated X-Forwarded-For and was given a new bucket each time"
    )


def test_the_forwarded_header_is_honoured_only_behind_a_trusted_proxy(
    monkeypatch,
) -> None:
    """Attribution itself, tested where it can be: `client_ip`.

    It cannot be exercised through the TestClient, whose peer is the literal
    string "testclient" and so can never be a configured proxy address. Driving
    the function directly is the honest way to pin the rule rather than to
    assert something weaker through HTTP and call it covered.
    """
    from app.core.middleware import client_ip

    def request_from(peer: str, forwarded: str | None):
        scope = {
            "type": "http",
            "headers": [(b"x-forwarded-for", forwarded.encode())] if forwarded else [],
            "client": (peer, 1234),
        }
        from starlette.requests import Request

        return Request(scope)

    monkeypatch.setattr(settings, "TRUSTED_PROXIES", "")
    assert client_ip(request_from("198.51.100.9", "203.0.113.7")) == "198.51.100.9", (
        "an untrusted peer's header was believed"
    )

    monkeypatch.setattr(settings, "TRUSTED_PROXIES", "198.51.100.0/24")
    assert client_ip(request_from("198.51.100.9", "203.0.113.7")) == "203.0.113.7"

    # A client-supplied hop to the LEFT of the proxy chain is ignored: the
    # client is the right-most entry that is not itself a trusted proxy.
    assert (
        client_ip(request_from("198.51.100.9", "1.1.1.1, 203.0.113.7")) == "203.0.113.7"
    )
    # A proxy appending its own address must not become the attributed client.
    assert (
        client_ip(request_from("198.51.100.9", "203.0.113.7, 198.51.100.4"))
        == "203.0.113.7"
    )


def test_probes_are_never_auth_limited(auth_limited) -> None:
    for _ in range(11):
        _attempt(auth_limited)
    assert auth_limited.get("/health").status_code == 200
