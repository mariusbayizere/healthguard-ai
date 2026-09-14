"""Structured logging configuration.

Logs are the only record of what the triage system decided for a patient, so
they are emitted as structured events with explicit fields: JSON in production
for ingestion, coloured console output in development for reading.
"""

from __future__ import annotations

import io
import logging
import sys
from typing import TextIO, cast

import structlog

from app.core.config import settings
from app.core.pii import PiiLogFilter, mask_pii_processor


class _CurrentStdout(io.TextIOBase):
    """Writes to whatever `sys.stdout` is at write time.

    Cached loggers otherwise keep the stream object they were created with, so
    a replaced stdout (a test capture, a supervisor) would miss their output.
    """

    def write(self, s: str) -> int:
        return sys.stdout.write(s)

    def flush(self) -> None:
        sys.stdout.flush()


# Loggers whose records never pass through the root logger's handlers (uvicorn
# installs its own), so the PII filter is attached to each by name.
_FILTERED_LOGGERS = ("", "uvicorn", "uvicorn.access", "uvicorn.error", "sqlalchemy")


def configure_logging(environment: str | None = None) -> None:
    """Configure structlog and route stdlib logging through it. Idempotent."""
    environment = environment or settings.ENVIRONMENT
    level = logging.getLevelNamesMapping()[settings.LOG_LEVEL]

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        # LAST before rendering, so exception text and bound context are
        # masked too. L11: no phone, email or name in any log line.
        mask_pii_processor,
    ]

    renderer = (
        structlog.processors.JSONRenderer()
        if environment == "production"
        else structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())
    )

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        # io.TextIOBase is the runtime contract PrintLogger uses (write/flush);
        # the cast is only because typeshed's TextIO is a distinct nominal type.
        logger_factory=structlog.PrintLoggerFactory(
            file=cast(TextIO, _CurrentStdout())
        ),
        cache_logger_on_first_use=True,
    )

    # Send uvicorn/sqlalchemy records through the same renderer so a deployment
    # emits one log format rather than two.
    logging.basicConfig(
        format="%(message)s", stream=_CurrentStdout(), level=level, force=True
    )
    # A logger's own filters do not see records propagated from its children
    # (httpx, sqlalchemy, any library), but its handlers do. So the filter goes
    # on the root handlers, and on uvicorn's loggers, which use their own.
    targets: list[logging.Filterer] = [*logging.getLogger().handlers]
    targets += [logging.getLogger(name) for name in _FILTERED_LOGGERS]
    for target in targets:
        if not any(isinstance(f, PiiLogFilter) for f in target.filters):
            target.addFilter(PiiLogFilter())
    # SQL statements carry patient data; they are opt-in via DB_ECHO only.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
