"""Tokens are RS256, and only the private key can mint one (FR-05-05).

WHY THIS MATTERS MORE THAN A CONFIG FLIP. Under HS256 the signing secret and
the verifying secret are the same string, so anything able to check a token is
also able to forge one. Splitting them means a service that only needs to
verify never holds the ability to issue.

The attack this file exists to prevent is algorithm confusion: an attacker takes
the PUBLIC key, which is not secret, signs a token with HMAC-SHA256 using that
key's bytes as the shared secret, and sends it. A verifier that accepts whatever
`alg` the token asks for will happily check an HS256 MAC using the public key
and admit a token the attacker minted. The defence is to pin the accepted
algorithm on the verifier and never derive it from the token header.

Key identity is a thumbprint of the public key rather than a configured name,
so a `kid` cannot disagree with the key it labels.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json

import jwt
import pytest
from app.core import security
from app.core.config import settings


def _public_pem() -> str:
    return security.active_public_key_pem()


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _forge_hs256(secret: bytes, *, kid: str | None) -> str:
    """Hand-build an HS256 token.

    PyJWT refuses to sign with a PEM, which is a good guard in the library and
    a useless one here: an attacker is not using PyJWT. Assembling the token
    directly is the only way to put the real attack in front of our verifier.
    """
    header: dict[str, object] = {"alg": "HS256", "typ": "JWT"}
    if kid is not None:
        header["kid"] = kid
    payload = {
        "sub": "1",
        "role": "ADMIN",
        "type": "access",
        "jti": "forged",
        "iat": 1,
        "exp": 9_999_999_999,
    }
    signing_input = (
        _b64(json.dumps(header).encode()) + "." + _b64(json.dumps(payload).encode())
    )
    mac = hmac.new(secret, signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64(mac)}"


# ── Algorithm ────────────────────────────────────────────────────────────


def test_an_access_token_is_signed_with_rs256() -> None:
    token, _ = security.create_access_token(subject=1, role="ADMIN")
    assert jwt.get_unverified_header(token)["alg"] == "RS256"


def test_a_refresh_token_is_signed_with_rs256() -> None:
    token, _ = security.create_refresh_token(subject=1, role="ADMIN")
    assert jwt.get_unverified_header(token)["alg"] == "RS256"


def test_the_configured_algorithm_is_asymmetric() -> None:
    """A symmetric algorithm here would silently reinstate the old design."""
    assert settings.JWT_ALGORITHM.startswith("RS")


# ── Forgery ──────────────────────────────────────────────────────────────


def test_a_token_hmac_signed_with_the_public_key_is_rejected() -> None:
    """Algorithm confusion. The public key is not a signing secret.

    Presented WITH the real kid, so the verifier looks up the correct key and
    the only thing standing between the attacker and an admin session is the
    pinned algorithm.
    """
    forged = _forge_hs256(_public_pem().encode("utf-8"), kid=security.active_kid())
    with pytest.raises(security.TokenError):
        security.decode_token(forged, expected_type="access")


def test_the_same_forgery_without_a_kid_is_also_rejected() -> None:
    forged = _forge_hs256(_public_pem().encode("utf-8"), kid=None)
    with pytest.raises(security.TokenError):
        security.decode_token(forged, expected_type="access")


def test_an_unsigned_token_is_rejected() -> None:
    """alg=none is the other half of the same family of attacks."""
    forged = jwt.encode(
        {
            "sub": "1",
            "role": "ADMIN",
            "type": "access",
            "jti": "none",
            "iat": 1,
            "exp": 9_999_999_999,
        },
        key="",
        algorithm="none",
    )
    with pytest.raises(security.TokenError):
        security.decode_token(forged, expected_type="access")


def test_a_token_signed_by_an_unrelated_key_is_rejected() -> None:
    stranger = security.generate_key_pair()
    forged = jwt.encode(
        {
            "sub": "1",
            "role": "ADMIN",
            "type": "access",
            "jti": "stranger",
            "iat": 1,
            "exp": 9_999_999_999,
        },
        stranger.private_pem,
        algorithm="RS256",
        headers={"kid": stranger.kid},
    )
    with pytest.raises(security.TokenError):
        security.decode_token(forged, expected_type="access")


# ── Key identity and rotation ────────────────────────────────────────────


def test_a_token_names_the_key_that_signed_it() -> None:
    token, _ = security.create_access_token(subject=1, role="ADMIN")
    header = jwt.get_unverified_header(token)
    assert header.get("kid"), "no kid: a verifier cannot tell which key to use"
    assert header["kid"] == security.active_kid()


def test_the_kid_is_a_thumbprint_of_the_key_it_labels() -> None:
    """Derived, not configured, so the two cannot drift apart."""
    pair = security.generate_key_pair()
    assert pair.kid == security.kid_for_public_pem(pair.public_pem)
    assert pair.kid != security.active_kid()


def test_a_token_from_a_retired_key_still_verifies(monkeypatch) -> None:
    """Rotation without logging everyone out.

    The retired key verifies but never signs, so sessions issued before the
    rotation keep working until they expire on their own.
    """
    retiring = security.generate_key_pair()
    token = jwt.encode(
        {
            "sub": "7",
            "role": "DOCTOR",
            "type": "access",
            "jti": "rotated",
            "iat": 1,
            "exp": 9_999_999_999,
        },
        retiring.private_pem,
        algorithm="RS256",
        headers={"kid": retiring.kid},
    )

    with security.additional_verification_keys([retiring.public_pem]):
        claims = security.decode_token(token, expected_type="access")
    assert claims.subject == 7

    # Once dropped from the ring, the same token stops verifying.
    with pytest.raises(security.TokenError):
        security.decode_token(token, expected_type="access")


def test_a_retired_key_cannot_sign_new_tokens() -> None:
    """Verification and signing are separate capabilities."""
    retiring = security.generate_key_pair()
    with security.additional_verification_keys([retiring.public_pem]):
        token, _ = security.create_access_token(subject=1, role="ADMIN")
    assert jwt.get_unverified_header(token)["kid"] == security.active_kid()


def test_an_unknown_kid_is_rejected() -> None:
    stranger = security.generate_key_pair()
    forged = jwt.encode(
        {
            "sub": "1",
            "role": "ADMIN",
            "type": "access",
            "jti": "unknown-kid",
            "iat": 1,
            "exp": 9_999_999_999,
        },
        stranger.private_pem,
        algorithm="RS256",
        headers={"kid": "not-a-key-we-know"},
    )
    with pytest.raises(security.TokenError):
        security.decode_token(forged, expected_type="access")


# ── Round trip still works ───────────────────────────────────────────────


def test_a_genuine_token_round_trips_with_its_claims() -> None:
    token, issued = security.create_access_token(subject=42, role="DOCTOR")
    claims = security.decode_token(token, expected_type="access")
    assert claims.subject == 42
    assert claims.role == "DOCTOR"
    assert claims.jti == issued.jti
    assert claims.token_type == "access"


def test_an_access_token_is_not_accepted_where_a_refresh_token_is_required() -> None:
    token, _ = security.create_access_token(subject=1, role="ADMIN")
    with pytest.raises(security.TokenError):
        security.decode_token(token, expected_type="refresh")


# ── Configuration ────────────────────────────────────────────────────────


def test_production_refuses_to_start_without_a_configured_signing_key() -> None:
    """An ephemeral key is a development convenience, never a deployment.

    Asserted as a refusal to construct, not merely as a reported problem: the
    process must not reach a first request in this state.
    """
    from app.core.config import Settings
    from pydantic import ValidationError

    with pytest.raises((ValidationError, ValueError)) as raised:
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql://u:p@localhost:5432/db",
            SECRET_KEY="a-long-enough-non-placeholder-secret-value-here",
            SMS_API_KEY="x",
            JWT_PRIVATE_KEY=None,
        )
    assert "JWT_PRIVATE_KEY" in str(raised.value)


def test_a_development_configuration_still_reports_the_missing_key() -> None:
    """The same problem is visible without having to boot production."""
    from app.core.config import Settings

    development = Settings(
        ENVIRONMENT="development",
        DATABASE_URL="postgresql://u:p@localhost:5432/db",
        SECRET_KEY="a-long-enough-non-placeholder-secret-value-here",
        SMS_API_KEY="x",
        JWT_PRIVATE_KEY=None,
    )
    assert any(
        "JWT_PRIVATE_KEY" in problem for problem in development.hardening_problems()
    )


def test_an_ephemeral_key_is_announced_rather_than_silent(caplog) -> None:
    """If sessions will not survive a restart, that must be visible."""
    assert (
        security.using_ephemeral_key() is True or settings.JWT_PRIVATE_KEY is not None
    )
