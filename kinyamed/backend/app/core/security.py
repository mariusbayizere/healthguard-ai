"""Password hashing and JWT issuing/verification.

This module is deliberately free of database and framework imports: it is pure
cryptographic plumbing, which makes it directly testable and keeps token policy
in one readable place.
"""

from __future__ import annotations

import re
import threading
import uuid
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Final, Literal

import bcrypt
import jwt
import structlog

from app.core.config import settings
from app.core.jwt_keys import (
    KeyPair,
    generate_key_pair,
    kid_for_public_pem,
    normalise_pem,
    public_pem_for_private_pem,
)

logger = structlog.get_logger(__name__)

# Re-exported so callers have one import for token policy and its key material.
__all__ = [
    "ACCESS_TOKEN",
    "REFRESH_TOKEN",
    "TokenClaims",
    "TokenError",
    "active_kid",
    "active_public_key_pem",
    "additional_verification_keys",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "generate_key_pair",
    "hash_password",
    "kid_for_public_pem",
    "using_ephemeral_key",
    "verification_kids",
    "verify_password",
]

_PEM_BLOCK = re.compile(
    r"-----BEGIN PUBLIC KEY-----.*?-----END PUBLIC KEY-----", re.DOTALL
)

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
    return datetime.now(UTC)


# ── Key material ──────────────────────────────────────────────────────────
#
# Resolved once at import. The signing key never changes within a process; a
# rotation is a deploy, which is what makes the retired-key window a bounded
# and observable thing rather than live mutable state.


def _load_signing_key() -> tuple[KeyPair, bool]:
    configured = settings.JWT_PRIVATE_KEY
    if configured is None:
        pair = generate_key_pair()
        logger.warning(
            "jwt_ephemeral_key_generated",
            kid=pair.kid,
            environment=settings.ENVIRONMENT,
            effect="every session ends when this process restarts",
            fix="set JWT_PRIVATE_KEY (python -m app.core.jwt_keys)",
        )
        return pair, True

    private_pem = normalise_pem(configured.get_secret_value())
    public_pem = public_pem_for_private_pem(private_pem)
    return (
        KeyPair(
            private_pem=private_pem,
            public_pem=public_pem,
            kid=kid_for_public_pem(public_pem),
        ),
        False,
    )


_SIGNING_KEY, _EPHEMERAL = _load_signing_key()

# kid -> public PEM. The active key plus any retired keys still inside a
# refresh-token lifetime.
_VERIFICATION_KEYS: dict[str, str] = {_SIGNING_KEY.kid: _SIGNING_KEY.public_pem}
for _block in _PEM_BLOCK.findall(settings.JWT_RETIRED_PUBLIC_KEYS or ""):
    _retired = normalise_pem(_block)
    _VERIFICATION_KEYS.setdefault(kid_for_public_pem(_retired), _retired)

_KEYS_LOCK = threading.Lock()


def active_kid() -> str:
    """The `kid` stamped on every token this process issues."""
    return _SIGNING_KEY.kid


def active_public_key_pem() -> str:
    """The public half of the signing key. Not a secret; publishable."""
    return _SIGNING_KEY.public_pem


def using_ephemeral_key() -> bool:
    """True when no key was configured and one was generated at start-up."""
    return _EPHEMERAL


def verification_kids() -> list[str]:
    """Every key id currently accepted, active first."""
    return [active_kid()] + [k for k in _VERIFICATION_KEYS if k != active_kid()]


@contextmanager
def additional_verification_keys(public_pems: Sequence[str]) -> Iterator[None]:
    """Temporarily accept extra public keys. For tests and rotation drills.

    Verification only: the signing key is untouched, so nothing minted inside
    this block is signed by a retired key.
    """
    added: list[str] = []
    with _KEYS_LOCK:
        for pem in public_pems:
            normalised = normalise_pem(pem)
            kid = kid_for_public_pem(normalised)
            if kid not in _VERIFICATION_KEYS:
                _VERIFICATION_KEYS[kid] = normalised
                added.append(kid)
    try:
        yield
    finally:
        with _KEYS_LOCK:
            for kid in added:
                _VERIFICATION_KEYS.pop(kid, None)


# ── Passwords ─────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """Return a bcrypt digest of `password`."""
    encoded = password.encode("utf-8")
    if len(encoded) > BCRYPT_MAX_BYTES:
        raise ValueError(
            f"password must be at most {BCRYPT_MAX_BYTES} bytes when encoded"
        )
    return bcrypt.hashpw(encoded, bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)).decode(
        "utf-8"
    )


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
        _SIGNING_KEY.private_pem,
        algorithm=settings.JWT_ALGORITHM,
        headers={"kid": _SIGNING_KEY.kid},
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
        # The key is chosen by the token's kid, but the ALGORITHM is pinned to
        # the configured one and never read from the header. Trusting the
        # header's `alg` is what lets an attacker present an HS256 MAC computed
        # with the public key and have it accepted as a signature.
        header = jwt.get_unverified_header(token)
        public_pem = _VERIFICATION_KEYS.get(str(header.get("kid", "")))
        if public_pem is None:
            raise TokenError("Token was signed by an unknown key")
        payload = jwt.decode(
            token,
            public_pem,
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
        expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
        issued_at=datetime.fromtimestamp(payload["iat"], tz=UTC),
    )
