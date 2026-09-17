"""Logout blocklist, and what happens when Redis is not there (FR-05-10, §6.3).

WHY A BLOCKLIST AT ALL. Logout revokes the refresh token in Postgres, so the
session cannot be extended. It does not touch the ACCESS token, which stays
valid for up to fifteen minutes because nothing checks it against anything. For
most of that window a stolen token still opens the ward queue. The blocklist
closes the window: logout records the token's `jti`, and every authenticated
request checks it.

THE FALLBACK MATTERS MORE THAN THE FEATURE. A service that crashes when Redis is
down is worse than one that degrades: the queue stops, and a clinic loses triage
because a cache is unavailable. §6.3 requires falling back to database-only
state with no crash. So these cases run Redis absent as well as present, and the
absent case is the one to read first.

What degrades, stated plainly: without Redis an access token remains usable
until it expires, which is the behaviour the system had before the blocklist
existed. Refresh revocation is unaffected, because that lives in Postgres.
"""

from __future__ import annotations

import pytest
from app.core.config import settings

REGISTRATION = {
    "email": "blocked@kinyamed.rw",
    "password": "Correct-Horse9-battery",
    "full_name": "Block Listed",
    "phone": "0788124111",
}


def _register(client) -> str:
    response = client.post("/api/v1/auth/register", json=REGISTRATION)
    assert response.status_code in (200, 201), response.text
    token = response.json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return token


@pytest.fixture
def with_redis(monkeypatch):
    """A real Redis, flushed. Skipped locally, REQUIRED on the runner.

    Skipping is a reasonable courtesy on a developer machine with no Redis. It
    is not reasonable in CI: the job would go green having run none of these
    cases, and "CI is green" would then say nothing about whether logout
    withdraws a token. The runner sets CI=true, so there the absence is a
    failure and names the service that is missing.
    """
    import os

    from app.core import token_blocklist

    monkeypatch.setattr(settings, "BLOCKLIST_ENABLED", True)
    token_blocklist.reset_client()
    client = token_blocklist.get_client()
    if client is None:
        if os.environ.get("CI"):
            pytest.fail(
                "Redis is unreachable on the runner, so the blocklist cases "
                "would have skipped and the job would have gone green without "
                "running them. Check the redis service in .github/workflows/ci.yml."
            )
        pytest.skip("Redis is not reachable; the fallback cases still run")
    client.flushdb()
    yield client
    client.flushdb()
    token_blocklist.reset_client()


@pytest.fixture
def without_redis(monkeypatch):
    """Point the blocklist at a closed port: Redis is down, not misconfigured."""
    from app.core import token_blocklist

    monkeypatch.setattr(settings, "BLOCKLIST_ENABLED", True)
    monkeypatch.setattr(settings, "REDIS_URL", "redis://127.0.0.1:1/0")
    token_blocklist.reset_client()
    yield
    token_blocklist.reset_client()


# ── The fallback: read this first ────────────────────────────────────────


def test_the_service_still_answers_when_redis_is_down(without_redis, anon_client):
    """§6.3: degrade, never crash."""
    _register(anon_client)
    assert anon_client.get("/api/v1/auth/me").status_code == 200


def test_logging_out_succeeds_when_redis_is_down(without_redis, anon_client):
    """A client must always be able to clear its own session."""
    _register(anon_client)
    assert anon_client.post("/api/v1/auth/logout").status_code == 200


def test_refresh_revocation_is_unaffected_by_redis_being_down(
    without_redis, anon_client
):
    """It lives in Postgres, so the session still cannot be extended."""
    _register(anon_client)
    anon_client.post("/api/v1/auth/logout")
    assert anon_client.post("/api/v1/auth/refresh").status_code == 401


def test_readiness_reports_redis_rather_than_failing(without_redis, anon_client):
    """Degraded is a state to be visible in, not one to hide."""
    response = anon_client.get("/health/ready")
    assert response.status_code in (200, 503)
    assert "redis" in response.json(), (
        "readiness says nothing about Redis, so nobody learns the blocklist is off"
    )


# ── The feature, with Redis present ──────────────────────────────────────


def test_an_access_token_stops_working_after_logout(with_redis, anon_client):
    """The fifteen-minute window is what the blocklist exists to close."""
    _register(anon_client)
    assert anon_client.get("/api/v1/auth/me").status_code == 200

    assert anon_client.post("/api/v1/auth/logout").status_code == 200
    assert anon_client.get("/api/v1/auth/me").status_code == 401, (
        "the access token still worked after logout; the window is open"
    )


def test_logging_out_everywhere_blocks_the_calling_session(with_redis, anon_client):
    _register(anon_client)
    assert anon_client.post("/api/v1/auth/logout-all").status_code == 200
    assert anon_client.get("/api/v1/auth/me").status_code == 401


def test_another_session_is_unaffected_by_one_logout(
    with_redis, anon_client, make_client
):
    """Blocking is per token, not per user."""
    _register(anon_client)
    other = make_client()
    login = other.post(
        "/api/v1/auth/login",
        json={"email": REGISTRATION["email"], "password": REGISTRATION["password"]},
    )
    other.headers["Authorization"] = f"Bearer {login.json()['access_token']}"

    anon_client.post("/api/v1/auth/logout")
    assert other.get("/api/v1/auth/me").status_code == 200


def test_a_blocked_entry_expires_with_the_token(with_redis, anon_client):
    """Entries carry a TTL: the blocklist must not grow without bound.

    A token that has expired is refused by signature checking anyway, so
    holding its id forever buys nothing and costs memory on a box that also
    serves the queue.
    """
    from app.core import token_blocklist

    _register(anon_client)
    anon_client.post("/api/v1/auth/logout")

    keys = with_redis.keys(f"{token_blocklist.KEY_PREFIX}*")
    assert keys, "logout recorded nothing"
    for key in keys:
        ttl = with_redis.ttl(key)
        assert ttl > 0, f"{key!r} has no expiry; the blocklist grows for ever"
        assert ttl <= settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60 + 60
