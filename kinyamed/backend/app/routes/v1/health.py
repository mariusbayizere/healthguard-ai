"""Liveness and readiness probes.

`/health` answers "is this process up?" and `/ready` answers "can it serve
traffic?" — the distinction Kubernetes needs to tell a restart from a
temporary removal from the load balancer.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.schemas.common import HealthResponse, ReadinessResponse

logger = structlog.get_logger(__name__)

router = APIRouter(tags=["Meta"])


def _database_ok() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001 - a probe reports, it never raises
        logger.error("health_check_database_unreachable")
        return False


def _model_status() -> str:
    """Report ML model readiness without importing torch when it is absent."""
    try:
        from app.ml.model_loader import ModelLoader
    except ImportError:
        return "not_installed"
    return "loaded" if ModelLoader().is_ready else "not_loaded"


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness: the process is running and can answer. Never touches the DB."""
    return HealthResponse(
        status="healthy",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )


@router.get("/ready", response_model=ReadinessResponse)
def ready(response: Response) -> ReadinessResponse:
    """Readiness: every dependency needed to serve a request is available."""
    database = "ok" if _database_ok() else "unreachable"
    model = _model_status()
    is_ready = database == "ok"

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        database=database,
        ml_model=model,
    )
