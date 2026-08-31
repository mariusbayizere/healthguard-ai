"""Version 1 of the HTTP API."""

from fastapi import APIRouter

from app.routes.v1.analytics import router as analytics_router
from app.routes.v1.auth import router as auth_router
from app.routes.v1.doctors import router as doctors_router
from app.routes.v1.health import router as health_router
from app.routes.v1.patients import router as patients_router
from app.routes.v1.queue import router as queue_router
from app.routes.v1.triage import router as triage_router
from app.routes.v1.users import router as users_router

# Mounted under settings.API_PREFIX by main.py.
api_router = APIRouter()
for _router in (
    auth_router,
    users_router,
    patients_router,
    triage_router,
    queue_router,
    doctors_router,
    analytics_router,
):
    api_router.include_router(_router)

__all__ = [
    "analytics_router",
    "auth_router",
    "api_router",
    "doctors_router",
    "health_router",
    "patients_router",
    "queue_router",
    "triage_router",
    "users_router",
]
