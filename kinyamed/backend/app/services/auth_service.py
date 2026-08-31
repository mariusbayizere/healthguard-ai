"""Authentication business rules.

Session model: a short-lived access token carried in the `Authorization`
header, and a long-lived refresh token held in an httpOnly cookie and recorded
in the database so it can be revoked.

Refresh tokens rotate on every use. Presenting a token that has already been
rotated away means the token was captured, so every session for that user is
ended rather than just refusing the one request.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

import structlog
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    RefreshTokenReusedError,
)
from app.core.security import (
    ACCESS_TOKEN,
    REFRESH_TOKEN,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.user import RefreshToken, User, UserRole
from app.repositories import (
    patient_repository,
    refresh_token_repository,
    user_repository,
)
from app.schemas.auth import RegisterRequest, UserCreate
from app.schemas.patient import normalise_phone

logger = structlog.get_logger(__name__)


class IssuedSession:
    """The pair of tokens handed back after a successful login or refresh."""

    __slots__ = ("access_token", "refresh_token", "expires_in", "user")

    def __init__(self, access_token: str, refresh_token: str, expires_in: int, user: User) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in
        self.user = user


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _issue_session(
    db: Session, user: User, *, user_agent: str | None, commit: bool = True
) -> IssuedSession:
    """Mint an access/refresh pair and record the refresh token."""
    access_token, _ = create_access_token(subject=user.id, role=user.role.value)
    refresh_token, refresh_claims = create_refresh_token(subject=user.id, role=user.role.value)

    refresh_token_repository.create(
        db,
        commit=False,
        jti=refresh_claims.jti,
        user_id=user.id,
        expires_at=refresh_claims.expires_at,
        user_agent=(user_agent or "")[:255] or None,
    )
    if commit:
        db.commit()

    return IssuedSession(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=user,
    )


def register_patient(db: Session, data: RegisterRequest, *, user_agent: str | None) -> IssuedSession:
    """Create a patient login together with their clinical record."""
    if user_repository.email_taken(db, data.email):
        raise EmailAlreadyRegisteredError(data.email)

    patient = patient_repository.create(
        db,
        commit=False,
        name=data.full_name,
        phone=normalise_phone(data.phone),
        age=data.age,
        gender=data.gender,
        location=data.location,
    )
    user = user_repository.create(
        db,
        commit=False,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=UserRole.PATIENT,
        patient_id=patient.id,
    )
    session = _issue_session(db, user, user_agent=user_agent)
    logger.info("patient_registered_account", user_id=user.id, patient_id=patient.id)
    return session


def create_user(db: Session, data: UserCreate) -> User:
    """Create a staff or administrator account. Administrators only."""
    if user_repository.email_taken(db, data.email):
        raise EmailAlreadyRegisteredError(data.email)
    user = user_repository.create(
        db,
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        role=data.role,
        doctor_id=data.doctor_id if data.role is UserRole.DOCTOR else None,
        patient_id=data.patient_id if data.role is UserRole.PATIENT else None,
    )
    logger.info("user_created", user_id=user.id, role=user.role.value)
    return user


def authenticate(
    db: Session, *, email: str, password: str, user_agent: str | None
) -> IssuedSession:
    """Verify credentials and start a session."""
    user = user_repository.get_by_email(db, email)
    if user is None:
        # Hash anyway so that a missing account and a wrong password take the
        # same time; otherwise response timing reveals which emails exist.
        verify_password(password, "$2b$12$" + "." * 53)
        logger.info("login_failed", reason="unknown_email")
        raise InvalidCredentialsError()

    if not verify_password(password, user.hashed_password):
        logger.info("login_failed", reason="bad_password", user_id=user.id)
        raise InvalidCredentialsError()

    if not user.is_active:
        logger.info("login_failed", reason="inactive", user_id=user.id)
        raise InactiveUserError()

    user_repository.update(db, user, commit=False, last_login_at=_now())
    session = _issue_session(db, user, user_agent=user_agent)
    logger.info("login_succeeded", user_id=user.id, role=user.role.value)
    return session


def refresh_session(db: Session, token: str, *, user_agent: str | None) -> IssuedSession:
    """Rotate a refresh token, detecting reuse of one already rotated away."""
    try:
        claims = decode_token(token, expected_type=REFRESH_TOKEN)
    except TokenError as exc:
        raise InvalidTokenError(str(exc)) from exc

    record = refresh_token_repository.get_by_jti(db, claims.jti)
    if record is None:
        raise InvalidTokenError("Refresh token is not recognised")

    if record.is_revoked:
        # This token was already exchanged. Either it leaked, or a client is
        # replaying it; either way every session for the user is now suspect.
        revoked = refresh_token_repository.revoke_all_for_user(db, record.user_id)
        logger.warning(
            "refresh_token_reuse_detected", user_id=record.user_id, sessions_ended=revoked
        )
        raise RefreshTokenReusedError()

    if record.expires_at <= _now():
        raise InvalidTokenError("Refresh token has expired")

    user = user_repository.get_by_id(db, record.user_id)
    if user is None:
        raise InvalidTokenError("Refresh token is not recognised")
    if not user.is_active:
        raise InactiveUserError()

    refresh_token_repository.revoke(db, record, commit=False)
    session = _issue_session(db, user, user_agent=user_agent)
    logger.info("session_refreshed", user_id=user.id)
    return session


def logout(db: Session, token: str | None) -> None:
    """End the session the refresh token belongs to.

    Never raises on an unrecognised token: logging out is always allowed to
    succeed, so a client can clear its state unconditionally.
    """
    if not token:
        return
    try:
        claims = decode_token(token, expected_type=REFRESH_TOKEN)
    except TokenError:
        return
    record = refresh_token_repository.get_by_jti(db, claims.jti)
    if record is not None and not record.is_revoked:
        refresh_token_repository.revoke(db, record)
        logger.info("logout", user_id=record.user_id)


def logout_everywhere(db: Session, user: User) -> int:
    """End every session for a user. Returns how many were ended."""
    ended = refresh_token_repository.revoke_all_for_user(db, user.id)
    logger.info("logout_all_sessions", user_id=user.id, sessions_ended=ended)
    return ended


def list_sessions(db: Session, user: User) -> Sequence[RefreshToken]:
    """Active sessions for a user."""
    return refresh_token_repository.active_for_user(db, user.id)


def change_password(
    db: Session, user: User, *, current_password: str, new_password: str
) -> None:
    """Change a password and end every other session.

    Ending other sessions is the point of a password change: if the old
    password leaked, the attacker's refresh token must stop working too.
    """
    if not verify_password(current_password, user.hashed_password):
        raise InvalidCredentialsError()
    user_repository.update(
        db, user, commit=False, hashed_password=hash_password(new_password)
    )
    refresh_token_repository.revoke_all_for_user(db, user.id, commit=False)
    db.commit()
    logger.info("password_changed", user_id=user.id)
