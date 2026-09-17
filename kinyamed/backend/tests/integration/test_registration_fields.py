"""Registration fields and refresh-cookie hardening (FR-05-02, FR-05-06).

FR-05-02 was INCORRECT on three counts: one `full_name` where the spec asks for
first and last, no `confirm_password`, and phone validation sitting in the
service layer where its bare `ValueError` had no handler, so a mistyped number
returned **500** rather than 422. A 500 is not a validation message: it pages
somebody, it tells the user nothing, and it looks identical to the service
being broken.

FR-05-06 was PARTIAL: the refresh cookie was `SameSite=lax`, and the token was
recorded by `jti` alone rather than as a digest.

WHY SameSite=strict MATTERS HERE. Under `lax` the cookie rides along with a
top-level GET from another site, so a link in an email can carry a live refresh
credential to a page the user did not mean to visit. `strict` withholds it from
every cross-site request. The cost is that a link into the app arrives without
the cookie and the user signs in again; for a clinical system that is the right
side of the trade.

WHY HASH THE TOKEN AT REST. The stored `jti` is not the credential, so storing
it is not itself a leak. Hashing the token means a read of `refresh_tokens` --
a backup, a support export -- yields nothing usable even if the rest of the
table is understood.
"""

from __future__ import annotations

import pytest
from app.core.config import settings

REGISTER = "/api/v1/auth/register"
BASE = {
    "email": "fields@kinyamed.rw",
    "password": "Correct-Horse9-battery",
    "confirm_password": "Correct-Horse9-battery",
    "first_name": "Uwimana",
    "last_name": "Jean",
    "phone": "0788126333",
}


def _register(client, **overrides):
    return client.post(REGISTER, json={**BASE, **overrides})


# ── First and last name ──────────────────────────────────────────────────


def test_registration_takes_a_first_and_last_name(anon_client, db):
    from app.models.user import User
    from sqlalchemy import select

    assert _register(anon_client).status_code in (200, 201)
    user = db.scalars(select(User).where(User.email == BASE["email"])).one()
    assert user.first_name == "Uwimana"
    assert user.last_name == "Jean"


def test_a_missing_last_name_is_rejected(anon_client):
    response = anon_client.post(
        REGISTER, json={k: v for k, v in BASE.items() if k != "last_name"}
    )
    assert response.status_code == 422


# ── Confirm password ─────────────────────────────────────────────────────


def test_a_mismatched_confirmation_is_rejected(anon_client):
    response = _register(anon_client, confirm_password="Different-Horse9-x")
    assert response.status_code == 422
    assert "confirm" in response.text.lower()


def test_a_missing_confirmation_is_rejected(anon_client):
    response = anon_client.post(
        REGISTER, json={k: v for k, v in BASE.items() if k != "confirm_password"}
    )
    assert response.status_code == 422


def test_the_confirmation_is_never_stored_or_echoed(anon_client, db):
    """It is a typing check, not a field."""
    from app.models.user import User
    from sqlalchemy import select

    response = _register(anon_client)
    assert "confirm_password" not in response.text
    user = db.scalars(select(User).where(User.email == BASE["email"])).one()
    assert not hasattr(user, "confirm_password")


# ── Phone: 422, not 500 ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "bad", ["not-a-number", "12", "+", "078812633312345678901234", "07 88 12 abc"]
)
def test_a_malformed_phone_is_a_validation_error(anon_client, bad):
    response = _register(anon_client, phone=bad)
    assert response.status_code == 422, (
        f"{bad!r} produced {response.status_code}; a 500 pages somebody and "
        "tells the user nothing"
    )


def test_a_valid_local_number_is_stored_as_e164(anon_client, db):
    from app.models.user import User
    from sqlalchemy import select

    assert _register(anon_client).status_code in (200, 201)
    user = db.scalars(select(User).where(User.email == BASE["email"])).one()
    assert user.phone is not None and user.phone.startswith("+")


def test_a_staff_account_can_hold_a_phone(client, db):
    """The gap that made a reset code undeliverable to staff."""
    from app.models.user import User
    from sqlalchemy import select

    created = client.post(
        "/api/v1/users",
        json={
            "email": "staff.phone@kinyamed.rw",
            "password": "Correct-Horse9-battery",
            "confirm_password": "Correct-Horse9-battery",
            "first_name": "Staff",
            "last_name": "Member",
            "phone": "0788126444",
            "role": "DOCTOR",
        },
    )
    assert created.status_code in (200, 201), created.text
    user = db.scalars(select(User).where(User.email == "staff.phone@kinyamed.rw")).one()
    assert user.phone is not None and user.phone.startswith("+")


# ── FR-05-06: the refresh cookie ─────────────────────────────────────────


def test_the_refresh_cookie_is_samesite_strict(anon_client):
    response = _register(anon_client)
    header = response.headers.get("set-cookie", "")
    assert "samesite=strict" in header.lower(), (
        f"the refresh cookie is not SameSite=Strict: {header!r}"
    )


def test_the_configured_default_is_strict():
    """Not merely strict in this test's environment."""
    from app.core.config import Settings

    fresh = Settings(
        _env_file=None,
        DATABASE_URL="postgresql://u:p@localhost:5432/db",
        SMS_API_KEY="x",
    )
    assert fresh.REFRESH_COOKIE_SAMESITE == "strict"


def test_the_refresh_cookie_is_httponly(anon_client):
    response = _register(anon_client)
    assert "httponly" in response.headers.get("set-cookie", "").lower()


def test_the_refresh_token_is_not_stored_in_the_clear(anon_client, db):
    from app.models.user import RefreshToken
    from sqlalchemy import select

    _register(anon_client)
    raw = anon_client.cookies[settings.REFRESH_COOKIE_NAME]

    db.expire_all()
    rows = db.scalars(select(RefreshToken)).all()
    assert rows, "no session was recorded"
    for row in rows:
        stored = " ".join(
            str(getattr(row, column.key)) for column in row.__table__.columns
        )
        assert raw not in stored, "the refresh token itself is in the table"


def test_a_stored_session_still_authenticates(anon_client):
    """Hashing must not break what it protects."""
    _register(anon_client)
    assert anon_client.post("/api/v1/auth/refresh").status_code == 200
