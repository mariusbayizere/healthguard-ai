"""Liveness and readiness probes.

`/health` answers "is this process up?" and `/ready` answers "can it serve
traffic?" — the distinction Kubernetes needs to tell a restart from a
temporary removal from the load balancer.
"""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Response, status
from sqlalchemy import text

from app.core import alert_stream, token_blocklist
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


def _model_loaded() -> bool:
    """Whether the trained model is loaded. Never loads it, never raises."""
    from app.services import triage_service

    return triage_service.get_classifier() is not None


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness: the process is running and can answer. Never touches the DB."""
    return HealthResponse(
        status="healthy",
        service=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )


@router.get("/health/ready", response_model=ReadinessResponse)
@router.get("/ready", response_model=ReadinessResponse, include_in_schema=False)
def ready(response: Response) -> ReadinessResponse:
    """Readiness, and whether automated triage is available.

    `status` gates on the database only. A missing model does NOT make the
    service unready: the queue and records still work, and the dashboards
    need the API reachable to show staff that triage is offline. `model`
    reports it instead. `/ready` is kept as an alias for existing probes.
    """
    database = "ok" if _database_ok() else "unreachable"
    # Redis does NOT gate readiness. The blocklist degrading is a reduced
    # safety property, not an inability to serve; taking the pod out of
    # rotation for it would turn a cache outage into a triage outage. It is
    # reported so an operator can see the degradation instead of guessing.
    redis = token_blocklist.status()
    # Same rule as Redis: reported, never gating. Taking a pod out of rotation
    # for a transport outage would turn it into a triage outage.
    kafka = alert_stream.status()
    is_ready = database == "ok"

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status="ready" if is_ready else "not_ready",
        database=database,
        redis=redis,
        kafka=kafka,
        model=_model_loaded(),
    )
