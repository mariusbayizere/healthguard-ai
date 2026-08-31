"""Structured logging configuration.

Logs are the only record of what the triage system decided for a patient, so
they are emitted as structured events with explicit fields: JSON in production
for ingestion, coloured console output in development for reading.
"""

from __future__ import annotations

import logging
import sys

import structlog

from app.core.config import settings


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
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Send uvicorn/sqlalchemy records through the same renderer so a deployment
    # emits one log format rather than two.
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=level, force=True)
    # SQL statements carry patient data; they are opt-in via DB_ECHO only.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
