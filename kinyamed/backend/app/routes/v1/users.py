"""Account administration. Administrators only."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.audit_context import AuditCtx
from app.core.database import get_db
from app.core.dependencies import AdminUser
from app.core.exceptions import NotFoundError
from app.repositories import user_repository
from app.schemas.auth import UserCreate, UserResponse
from app.schemas.common import PaginatedResponse, PaginationParams, pagination
from app.services import auth_service
from app.services.audit import record, snapshot

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    admin: AdminUser,
    audit: AuditCtx,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Create a clinician or administrator account."""
    return UserResponse.model_validate(
        auth_service.create_user(db, data, audit=audit.acting_as(admin))
    )


@router.get("", response_model=PaginatedResponse[UserResponse])
def list_users(
    _admin: AdminUser,
    db: Session = Depends(get_db),
    page: PaginationParams = Depends(pagination),
) -> PaginatedResponse[UserResponse]:
    """List accounts, newest first."""
    users, total = user_repository.list_users(db, skip=page.offset, limit=page.limit)
    return PaginatedResponse[UserResponse].build(
        [UserResponse.model_validate(user) for user in users], total=total, params=page
    )


@router.patch("/{user_id}/deactivate", response_model=UserResponse)
def deactivate_user(
    user_id: int,
    admin: AdminUser,
    audit: AuditCtx,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Disable an account and end all of its sessions.

    Deactivation rather than deletion: the account may own clinical history,
    and an audit trail of who did what must survive.
    """
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise NotFoundError("User", user_id)
    before = snapshot(user)
    user_repository.update(db, user, commit=False, is_active=False)
    auth_service.logout_everywhere(db, user)
    record(
        db,
        action="DEACTIVATE_USER",
        table_name="users",
        record_id=user_id,
        before=before,
        after=snapshot(user),
        actor=admin,
        ip_address=audit.ip_address,
        user_agent=audit.user_agent,
    )
    db.commit()
    return UserResponse.model_validate(user)


@router.patch("/{user_id}/activate", response_model=UserResponse)
def activate_user(
    user_id: int,
    admin: AdminUser,
    audit: AuditCtx,
    db: Session = Depends(get_db),
) -> UserResponse:
    """Re-enable a disabled account."""
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise NotFoundError("User", user_id)
    before = snapshot(user)
    user_repository.update(db, user, commit=False, is_active=True)
    record(
        db,
        action="ACTIVATE_USER",
        table_name="users",
        record_id=user_id,
        before=before,
        after=snapshot(user),
        actor=admin,
        ip_address=audit.ip_address,
        user_agent=audit.user_agent,
    )
    db.commit()
    return UserResponse.model_validate(user)
