"""Authentication business rules.

Session model: a short-lived access token carried in the `Authorization`
header, and a long-lived refresh token held in an httpOnly cookie and recorded
in the database so it can be revoked.

Refresh tokens rotate on every use. Presenting a token that has already been
rotated away means the token was captured, so every session for that user is
ended rather than just refusing the one request.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime

import structlog
from sqlalchemy.orm import Session

from app.core.audit_context import AuditContext
from app.core.config import settings
from app.core.exceptions import (
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    RefreshTokenReusedError,
)
from app.core.google_identity import GoogleIdentity
from app.core.security import (
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
from app.services.audit import record as audit_record
from app.services.audit import snapshot

logger = structlog.get_logger(__name__)


class IssuedSession:
    """The pair of tokens handed back after a successful login or refresh."""

    __slots__ = ("access_token", "expires_in", "refresh_token", "user")

    def __init__(
        self, access_token: str, refresh_token: str, expires_in: int, user: User
    ) -> None:
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in
        self.user = user


def _now() -> datetime:
    return datetime.now(UTC)


def _token_digest(token: str) -> str:
    """SHA-256 of a refresh token.

    Not bcrypt: bcrypt truncates silently past 72 bytes and a JWT is longer, so
    it would hash a prefix. A refresh token is high-entropy and not guessable,
    so the slow-hash argument for passwords does not apply; the goal is that a
    read of refresh_tokens yields nothing usable.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _issue_session(
    db: Session,
    user: User,
    *,
    user_agent: str | None,
    commit: bool = True,
    family_id: str | None = None,
) -> IssuedSession:
    """Mint an access/refresh pair and record the refresh token.

    `family_id` is None for a new login, which starts its own lineage, and is
    the incoming token's family on rotation, which keeps the lineage intact.
    Getting this backwards would make reuse detection able to revoke only the
    newest token, which is the same as not having it.
    """
    access_token, _ = create_access_token(subject=user.id, role=user.role.value)
    refresh_token, refresh_claims = create_refresh_token(
        subject=user.id, role=user.role.value
    )

    refresh_token_repository.create(
        db,
        commit=False,
        jti=refresh_claims.jti,
        token_hash=_token_digest(refresh_token),
        user_id=user.id,
        family_id=family_id or str(uuid.uuid4()),
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


def register_patient(
    db: Session,
    data: RegisterRequest,
    *,
    user_agent: str | None,
    audit: AuditContext | None = None,
) -> IssuedSession:
    """Create a patient login together with their clinical record."""
    if user_repository.email_taken(db, data.email):
        raise EmailAlreadyRegisteredError(data.email)

    patient = patient_repository.create(
        db,
        commit=False,
        name=f"{data.first_name} {data.last_name}".strip(),
        # Already E.164: the schema normalised it, so a bad number was a 422
        # before any of this ran.
        phone=data.phone,
        age=data.age,
        gender=data.gender,
        location=data.location,
    )
    user = user_repository.create(
        db,
        commit=False,
        email=data.email,
        hashed_password=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        role=UserRole.PATIENT,
        patient_id=patient.id,
    )
    if audit is not None:
        audit_record(
            db,
            action="REGISTER_PATIENT",
            table_name="users",
            record_id=user.id,
            after={"user_id": user.id, "patient_id": patient.id, "role": user.role},
            actor=user,
            ip_address=audit.ip_address,
            user_agent=audit.user_agent,
        )
    session = _issue_session(db, user, user_agent=user_agent)
    logger.info("patient_registered_account", user_id=user.id, patient_id=patient.id)
    return session


def create_user(db: Session, data: UserCreate, *, audit: AuditContext) -> User:
    """Create a staff or administrator account. Administrators only."""
    if user_repository.email_taken(db, data.email):
        raise EmailAlreadyRegisteredError(data.email)
    user = user_repository.create(
        db,
        commit=False,
        email=data.email,
        hashed_password=hash_password(data.password),
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        role=data.role,
        doctor_id=data.doctor_id if data.role is UserRole.DOCTOR else None,
        patient_id=data.patient_id if data.role is UserRole.PATIENT else None,
    )
    audit_record(
        db,
        action="CREATE_USER",
        table_name="users",
        record_id=user.id,
        after=snapshot(user),
        actor=audit.actor,
        ip_address=audit.ip_address,
        user_agent=audit.user_agent,
    )
    db.commit()
    db.refresh(user)
    logger.info("user_created", user_id=user.id, role=user.role.value)
    return user


def sign_in_with_google(
    db: Session,
    identity: GoogleIdentity,
    *,
    user_agent: str | None,
    audit: AuditContext | None = None,
) -> IssuedSession:
    """Start a session for a verified Google identity (FR-05-04).

    LINKING IS BY VERIFIED EMAIL, and only verified: `google_identity.verify`
    refuses a token whose `email_verified` is not true, because linking on an
    unverified address would let anyone who can register that address with
    Google claim the matching account here.

    An existing password account gains the OAuth identity and KEEPS its
    password. Removing it would silently take away a sign-in method the person
    was using, and would strand them if they later unlinked Google.
    """
    user = user_repository.get_by_email(db, identity.email)

    if user is None:
        user = user_repository.create(
            db,
            commit=False,
            email=identity.email,
            # No password: the CHECK constraint is satisfied by oauth_provider.
            hashed_password=None,
            first_name=identity.first_name,
            last_name=identity.last_name,
            avatar_url=identity.picture,
            oauth_provider="google",
            oauth_id=identity.subject,
            role=UserRole.PATIENT,
        )
        action = "GOOGLE_SIGN_UP"
    else:
        if not user.is_active:
            raise InactiveUserError()
        if user.oauth_provider is None:
            user_repository.update(
                db,
                user,
                commit=False,
                oauth_provider="google",
                oauth_id=identity.subject,
                avatar_url=user.avatar_url or identity.picture,
            )
            action = "LINK_GOOGLE_ACCOUNT"
        else:
            action = "GOOGLE_SIGN_IN"

    if not user.is_active:
        raise InactiveUserError()

    user_repository.update(db, user, commit=False, last_login_at=_now())
    if audit is not None:
        audit_record(
            db,
            action=action,
            table_name="users",
            record_id=user.id,
            after={"user_id": user.id, "oauth_provider": "google"},
            actor=user,
            ip_address=audit.ip_address,
            user_agent=audit.user_agent,
        )
    session = _issue_session(db, user, user_agent=user_agent)
    logger.info("google_sign_in", user_id=user.id, action=action)
    return session


def authenticate(
    db: Session,
    *,
    email: str,
    password: str,
    user_agent: str | None,
    audit: AuditContext | None = None,
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
    # A successful sign-in is a state change (last_login_at, a new session) and
    # the event an intrusion review starts from. Failures are logged but not
    # audited here: they change nothing, and an unauthenticated caller must not
    # be able to append rows to this table at will.
    if audit is not None:
        audit_record(
            db,
            action="LOGIN",
            table_name="users",
            record_id=user.id,
            after={"user_id": user.id, "role": user.role},
            actor=user,
            ip_address=audit.ip_address,
            user_agent=audit.user_agent,
        )
    session = _issue_session(db, user, user_agent=user_agent)
    logger.info("login_succeeded", user_id=user.id, role=user.role.value)
    return session


def refresh_session(
    db: Session,
    token: str,
    *,
    user_agent: str | None,
    audit: AuditContext | None = None,
) -> IssuedSession:
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
        # replaying it; either way this lineage is compromised.
        #
        # The family, not the user: ending every session would sign a clinician
        # out of the ward workstation and the laptop because the phone in their
        # pocket replayed a token. The blast radius is the compromised device.
        revoked = refresh_token_repository.revoke_family(db, record.family_id)
        logger.warning(
            "refresh_token_reuse_detected",
            user_id=record.user_id,
            family_id=record.family_id,
            sessions_ended=revoked,
        )
        raise RefreshTokenReusedError()

    if record.expires_at <= _now():
        raise InvalidTokenError("Refresh token has expired")

    # The jti identifies the row; the digest proves the presented token is the
    # one that row was issued for. A row written before the digest column
    # existed has None, which cannot confirm anything and so is refused rather
    # than waved through.
    if record.token_hash is None or not secrets.compare_digest(
        record.token_hash, _token_digest(token)
    ):
        raise InvalidTokenError("Refresh token is not recognised")

    user = user_repository.get_by_id(db, record.user_id)
    if user is None:
        raise InvalidTokenError("Refresh token is not recognised")
    if not user.is_active:
        raise InactiveUserError()

    refresh_token_repository.revoke(db, record, commit=False)
    family_id = record.family_id
    if audit is not None:
        audit_record(
            db,
            action="REFRESH_SESSION",
            table_name="refresh_tokens",
            record_id=record.id,
            after={"user_id": user.id},
            actor=user,
            ip_address=audit.ip_address,
            user_agent=audit.user_agent,
        )
    session = _issue_session(db, user, user_agent=user_agent, family_id=family_id)
    logger.info("session_refreshed", user_id=user.id, family_id=family_id)
    return session


def logout(
    db: Session, token: str | None, *, audit: AuditContext | None = None
) -> None:
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
        refresh_token_repository.revoke(db, record, commit=False)
        if audit is not None:
            audit_record(
                db,
                action="LOGOUT",
                table_name="refresh_tokens",
                record_id=record.id,
                before={"user_id": record.user_id, "revoked": False},
                after={"user_id": record.user_id, "revoked": True},
                actor=audit.actor,
                ip_address=audit.ip_address,
                user_agent=audit.user_agent,
            )
        db.commit()
        logger.info("logout", user_id=record.user_id)


def logout_everywhere(
    db: Session, user: User, *, audit: AuditContext | None = None
) -> int:
    """End every session for a user. Returns how many were ended.

    `audit` is None when deactivation calls this as one of its steps; that
    operation writes the single row describing what it did.
    """
    ended = refresh_token_repository.revoke_all_for_user(db, user.id)
    if audit is not None:
        audit_record(
            db,
            action="LOGOUT_ALL",
            table_name="refresh_tokens",
            record_id=None,
            after={"user_id": user.id, "sessions_ended": ended},
            actor=audit.actor,
            ip_address=audit.ip_address,
            user_agent=audit.user_agent,
        )
        db.commit()
    logger.info("logout_all_sessions", user_id=user.id, sessions_ended=ended)
    return ended


def list_sessions(db: Session, user: User) -> Sequence[RefreshToken]:
    """Active sessions for a user."""
    return refresh_token_repository.active_for_user(db, user.id)


def change_password(
    db: Session,
    user: User,
    *,
    current_password: str,
    new_password: str,
    audit: AuditContext | None = None,
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
    # Neither password reaches the payload, old or new, hashed or not.
    if audit is not None:
        audit_record(
            db,
            action="CHANGE_PASSWORD",
            table_name="users",
            record_id=user.id,
            after={"user_id": user.id, "sessions_ended": True},
            actor=user,
            ip_address=audit.ip_address,
            user_agent=audit.user_agent,
        )
    db.commit()
    logger.info("password_changed", user_id=user.id)
