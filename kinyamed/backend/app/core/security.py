"""Password hashing and JWT issuing/verification.

This module is deliberately free of database and framework imports: it is pure
cryptographic plumbing, which makes it directly testable and keeps token policy
in one readable place.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Final, Literal

import bcrypt
import jwt
import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

TokenType = Literal["access", "refresh"]

ACCESS_TOKEN: Final[TokenType] = "access"
REFRESH_TOKEN: Final[TokenType] = "refresh"

# bcrypt truncates silently at 72 bytes; longer input is rejected rather than
# quietly ignored, so a 200-character passphrase is not reduced to its prefix.
BCRYPT_MAX_BYTES: Final[int] = 72


class TokenError(Exception):
    """A token could not be decoded, or is not the type that was expected."""


@dataclass(frozen=True)
class TokenClaims:
    """The claims this application relies on, extracted and typed."""

    subject: int
    role: str
    token_type: TokenType
    jti: str
    expires_at: datetime
    issued_at: datetime


def _now() -> datetime:
    return datetime.now(timezone.utc)


# ── Passwords ─────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """Return a bcrypt digest of `password`."""
    encoded = password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        raise ValueError(f"password must be at most {BCRYPT_MAX_BYTES} bytes when encoded")
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """Whether `password` matches `hashed`, in constant time.

    Returns False rather than raising on a malformed digest so that a corrupted
    stored hash reads as a failed login, not a 500.
    """
    encoded = password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        return False
    try:
        return bcrypt.checkpw(encoded, hashed.encode("utf-8"))
    except (ValueError, TypeError):
        logger.warning("password_hash_malformed")
        return False


# ── Tokens ────────────────────────────────────────────────────────────────
def _create_token(
    *, subject: int, role: str, token_type: TokenType, lifetime: timedelta
) -> tuple[str, TokenClaims]:
    issued_at = _now()
    expires_at = issued_at + lifetime
    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": str(subject),  # RFC 7519 requires a string subject
        "role": role,
        "type": token_type,
        "jti": jti,
        "iat": issued_at,
        "exp": expires_at,
    }
    token = jwt.encode(
        payload,
        settings.SECRET_KEY.get_secret_value(),
        algorithm=settings.JWT_ALGORITHM,
    )
    claims = TokenClaims(
        subject=subject,
        role=role,
        token_type=token_type,
        jti=jti,
        expires_at=expires_at,
        issued_at=issued_at,
    )
    return token, claims


def create_access_token(*, subject: int, role: str) -> tuple[str, TokenClaims]:
    """Issue a short-lived access token."""
    return _create_token(
        subject=subject,
        role=role,
        token_type=ACCESS_TOKEN,
        lifetime=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(*, subject: int, role: str) -> tuple[str, TokenClaims]:
    """Issue a long-lived refresh token. The caller must record its `jti`."""
    return _create_token(
        subject=subject,
        role=role,
        token_type=REFRESH_TOKEN,
        lifetime=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


def decode_token(token: str, *, expected_type: TokenType) -> TokenClaims:
    """Decode and validate a token, or raise `TokenError`.

    The token type is part of validation: an access token must never be
    accepted where a refresh token is required, or the 15-minute lifetime is
    meaningless.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY.get_secret_value(),
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub", "jti"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Token is invalid") from exc

    token_type = payload.get("type")
    if token_type != expected_type:
        raise TokenError(f"Expected a {expected_type} token, got {token_type!r}")

    try:
        subject = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise TokenError("Token subject is not a user id") from exc

    return TokenClaims(
        subject=subject,
        role=payload.get("role", ""),
        token_type=token_type,
        jti=payload["jti"],
        expires_at=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        issued_at=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
    )
