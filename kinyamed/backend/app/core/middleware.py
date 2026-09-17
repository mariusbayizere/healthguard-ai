"""HTTP middleware: request correlation, timing and rate limiting."""

from __future__ import annotations

import ipaddress
import time
import uuid
from collections import defaultdict, deque
from threading import Lock

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.exceptions import RateLimitExceededError, error_response

logger = structlog.get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Bind a request id to the log context and record request timing.

    Every log line emitted while handling a request carries the same
    `request_id`, which is what makes a production incident traceable across
    services.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            logger.exception("request_failed", duration_ms=duration_ms)
            raise

        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers["X-Response-Time-ms"] = str(duration_ms)
        logger.info(
            "request_completed",
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response


def _is_trusted_proxy(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address)
    except ValueError:
        return False
    return any(ip in network for network in settings.trusted_proxy_networks)


def client_ip(request: Request) -> str:
    """The address a request should be attributed to.

    X-Forwarded-For is written by whoever sends the request, so it is believed
    only when the TCP peer is a configured trusted proxy. A proxy APPENDS the
    address it received the connection from, so the client is the right-most
    entry that is not itself a trusted proxy; anything to its left was supplied
    by the client and is ignored. With no trusted proxy configured, the header
    is ignored entirely.
    """
    peer = request.client.host if request.client else "unknown"
    forwarded = request.headers.get("X-Forwarded-For")
    if not forwarded or not _is_trusted_proxy(peer):
        return peer
    hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
    for hop in reversed(hops):
        if not _is_trusted_proxy(hop):
            return hop
    return hops[0] if hops else peer


# Buckets live at module scope rather than on the middleware instance so that a
# test which rebuilds the app does not silently get a fresh, empty limiter --
# and so `reset_rate_limit_state` can clear them between cases.
_HITS: dict[str, deque[float]] = defaultdict(deque)
_HITS_LOCK = Lock()


def reset_rate_limit_state() -> None:
    """Forget every counted request. For tests and for nothing else."""
    with _HITS_LOCK:
        _HITS.clear()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-capacity sliding-window rate limiter, keyed by client IP.

    TWO BUDGETS, not one. Authentication endpoints are the brute-force surface
    and get FR-05-09's ten-per-fifteen-minutes; everything else keeps the
    general allowance. They are counted separately in both directions: ordinary
    traffic cannot exhaust the login budget, and an exhausted login budget does
    not lock a clinician out of the queue.

    State is per-process and in-memory: with several uvicorn workers the
    effective limit is `RATE_LIMIT_REQUESTS * workers`. That is an accepted
    trade-off for a single-node deployment; a multi-node deployment must move
    this counter to Redis, which is why the limit is configuration, not a
    constant.

    OPERATIONAL NOTE. The key is an IP, as the requirement states. Every client
    behind one NAT shares a budget, so a clinic whose staff share a public
    address shares ten attempts per fifteen minutes between all of them. That is
    tolerable for the brute-force threat this addresses and intolerable at shift
    change; when it bites, the fix is a per-account counter alongside this one,
    not a larger number here.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    def _policy(self, request: Request) -> tuple[str, int, int]:
        """(bucket prefix, limit, window) for this request."""
        if request.url.path in settings.auth_rate_limit_paths:
            return (
                "auth",
                settings.AUTH_RATE_LIMIT_REQUESTS,
                settings.AUTH_RATE_LIMIT_WINDOW_SECONDS,
            )
        return "all", settings.RATE_LIMIT_REQUESTS, settings.RATE_LIMIT_WINDOW_SECONDS

    def _client_key(self, request: Request) -> str:
        return client_ip(request)

    def _is_allowed(self, key: str, limit: int, window: int) -> bool:
        now = time.monotonic()
        with _HITS_LOCK:
            hits = _HITS[key]
            while hits and now - hits[0] > window:
                hits.popleft()
            if len(hits) >= limit:
                return False
            hits.append(now)
            return True

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if (
            not settings.RATE_LIMIT_ENABLED
            or request.url.path in settings.rate_limit_exempt_paths
        ):
            return await call_next(request)

        bucket, limit, window = self._policy(request)
        key = f"{bucket}:{self._client_key(request)}"
        if not self._is_allowed(key, limit, window):
            error = RateLimitExceededError(limit, window)
            logger.warning("rate_limit_exceeded", client=key, bucket=bucket)
            response = error_response(
                error.status_code, error.message, error.code, error.details
            )
            # The window of the budget that was actually exhausted, not the
            # general one: a Retry-After that under-reports invites an
            # immediate retry that is refused again.
            response.headers["Retry-After"] = str(window)
            return response

        return await call_next(request)


def register_middleware(app: FastAPI) -> None:
    """Install middleware. Order matters: the last added runs first."""
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER, "X-Response-Time-ms", "Retry-After"],
    )
