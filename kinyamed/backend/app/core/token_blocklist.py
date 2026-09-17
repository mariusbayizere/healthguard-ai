"""Access tokens withdrawn before they expire (FR-05-10).

Logging out revokes the refresh token in Postgres, so the session cannot be
extended. It does nothing to the ACCESS token, which stays valid for up to
fifteen minutes because verifying it requires no state. For that window a
stolen token still opens the ward queue. This module closes the window: logout
records the token's `jti`, and `get_current_user` refuses anything listed.

DEGRADE, NEVER CRASH (ENGINEERING_SPEC §6.3). Redis is a cache in front of a
safety property, not a dependency of the request path. Every call here is
wrapped: if Redis is unreachable the service keeps answering, and what is lost
is precisely the early withdrawal — an access token then remains usable until
it expires, which is the behaviour the system had before this module existed.
A clinic must not lose triage because a cache is down.

The failure is logged once per transition rather than per request, because a
Redis outage during a busy clinic would otherwise write a line per queue poll
and bury everything else.

ENTRIES EXPIRE. A blocked id is held only until the token would have expired
anyway; after that the signature check refuses it for free. Holding ids for
ever would grow without bound on a box that also serves the queue.
"""

from __future__ import annotations

import threading
from datetime import UTC, datetime
from typing import Any

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

KEY_PREFIX = "kinyamed:blocked-jti:"

_client: Any | None = None
_client_resolved = False
_lock = threading.Lock()
_last_failure_logged = False


def reset_client() -> None:
    """Drop the cached connection. For tests, and for config changes."""
    global _client, _client_resolved, _last_failure_logged
    with _lock:
        _client = None
        _client_resolved = False
        _last_failure_logged = False


def get_client() -> Any | None:
    """A connected Redis client, or None if it cannot be reached.

    Resolved once and cached, including the negative result: retrying a dead
    connection on every request would add its timeout to every response.
    `reset_client` is how a process picks up a recovered Redis, and readiness
    reports the current state so an operator can see it is degraded.
    """
    global _client, _client_resolved
    if _client_resolved:
        return _client

    with _lock:
        if _client_resolved:
            return _client
        _client_resolved = True
        if not settings.BLOCKLIST_ENABLED:
            _client = None
            return None
        try:
            import redis

            candidate = redis.Redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=settings.REDIS_TIMEOUT_SECONDS,
                socket_timeout=settings.REDIS_TIMEOUT_SECONDS,
                decode_responses=True,
            )
            candidate.ping()
            _client = candidate
        except Exception as error:  # noqa: BLE001 - any failure means "no cache"
            _degraded("connect", error)
            _client = None
        return _client


def _degraded(operation: str, error: Exception) -> None:
    """Log the first failure of a run, not one per request."""
    global _last_failure_logged
    if _last_failure_logged:
        return
    _last_failure_logged = True
    logger.warning(
        "token_blocklist_unavailable",
        operation=operation,
        error=type(error).__name__,
        effect=(
            "access tokens stay valid until they expire; refresh revocation is "
            "unaffected because it lives in the database"
        ),
    )


def block(jti: str, expires_at: datetime) -> bool:
    """Withdraw one access token. True if it was recorded.

    False means Redis was unavailable, which the caller treats as a degraded
    logout rather than a failed one: the refresh token is revoked either way.
    """
    client = get_client()
    if client is None:
        return False
    ttl = int((expires_at - datetime.now(UTC)).total_seconds())
    if ttl <= 0:
        # Already expired; the signature check refuses it without our help.
        return True
    try:
        client.setex(f"{KEY_PREFIX}{jti}", ttl, "1")
        return True
    except Exception as error:  # noqa: BLE001
        _degraded("block", error)
        return False


def is_blocked(jti: str) -> bool:
    """Whether this token was withdrawn.

    Returns False when Redis is unavailable. That is the degradation, stated
    honestly: an unreachable blocklist cannot refuse anything, and refusing
    every request instead would turn a cache outage into an outage.
    """
    client = get_client()
    if client is None:
        return False
    try:
        return bool(client.exists(f"{KEY_PREFIX}{jti}"))
    except Exception as error:  # noqa: BLE001
        _degraded("is_blocked", error)
        return False


def status() -> str:
    """'ok', 'degraded' or 'disabled', for readiness."""
    if not settings.BLOCKLIST_ENABLED:
        return "disabled"
    return "ok" if get_client() is not None else "degraded"
