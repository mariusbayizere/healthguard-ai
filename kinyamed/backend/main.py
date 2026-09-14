"""ASGI entrypoint for the KinyaMed API.

Wiring only: configuration, logging, middleware, exception handlers and
routers. No business logic lives in this file.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from app.core.config import settings
from app.core.database import engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import register_middleware
from app.routes import api_router, health_router
from app.schemas.common import ServiceInfoResponse
from fastapi import FastAPI

configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Start-up and shutdown.

    The schema is not created here: it is owned by Alembic (`alembic upgrade
    head`), so an application start can never invent a schema that differs from
    the migrated one.
    """
    logger.info(
        "application_starting",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )

    # C1. Load and WARM the model before the service reports ready. Measured on
    # the reference hardware, the first inference in a process costs 1341 ms
    # against a warm median of 66 ms, so it is paid at start-up, not by a patient.
    # A missing model does not stop the service: the queue and records stay
    # usable, and triage FAILS CLOSED with 503 until a model is loaded.
    from app.services import triage_service

    if triage_service.get_classifier() is None:
        logger.error(
            "triage_disabled",
            reason=triage_service.ACTIVE_CLASSIFIER_DESCRIPTION,
            effect="POST /triage returns 503; triage patients manually",
        )
    else:
        logger.info(
            "classifier_selected",
            classifier=triage_service.ACTIVE_CLASSIFIER_DESCRIPTION,
        )
    try:
        yield
    finally:
        engine.dispose()
        logger.info("application_stopped", service=settings.APP_NAME)


app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="AI-powered multilingual medical triage for Kinyarwanda speakers.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    # Interactive docs expose every endpoint; keep them off in production.
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
)

register_middleware(app)
register_exception_handlers(app)

# Probes stay unversioned at the root; orchestrators should not chase API versions.
app.include_router(health_router)
app.include_router(api_router, prefix=settings.API_PREFIX)


@app.get("/", tags=["Meta"], response_model=ServiceInfoResponse)
def root() -> ServiceInfoResponse:
    """Service identity."""
    return ServiceInfoResponse(
        status="ok",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        docs="/docs" if not settings.is_production else "disabled",
    )
