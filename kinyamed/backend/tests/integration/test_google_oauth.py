"""Google sign-in: the ID token is VERIFIED, not decoded (FR-05-03, FR-05-04).

THE DEFECT THIS FILE EXISTS TO PREVENT. A Google ID token is a JWT, and it is
trivially readable without verification. An implementation that base64-decodes
it and trusts the `email` inside will authenticate anyone who can type JSON:
the token never has to have come from Google at all. That is the common way
this feature is got wrong, and from the outside it is indistinguishable from a
correct one, because both log the user in.

So the tests here are mostly forgeries. Each presents a token that a naive
implementation accepts and a verifying one refuses:

  * signed by a key that is not Google's;
  * unsigned (`alg=none`);
  * HMAC-signed with Google's own public key as the secret -- the algorithm
    confusion attack, identical in shape to the one the RS256 work closed, and
    the reason the algorithm is pinned on the verifier rather than read from
    the token's header;
  * issued for a different `aud`, i.e. a real Google token for another
    application;
  * from the wrong `iss`;
  * expired.

JWKS is mocked throughout. Reaching Google in a test would make the suite
depend on the network and on a third party's uptime, and it would test their
availability rather than our verification.
"""

from __future__ import annotations

import time

import jwt
import pytest
from app.core.config import settings

SIGN_IN = "/api/v1/auth/google"


@pytest.fixture
def google(monkeypatch):
    """A fake Google: one signing key, served through a mocked JWKS."""
    from app.core import google_identity
    from app.core.jwt_keys import generate_key_pair

    pair = generate_key_pair()
    monkeypatch.setattr(
        settings, "GOOGLE_CLIENT_ID", "kinyamed.apps.googleusercontent.com"
    )
    google_identity.reset_cache()

    calls = {"count": 0}

    def fake_fetch() -> dict[str, str]:
        calls["count"] += 1
        return {pair.kid: pair.public_pem}

    monkeypatch.setattr(google_identity, "_fetch_jwks", fake_fetch)
    yield pair, calls
    google_identity.reset_cache()


def _token(
    pair,
    *,
    aud: str = "kinyamed.apps.googleusercontent.com",
    iss: str = "https://accounts.google.com",
    exp_in: int = 600,
    email: str = "clinician@gmail.com",
    email_verified: bool = True,
    sub: str = "google-subject-1",
    key=None,
    algorithm: str = "RS256",
    kid: str | None = None,
) -> str:
    now = int(time.time())
    claims = {
        "iss": iss,
        "aud": aud,
        "sub": sub,
        "email": email,
        "email_verified": email_verified,
        "given_name": "Clin",
        "family_name": "Ician",
        "picture": "https://lh3.googleusercontent.com/a/x",
        "iat": now,
        "exp": now + exp_in,
    }
    return jwt.encode(
        claims,
        key if key is not None else pair.private_pem,
        algorithm=algorithm,
        headers={"kid": kid or pair.kid},
    )


# ── Forgeries: every one of these a decode-only implementation accepts ────


def test_a_token_naming_an_unknown_key_is_refused(google, anon_client):
    """A kid Google does not publish. Rejected before any signature check."""
    pair, _ = google
    from app.core.jwt_keys import generate_key_pair

    stranger = generate_key_pair()
    forged = _token(pair, key=stranger.private_pem, kid=stranger.kid)
    assert anon_client.post(SIGN_IN, json={"id_token": forged}).status_code == 401


def test_a_token_signed_by_a_stranger_under_googles_kid_is_refused(google, anon_client):
    """The signature itself, isolated.

    This token claims Google's key id and is signed by somebody else, so the
    kid lookup SUCCEEDS and the only thing that can refuse it is verifying the
    signature against the key that kid names. Written this way after mutation
    testing: the earlier version used the stranger's own kid, so it was
    rejected as an unknown key and proved nothing about signatures. Disabling
    signature verification left it passing.
    """
    pair, _ = google
    from app.core.jwt_keys import generate_key_pair

    stranger = generate_key_pair()
    forged = _token(pair, key=stranger.private_pem, kid=pair.kid)
    assert anon_client.post(SIGN_IN, json={"id_token": forged}).status_code == 401


def test_a_genuinely_signed_token_with_a_wrong_kid_is_refused(google, anon_client):
    """The kid check, isolated from the signature check.

    Signed by the key Google really holds, but naming a kid Google does not
    publish. A verifier that falls back to "some key in the ring" when the kid
    is unknown ACCEPTS this, because the signature does verify -- so signature
    checking cannot catch it and only the kid lookup can. Added after a
    mutation ("unknown kid tolerated") survived against the previous test,
    which was rejected by the signature path instead and so proved nothing
    about key selection.
    """
    pair, _ = google
    forged = _token(pair, kid="a-kid-google-does-not-publish")
    assert anon_client.post(SIGN_IN, json={"id_token": forged}).status_code == 401


def test_an_unsigned_token_is_refused(google, anon_client):
    pair, _ = google
    forged = _token(pair, key="", algorithm="none")
    assert anon_client.post(SIGN_IN, json={"id_token": forged}).status_code == 401


def test_a_token_hmac_signed_with_googles_public_key_is_refused(google, anon_client):
    """Algorithm confusion. The public key is not a signing secret."""
    import base64
    import hashlib
    import hmac
    import json

    pair, _ = google
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT", "kid": pair.kid}
    claims = {
        "iss": "https://accounts.google.com",
        "aud": "kinyamed.apps.googleusercontent.com",
        "sub": "attacker",
        "email": "clinician@gmail.com",
        "email_verified": True,
        "iat": now,
        "exp": now + 600,
    }

    def b64(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    signing_input = (
        f"{b64(json.dumps(header).encode())}.{b64(json.dumps(claims).encode())}"
    )
    mac = hmac.new(
        pair.public_pem.encode(), signing_input.encode(), hashlib.sha256
    ).digest()
    forged = f"{signing_input}.{b64(mac)}"

    assert anon_client.post(SIGN_IN, json={"id_token": forged}).status_code == 401


def test_a_token_for_another_application_is_refused(google, anon_client):
    """A real Google token, correctly signed, issued to somebody else."""
    pair, _ = google
    other = _token(pair, aud="someone-else.apps.googleusercontent.com")
    assert anon_client.post(SIGN_IN, json={"id_token": other}).status_code == 401


def test_a_token_from_the_wrong_issuer_is_refused(google, anon_client):
    pair, _ = google
    assert (
        anon_client.post(
            SIGN_IN, json={"id_token": _token(pair, iss="https://evil.example")}
        ).status_code
        == 401
    )


def test_an_expired_token_is_refused(google, anon_client):
    pair, _ = google
    assert (
        anon_client.post(
            SIGN_IN, json={"id_token": _token(pair, exp_in=-60)}
        ).status_code
        == 401
    )


def test_an_unverified_email_is_refused(google, anon_client):
    """Linking on an unverified address would let anyone claim any account."""
    pair, _ = google
    assert (
        anon_client.post(
            SIGN_IN, json={"id_token": _token(pair, email_verified=False)}
        ).status_code
        == 401
    )


# ── The happy path ───────────────────────────────────────────────────────


def test_a_genuine_token_signs_the_user_in(google, anon_client, db):
    pair, _ = google
    response = anon_client.post(SIGN_IN, json={"id_token": _token(pair)})
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]


def test_a_new_google_user_becomes_a_patient(google, anon_client, db):
    from app.models.user import User, UserRole
    from sqlalchemy import select

    pair, _ = google
    anon_client.post(SIGN_IN, json={"id_token": _token(pair)})

    db.expire_all()
    user = db.scalars(select(User).where(User.email == "clinician@gmail.com")).one()
    assert user.role is UserRole.PATIENT
    assert user.oauth_provider == "google"
    assert user.hashed_password is None, "a Google account should hold no password"


# ── FR-05-04: linking ────────────────────────────────────────────────────


def test_signing_in_twice_does_not_create_a_second_account(google, anon_client, db):
    from app.models.user import User
    from sqlalchemy import func, select

    pair, _ = google
    anon_client.post(SIGN_IN, json={"id_token": _token(pair)})
    anon_client.post(SIGN_IN, json={"id_token": _token(pair)})

    db.expire_all()
    count = db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.email == "clinician@gmail.com")
    )
    assert count == 1


def test_google_links_to_an_existing_password_account(google, anon_client, db):
    """Same verified address: one person, one account, either way in."""
    from app.models.user import User
    from sqlalchemy import func, select

    pair, _ = google
    anon_client.post(
        "/api/v1/auth/register",
        json={
            "email": "clinician@gmail.com",
            "password": "Correct-Horse9-battery",
            "confirm_password": "Correct-Horse9-battery",
            "first_name": "Clin",
            "last_name": "Ician",
            "phone": "0788127555",
        },
    )
    assert anon_client.post(SIGN_IN, json={"id_token": _token(pair)}).status_code == 200

    db.expire_all()
    assert (
        db.scalar(
            select(func.count())
            .select_from(User)
            .where(User.email == "clinician@gmail.com")
        )
        == 1
    )
    user = db.scalars(select(User).where(User.email == "clinician@gmail.com")).one()
    assert user.oauth_provider == "google"
    assert user.hashed_password is not None, "linking must not delete the password"


def test_password_login_still_works_after_linking(google, anon_client):
    pair, _ = google
    anon_client.post(
        "/api/v1/auth/register",
        json={
            "email": "clinician@gmail.com",
            "password": "Correct-Horse9-battery",
            "confirm_password": "Correct-Horse9-battery",
            "first_name": "Clin",
            "last_name": "Ician",
            "phone": "0788127556",
        },
    )
    anon_client.post(SIGN_IN, json={"id_token": _token(pair)})
    assert (
        anon_client.post(
            "/api/v1/auth/login",
            json={
                "email": "clinician@gmail.com",
                "password": "Correct-Horse9-battery",
            },
        ).status_code
        == 200
    )


def test_a_deactivated_account_cannot_sign_in_with_google(
    google, anon_client, db, client
):
    """FR-03-02 says deactivation blocks EVERY method. This is the new one."""
    from app.models.user import User
    from sqlalchemy import select

    pair, _ = google
    anon_client.post(SIGN_IN, json={"id_token": _token(pair)})
    db.expire_all()
    user = db.scalars(select(User).where(User.email == "clinician@gmail.com")).one()

    assert client.patch(f"/api/v1/users/{user.id}/deactivate").status_code == 200
    assert anon_client.post(SIGN_IN, json={"id_token": _token(pair)}).status_code == 403


# ── JWKS caching and the outage path ─────────────────────────────────────


def test_the_key_set_is_cached(google, anon_client):
    """One fetch, not one per sign-in: Google rate-limits and we would deserve it."""
    pair, calls = google
    for _ in range(4):
        anon_client.post(SIGN_IN, json={"id_token": _token(pair)})
    assert calls["count"] == 1, f"JWKS was fetched {calls['count']} times"


def test_the_cache_has_a_one_hour_ttl():
    from app.core import google_identity

    assert google_identity.JWKS_TTL_SECONDS == 3600


def test_password_login_survives_google_being_unavailable(monkeypatch, anon_client):
    """ENGINEERING_SPEC §6.3: an outage at Google is not an outage here."""
    from app.core import google_identity

    google_identity.reset_cache()

    def dead_fetch() -> dict[str, str]:
        raise RuntimeError("JWKS endpoint returned 503")

    monkeypatch.setattr(google_identity, "_fetch_jwks", dead_fetch)
    monkeypatch.setattr(
        settings, "GOOGLE_CLIENT_ID", "kinyamed.apps.googleusercontent.com"
    )

    anon_client.post(
        "/api/v1/auth/register",
        json={
            "email": "password.person@kinyamed.rw",
            "password": "Correct-Horse9-battery",
            "confirm_password": "Correct-Horse9-battery",
            "first_name": "Pass",
            "last_name": "Word",
            "phone": "0788127777",
        },
    )
    anon_client.headers.pop("Authorization", None)

    assert (
        anon_client.post(
            "/api/v1/auth/login",
            json={
                "email": "password.person@kinyamed.rw",
                "password": "Correct-Horse9-battery",
            },
        ).status_code
        == 200
    ), "a Google outage took down password sign-in"

    google_identity.reset_cache()


def test_google_sign_in_reports_the_outage_rather_than_a_generic_failure(
    monkeypatch, anon_client, google
):
    pair, _ = google
    from app.core import google_identity

    google_identity.reset_cache()
    monkeypatch.setattr(
        google_identity,
        "_fetch_jwks",
        lambda: (_ for _ in ()).throw(RuntimeError("503")),
    )
    response = anon_client.post(SIGN_IN, json={"id_token": _token(pair)})
    assert response.status_code == 503
    assert response.headers.get("Retry-After")


def test_sign_in_is_refused_when_no_client_id_is_configured(monkeypatch, anon_client):
    """Without an audience to check against, verification is not verification."""
    from app.core import google_identity

    google_identity.reset_cache()
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", None)
    response = anon_client.post(SIGN_IN, json={"id_token": "anything"})
    assert response.status_code in (401, 503)
