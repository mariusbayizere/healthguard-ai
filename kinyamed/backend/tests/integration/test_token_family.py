"""Reuse detection is scoped to one token family (FR-05-13).

A refresh token is a long-lived bearer credential, so presenting one that has
already been rotated away means either it leaked or a client is replaying it.
Either way that lineage is compromised and must end.

WHAT WAS WRONG. The response was to revoke every session the user had. That is
safe and far too broad: a clinician with a phone, a ward workstation and a
laptop lost all three because one of them replayed a token, mid-shift, with no
way to tell which device was at fault.

A FAMILY is one login and everything rotated from it. Logging in starts a
family; each rotation stays inside it. Reuse ends that family and leaves the
others alone, so the blast radius is the compromised device rather than the
person.

The family id is opaque and carries no meaning beyond identity: it is never
shown to a user, never derived from the device, and a reader of the table
learns only that two rows share a lineage.
"""

from __future__ import annotations

import pytest
from app.core.config import settings

REGISTRATION = {
    "email": "family@kinyamed.rw",
    "password": "Correct-Horse9-battery",
    "confirm_password": "Correct-Horse9-battery",
    "first_name": "Fam",
    "last_name": "Ily",
    "phone": "0788123999",
}


def _families(db, user_id: int) -> list[str]:
    from app.models.user import RefreshToken
    from sqlalchemy import select

    db.expire_all()
    return list(
        db.scalars(
            select(RefreshToken.family_id).where(RefreshToken.user_id == user_id)
        ).all()
    )


def _live_count(db, user_id: int) -> int:
    from app.models.user import RefreshToken
    from sqlalchemy import func, select

    db.expire_all()
    return (
        db.scalar(
            select(func.count())
            .select_from(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        )
        or 0
    )


@pytest.fixture
def registered(anon_client, db):
    response = anon_client.post("/api/v1/auth/register", json=REGISTRATION)
    assert response.status_code in (200, 201), response.text
    from app.models.user import User
    from sqlalchemy import select

    user = db.scalars(select(User).where(User.email == REGISTRATION["email"])).one()
    return user


def _login(client) -> str:
    """Start a fresh session on this client.

    Sets the bearer header as well as keeping the refresh cookie: the cookie
    alone gets you /auth/refresh, while /auth/logout-all needs an access token
    like any other authenticated route.
    """
    response = client.post(
        "/api/v1/auth/login",
        json={"email": REGISTRATION["email"], "password": REGISTRATION["password"]},
    )
    assert response.status_code == 200, response.text
    client.headers["Authorization"] = f"Bearer {response.json()['access_token']}"
    return response.cookies[settings.REFRESH_COOKIE_NAME]


# ── The family exists and is stable across rotation ──────────────────────


def test_every_session_records_a_family(registered, db) -> None:
    assert all(_families(db, registered.id)), "a session was stored with no family"


def test_rotation_stays_inside_the_same_family(registered, anon_client, db) -> None:
    before = set(_families(db, registered.id))
    assert anon_client.post("/api/v1/auth/refresh").status_code == 200
    after = set(_families(db, registered.id))
    assert after == before, (
        f"rotation started a new family: {before} -> {after}; reuse detection "
        "would then only ever kill the newest token"
    )


def test_separate_logins_are_separate_families(registered, make_client, db) -> None:
    _login(make_client())
    _login(make_client())
    families = _families(db, registered.id)
    assert len(set(families)) == len(families) >= 3, (
        f"logins shared a family: {families}"
    )


# ── The point of the change ──────────────────────────────────────────────


def test_replaying_a_rotated_token_ends_only_its_own_family(
    registered, make_client, db
) -> None:
    """The clinician's other two devices keep working."""
    phone = make_client()
    workstation = make_client()
    laptop = make_client()

    _login(phone)
    _login(workstation)
    _login(laptop)

    # The phone rotates once; its first token is now spent.
    stale = phone.cookies[settings.REFRESH_COOKIE_NAME]
    assert phone.post("/api/v1/auth/refresh").status_code == 200
    live_before = _live_count(db, registered.id)

    # Somebody replays the spent token.
    phone.cookies.set(settings.REFRESH_COOKIE_NAME, stale)
    replayed = phone.post("/api/v1/auth/refresh")
    assert replayed.status_code == 401
    assert replayed.json()["error"]["code"] == "REFRESH_TOKEN_REUSED"

    # Exactly one family died: the phone's. Two sessions remain.
    assert _live_count(db, registered.id) == live_before - 1, (
        "reuse took down more than the compromised family"
    )
    assert workstation.post("/api/v1/auth/refresh").status_code == 200
    assert laptop.post("/api/v1/auth/refresh").status_code == 200


def test_the_compromised_family_cannot_refresh_again(
    registered, make_client, db
) -> None:
    phone = make_client()
    _login(phone)
    stale = phone.cookies[settings.REFRESH_COOKIE_NAME]
    phone.post("/api/v1/auth/refresh")
    current = phone.cookies[settings.REFRESH_COOKIE_NAME]

    phone.cookies.set(settings.REFRESH_COOKIE_NAME, stale)
    phone.post("/api/v1/auth/refresh")

    # The token that was legitimately current is dead too: it is in the family.
    phone.cookies.set(settings.REFRESH_COOKIE_NAME, current)
    assert phone.post("/api/v1/auth/refresh").status_code == 401, (
        "the live token of a compromised family survived"
    )


# ── What must not regress ────────────────────────────────────────────────


def test_logging_out_everywhere_still_ends_every_family(
    registered, make_client, db
) -> None:
    """Family scoping narrows reuse, not the user's own deliberate action."""
    first = make_client()
    _login(first)
    _login(make_client())
    assert first.post("/api/v1/auth/logout-all").status_code == 200
    assert _live_count(db, registered.id) == 0


def test_a_deactivated_account_still_loses_every_family(
    registered, make_client, client, db
) -> None:
    _login(make_client())
    assert client.patch(f"/api/v1/users/{registered.id}/deactivate").status_code == 200
    assert _live_count(db, registered.id) == 0
