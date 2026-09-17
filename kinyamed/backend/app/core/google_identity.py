"""Verifying a Google ID token (FR-05-03).

A Google ID token is a JWT: anyone can read it and anyone can write one. The
only thing that makes it evidence is the signature, checked against Google's
published keys, together with the claims that say who it was issued FOR and BY.
An implementation that decodes the token and trusts the `email` inside will
authenticate whoever can type JSON, and from the outside it looks identical to
a correct one, because both log the user in.

FOUR CHECKS, none of them optional:

  * SIGNATURE, against the key named by the token's `kid` in Google's JWKS.
  * `aud` must equal our client id. Without it, a real Google token issued to
    ANY other application is accepted here -- and those are not hard to obtain.
  * `iss` must be Google.
  * `exp` must be in the future, which PyJWT enforces once verification is on.

THE ALGORITHM IS PINNED AND NEVER READ FROM THE TOKEN. `algorithms=` lists only
RS256; the header's `alg` is not consulted. Trusting it allows the confusion
attack the RS256 work already closed in this codebase: an attacker HMAC-signs
using the public key, which is not secret, and a header-trusting verifier
checks that MAC with the same public key and admits the token.

`email_verified` is required as well. Linking an account on an unverified
address would let anyone who can create a Google account with somebody else's
address claim that person's record.

CACHING. The key set is fetched at most once an hour. Fetching per sign-in
would be rude to Google, slow for the user, and would put their rate limit on
our critical path. A miss on an unknown `kid` refreshes once, because that is
what a legitimate key rotation looks like.
"""

from __future__ import annotations

import json
import threading
import time
import urllib.request
from dataclasses import dataclass
from typing import Any

import jwt
import structlog
from cryptography.hazmat.primitives import serialization

from app.core.config import settings

logger = structlog.get_logger(__name__)

JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
JWKS_TTL_SECONDS = 3600
ISSUERS = frozenset({"https://accounts.google.com", "accounts.google.com"})
ALGORITHM = "RS256"
FETCH_TIMEOUT_SECONDS = 5.0


class GoogleIdentityError(Exception):
    """The token is not acceptable evidence of who the caller is."""


class GoogleUnavailableError(Exception):
    """Google's key set could not be reached, so nothing can be verified."""


@dataclass(frozen=True)
class GoogleIdentity:
    """The claims we act on, extracted and typed."""

    subject: str
    email: str
    first_name: str
    last_name: str | None
    picture: str | None


_keys: dict[str, str] = {}
_fetched_at: float = 0.0
_lock = threading.Lock()


def reset_cache() -> None:
    """Forget the cached key set. For tests and for a forced refresh."""
    global _keys, _fetched_at
    with _lock:
        _keys = {}
        _fetched_at = 0.0


def _fetch_jwks() -> dict[str, str]:
    """kid -> PEM, from Google. Replaced wholesale in tests."""
    request = urllib.request.Request(JWKS_URL, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
        document = json.loads(response.read())
    keys: dict[str, str] = {}
    for entry in document.get("keys", []):
        kid = entry.get("kid")
        if not kid:
            continue
        public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(entry))
        keys[kid] = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")
    return keys


def _key_set(*, force: bool = False) -> dict[str, str]:
    global _keys, _fetched_at
    with _lock:
        fresh = _keys and (time.monotonic() - _fetched_at) < JWKS_TTL_SECONDS
        if fresh and not force:
            return _keys
    try:
        fetched = _fetch_jwks()
    except Exception as error:
        logger.warning(
            "google_jwks_unavailable",
            error=type(error).__name__,
            effect="Google sign-in is unavailable; password sign-in is unaffected",
        )
        raise GoogleUnavailableError(str(error)) from error
    with _lock:
        _keys = fetched
        _fetched_at = time.monotonic()
        return _keys


def verify(id_token: str) -> GoogleIdentity:
    """Verify a Google ID token, or raise. Never returns unverified claims."""
    client_id = settings.GOOGLE_CLIENT_ID
    if not client_id:
        # Without an audience to check against, "verification" would confirm
        # only that Google signed something for somebody.
        raise GoogleUnavailableError("GOOGLE_CLIENT_ID is not configured")

    try:
        header = jwt.get_unverified_header(id_token)
    except jwt.InvalidTokenError as error:
        raise GoogleIdentityError("Malformed token") from error

    kid = str(header.get("kid", ""))
    keys = _key_set()
    if kid not in keys:
        # A key we have not seen is what a rotation looks like; refresh once
        # before concluding the token is bad.
        keys = _key_set(force=True)
    public_pem = keys.get(kid)
    if public_pem is None:
        raise GoogleIdentityError("Token names a key Google does not publish")

    try:
        claims: dict[str, Any] = jwt.decode(
            id_token,
            public_pem,
            # Pinned. The header's `alg` is never consulted.
            algorithms=[ALGORITHM],
            audience=client_id,
            options={"require": ["exp", "iat", "aud", "iss", "sub"]},
        )
    except jwt.InvalidTokenError as error:
        raise GoogleIdentityError(str(error)) from error

    if claims.get("iss") not in ISSUERS:
        raise GoogleIdentityError("Token was not issued by Google")
    if not claims.get("email"):
        raise GoogleIdentityError("Token carries no email")
    if claims.get("email_verified") is not True:
        raise GoogleIdentityError("Google has not verified that address")

    return GoogleIdentity(
        subject=str(claims["sub"]),
        email=str(claims["email"]).strip().lower(),
        first_name=str(claims.get("given_name") or claims["email"].split("@")[0]),
        last_name=(str(claims["family_name"]) if claims.get("family_name") else None),
        picture=(str(claims["picture"]) if claims.get("picture") else None),
    )
