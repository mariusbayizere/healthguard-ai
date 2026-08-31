"""Account administration. Administrators only."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import AdminUser
from app.core.exceptions import NotFoundError
from app.repositories import user_repository
from app.schemas.auth import UserCreate, UserResponse
from app.schemas.common import PaginatedResponse, PaginationParams, pagination
from app.services import auth_service

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(data: UserCreate, _admin: AdminUser, db: Session = Depends(get_db)) -> UserResponse:
    """Create a clinician or administrator account."""
    return UserResponse.model_validate(auth_service.create_user(db, data))


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
def deactivate_user(user_id: int, _admin: AdminUser, db: Session = Depends(get_db)) -> UserResponse:
    """Disable an account and end all of its sessions.

    Deactivation rather than deletion: the account may own clinical history,
    and an audit trail of who did what must survive.
    """
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise NotFoundError("User", user_id)
    user_repository.update(db, user, commit=False, is_active=False)
    auth_service.logout_everywhere(db, user)
    return UserResponse.model_validate(user)


@router.patch("/{user_id}/activate", response_model=UserResponse)
def activate_user(user_id: int, _admin: AdminUser, db: Session = Depends(get_db)) -> UserResponse:
    """Re-enable a disabled account."""
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise NotFoundError("User", user_id)
    user_repository.update(db, user, is_active=True)
    return UserResponse.model_validate(user)
