"""Authentication endpoints.

The refresh token is delivered as an httpOnly cookie and never appears in a
response body, so page JavaScript cannot read it. The access token is returned
in the body for the client to hold in memory and send as a bearer header.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import AuthenticatedUser, CurrentUser, get_client_user_agent
from app.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    RegisterRequest,
    SessionResponse,
    TokenResponse,
    UserResponse,
)
from app.schemas.common import Message
from app.services import auth_service
from app.services.auth_service import IssuedSession

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Scoped to the refresh endpoints: the cookie is not attached to ordinary API
# calls, which keeps it out of reach of CSRF against the rest of the API.
REFRESH_COOKIE_PATH = f"{settings.API_PREFIX}/auth"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite=settings.REFRESH_COOKIE_SAMESITE,
        path=REFRESH_COOKIE_PATH,
    )


def _token_response(response: Response, session: IssuedSession) -> TokenResponse:
    _set_refresh_cookie(response, session.refresh_token)
    return TokenResponse(
        access_token=session.access_token,
        expires_in=session.expires_in,
        user=UserResponse.model_validate(session.user),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(
    data: RegisterRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Register a patient account and sign them in.

    Only patient accounts can be self-registered; clinician and administrator
    accounts are created by an administrator.
    """
    session = auth_service.register_patient(
        db, data, user_agent=get_client_user_agent(request)
    )
    return _token_response(response, session)


@router.post("/login", response_model=TokenResponse)
def login(
    data: LoginRequest,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """Exchange credentials for an access token and a refresh cookie."""
    session = auth_service.authenticate(
        db,
        email=data.email,
        password=data.password,
        user_agent=get_client_user_agent(request),
    )
    return _token_response(response, session)


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    refresh_token: Annotated[str | None, Cookie(alias=settings.REFRESH_COOKIE_NAME)] = None,
) -> TokenResponse:
    """Rotate the refresh cookie and issue a fresh access token.

    Every refresh invalidates the token it was called with. Presenting a token
    twice ends all of that user's sessions, on the assumption it was stolen.
    """
    session = auth_service.refresh_session(
        db, refresh_token or "", user_agent=get_client_user_agent(request)
    )
    return _token_response(response, session)


@router.post("/logout", response_model=Message)
def logout(
    response: Response,
    db: Session = Depends(get_db),
    refresh_token: Annotated[str | None, Cookie(alias=settings.REFRESH_COOKIE_NAME)] = None,
) -> Message:
    """End the current session and clear the refresh cookie.

    Succeeds even without a valid cookie, so a client can always clear state.
    """
    auth_service.logout(db, refresh_token)
    _clear_refresh_cookie(response)
    return Message(message="Signed out")


@router.post("/logout-all", response_model=Message)
def logout_all(
    user: AuthenticatedUser, response: Response, db: Session = Depends(get_db)
) -> Message:
    """End every session for the current account, on every device."""
    ended = auth_service.logout_everywhere(db, user)
    _clear_refresh_cookie(response)
    return Message(message=f"Ended {ended} session(s)")


@router.get("/me", response_model=UserResponse)
def read_current_user(user: CurrentUser) -> UserResponse:
    """The account behind the presented access token."""
    return UserResponse.model_validate(user)


@router.get("/sessions", response_model=list[SessionResponse])
def list_sessions(user: AuthenticatedUser, db: Session = Depends(get_db)) -> list[SessionResponse]:
    """Active sessions for the current account."""
    return [
        SessionResponse.model_validate(session)
        for session in auth_service.list_sessions(db, user)
    ]


@router.post("/change-password", response_model=Message)
def change_password(
    data: PasswordChangeRequest,
    user: AuthenticatedUser,
    response: Response,
    db: Session = Depends(get_db),
) -> Message:
    """Change the current account's password, ending all other sessions."""
    auth_service.change_password(
        db,
        user,
        current_password=data.current_password,
        new_password=data.new_password,
    )
    _clear_refresh_cookie(response)
    return Message(message="Password changed. Please sign in again.")
