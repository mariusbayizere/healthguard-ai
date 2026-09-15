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


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-capacity sliding-window rate limiter, keyed by client IP.

    State is per-process and in-memory: with several uvicorn workers the
    effective limit is `RATE_LIMIT_REQUESTS * workers`. That is an accepted
    trade-off for a single-node deployment; a multi-node deployment must move
    this counter to Redis, which is why the limit is configuration, not a
    constant.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def _client_key(self, request: Request) -> str:
        return client_ip(request)

    def _is_allowed(self, key: str) -> bool:
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        limit = settings.RATE_LIMIT_REQUESTS
        now = time.monotonic()
        with self._lock:
            hits = self._hits[key]
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

        key = self._client_key(request)
        if not self._is_allowed(key):
            error = RateLimitExceededError(
                settings.RATE_LIMIT_REQUESTS, settings.RATE_LIMIT_WINDOW_SECONDS
            )
            logger.warning("rate_limit_exceeded", client=key)
            response = error_response(
                error.status_code, error.message, error.code, error.details
            )
            response.headers["Retry-After"] = str(settings.RATE_LIMIT_WINDOW_SECONDS)
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
