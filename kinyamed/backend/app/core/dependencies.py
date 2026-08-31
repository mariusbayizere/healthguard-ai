"""Authentication and authorisation dependencies.

`get_current_user` identifies the caller; `require_roles` authorises them.
Routes declare their policy in the signature, so what an endpoint requires is
visible in the endpoint itself and in the generated OpenAPI document.
"""

from __future__ import annotations

from typing import Annotated, Callable

import structlog
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import (
    ForbiddenError,
    InactiveUserError,
    InsufficientRoleError,
    InvalidTokenError,
)
from app.core.security import ACCESS_TOKEN, TokenError, decode_token
from app.models.user import User, UserRole
from app.repositories import user_repository

logger = structlog.get_logger(__name__)

# auto_error=False so a missing header raises our own typed error with the
# shared envelope, rather than FastAPI's bare {"detail": "Not authenticated"}.
bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Session = Depends(get_db),
) -> User:
    """Resolve the caller from their access token, or raise 401."""
    if credentials is None or not credentials.credentials:
        raise InvalidTokenError("Authorization header is missing")

    try:
        claims = decode_token(credentials.credentials, expected_type=ACCESS_TOKEN)
    except TokenError as exc:
        raise InvalidTokenError(str(exc)) from exc

    user = user_repository.get_by_id(db, claims.subject)
    if user is None:
        # The account was deleted while the token was still inside its window.
        raise InvalidTokenError("Account no longer exists")
    if not user.is_active:
        raise InactiveUserError()

    structlog.contextvars.bind_contextvars(user_id=user.id, role=user.role.value)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """Build a dependency admitting only the given roles.

    Usage:
        @router.get("", dependencies=[Depends(require_roles(UserRole.ADMIN))])
        def endpoint(...): ...
    """
    allowed = frozenset(roles)

    def dependency(user: CurrentUser) -> User:
        if user.role not in allowed:
            logger.info(
                "authorisation_denied",
                user_id=user.id,
                role=user.role.value,
                required=[role.value for role in allowed],
            )
            raise InsufficientRoleError(
                required=sorted(role.value for role in allowed), actual=user.role.value
            )
        return user

    return dependency


# Named policies, so a route reads as its intent rather than a role list.
require_admin = require_roles(UserRole.ADMIN)
require_clinical_staff = require_roles(UserRole.DOCTOR, UserRole.ADMIN)
require_any_role = require_roles(UserRole.PATIENT, UserRole.DOCTOR, UserRole.ADMIN)

AdminUser = Annotated[User, Depends(require_admin)]
StaffUser = Annotated[User, Depends(require_clinical_staff)]
AuthenticatedUser = Annotated[User, Depends(require_any_role)]


def assert_may_act_for_patient(user: User, patient_id: int) -> None:
    """Authorise a caller to act on a specific patient's record.

    Staff act for anyone. A patient acts only for themselves — without this
    check, any logged-in patient could submit symptoms as, or read the triage
    of, any other patient by changing an id.
    """
    if user.role in (UserRole.DOCTOR, UserRole.ADMIN):
        return
    if user.patient_id != patient_id:
        logger.info(
            "patient_scope_denied", user_id=user.id, requested_patient_id=patient_id
        )
        raise ForbiddenError(
            "You may only act on your own patient record",
            code="PATIENT_SCOPE_VIOLATION",
        )


def get_client_user_agent(request: Request) -> str | None:
    """The caller's User-Agent, recorded against a session."""
    return request.headers.get("User-Agent")
