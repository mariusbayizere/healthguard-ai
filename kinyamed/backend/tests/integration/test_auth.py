"""Authentication: registration, login, refresh rotation, logout."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.models.user import UserRole

REGISTRATION = {
    "email": "uwimana@example.rw",
    "password": "correct-horse-battery",
    "full_name": "Uwimana Jean",
    "phone": "0788123456",
    "age": 34,
}


def test_registration_creates_a_patient_login_and_chart(anon_client, db):
    from app.models.patient import Patient
    from app.models.user import User

    response = anon_client.post("/api/v1/auth/register", json=REGISTRATION)
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["user"]["role"] == "PATIENT"
    assert body["user"]["patient_id"] is not None
    assert body["access_token"]
    assert body["expires_in"] == settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    assert db.query(User).count() == 1
    assert db.query(Patient).count() == 1


def test_registration_never_returns_the_password_or_refresh_token(anon_client):
    body = anon_client.post("/api/v1/auth/register", json=REGISTRATION).text
    assert REGISTRATION["password"] not in body
    assert "refresh_token" not in body


def test_refresh_token_is_httponly_and_scoped(anon_client):
    response = anon_client.post("/api/v1/auth/register", json=REGISTRATION)
    cookie = response.headers["set-cookie"]
    assert settings.REFRESH_COOKIE_NAME in cookie
    assert "HttpOnly" in cookie
    assert f"Path={settings.API_PREFIX}/auth" in cookie


def test_password_is_stored_as_a_bcrypt_digest(anon_client, db):
    from app.models.user import User

    anon_client.post("/api/v1/auth/register", json=REGISTRATION)
    stored = db.query(User).one().hashed_password
    assert stored.startswith("$2b$")
    assert REGISTRATION["password"] not in stored


def test_duplicate_email_is_rejected(anon_client):
    anon_client.post("/api/v1/auth/register", json=REGISTRATION)
    again = anon_client.post("/api/v1/auth/register", json=REGISTRATION)
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


@pytest.mark.parametrize("password", ["short", "elevenchars"])
def test_weak_passwords_are_rejected(anon_client, password):
    payload = {**REGISTRATION, "password": password}
    assert anon_client.post("/api/v1/auth/register", json=payload).status_code == 422


def test_login_succeeds_and_records_the_time(anon_client, db):
    from app.models.user import User

    anon_client.post("/api/v1/auth/register", json=REGISTRATION)
    response = anon_client.post(
        "/api/v1/auth/login",
        json={"email": REGISTRATION["email"], "password": REGISTRATION["password"]},
    )
    assert response.status_code == 200
    assert db.query(User).one().last_login_at is not None


def test_wrong_password_and_unknown_email_are_indistinguishable(anon_client):
    """Different messages would turn login into an account-enumeration oracle."""
    anon_client.post("/api/v1/auth/register", json=REGISTRATION)

    wrong = anon_client.post(
        "/api/v1/auth/login", json={"email": REGISTRATION["email"], "password": "wrong-password"}
    )
    unknown = anon_client.post(
        "/api/v1/auth/login", json={"email": "nobody@example.rw", "password": "wrong-password"}
    )
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()


def test_deactivated_account_cannot_log_in(anon_client, db):
    from app.models.user import User

    anon_client.post("/api/v1/auth/register", json=REGISTRATION)
    db.query(User).one().is_active = False
    db.commit()

    response = anon_client.post(
        "/api/v1/auth/login",
        json={"email": REGISTRATION["email"], "password": REGISTRATION["password"]},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "ACCOUNT_INACTIVE"


def test_me_requires_a_token(anon_client):
    unauthenticated = anon_client.get("/api/v1/auth/me")
    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error"]["code"] == "INVALID_TOKEN"


def test_me_returns_the_token_holder(anon_client):
    token = anon_client.post("/api/v1/auth/register", json=REGISTRATION).json()["access_token"]
    body = anon_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}
    ).json()
    assert body["email"] == REGISTRATION["email"]
    assert body["role"] == UserRole.PATIENT.value


def test_a_tampered_token_is_rejected(anon_client):
    token = anon_client.post("/api/v1/auth/register", json=REGISTRATION).json()["access_token"]
    response = anon_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {token[:-2]}xy"}
    )
    assert response.status_code == 401


def test_a_refresh_token_is_not_accepted_as_an_access_token(anon_client):
    """Token-type confusion would give a 7-day access token."""
    anon_client.post("/api/v1/auth/register", json=REGISTRATION)
    refresh_cookie = anon_client.cookies[settings.REFRESH_COOKIE_NAME]
    response = anon_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh_cookie}"}
    )
    assert response.status_code == 401


def test_refresh_rotates_the_token(anon_client):
    first = anon_client.post("/api/v1/auth/register", json=REGISTRATION)
    original_cookie = anon_client.cookies[settings.REFRESH_COOKIE_NAME]

    refreshed = anon_client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    assert anon_client.cookies[settings.REFRESH_COOKIE_NAME] != original_cookie
    assert refreshed.json()["access_token"] != first.json()["access_token"]


def test_reusing_a_rotated_refresh_token_ends_every_session(anon_client, db):
    """Replay of a rotated token is the signature of a stolen credential."""
    from app.models.user import RefreshToken

    anon_client.post("/api/v1/auth/register", json=REGISTRATION)
    stolen = anon_client.cookies[settings.REFRESH_COOKIE_NAME]
    anon_client.post("/api/v1/auth/refresh")  # rotates `stolen` away

    anon_client.cookies.set(settings.REFRESH_COOKIE_NAME, stolen)
    replay = anon_client.post("/api/v1/auth/refresh")
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "REFRESH_TOKEN_REUSED"

    live = db.query(RefreshToken).filter(RefreshToken.revoked_at.is_(None)).count()
    assert live == 0, "all sessions must be ended after reuse is detected"


def test_refresh_without_a_cookie_is_rejected(anon_client):
    assert anon_client.post("/api/v1/auth/refresh").status_code == 401


def test_logout_revokes_the_session(anon_client):
    anon_client.post("/api/v1/auth/register", json=REGISTRATION)
    assert anon_client.post("/api/v1/auth/logout").status_code == 200
    assert anon_client.post("/api/v1/auth/refresh").status_code == 401


def test_logout_succeeds_without_a_session(anon_client):
    """A client must always be able to clear its own state."""
    assert anon_client.post("/api/v1/auth/logout").status_code == 200


def test_logout_all_ends_every_device(anon_client, db):
    from app.models.user import RefreshToken

    token = anon_client.post("/api/v1/auth/register", json=REGISTRATION).json()["access_token"]
    anon_client.post(
        "/api/v1/auth/login",
        json={"email": REGISTRATION["email"], "password": REGISTRATION["password"]},
    )
    assert db.query(RefreshToken).filter(RefreshToken.revoked_at.is_(None)).count() == 2

    response = anon_client.post(
        "/api/v1/auth/logout-all", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert db.query(RefreshToken).filter(RefreshToken.revoked_at.is_(None)).count() == 0


def test_changing_password_ends_other_sessions_and_changes_the_credential(anon_client):
    token = anon_client.post("/api/v1/auth/register", json=REGISTRATION).json()["access_token"]

    changed = anon_client.post(
        "/api/v1/auth/change-password",
        json={
            "current_password": REGISTRATION["password"],
            "new_password": "a-brand-new-passphrase",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert changed.status_code == 200
    assert anon_client.post("/api/v1/auth/refresh").status_code == 401

    old = anon_client.post(
        "/api/v1/auth/login",
        json={"email": REGISTRATION["email"], "password": REGISTRATION["password"]},
    )
    assert old.status_code == 401
    new = anon_client.post(
        "/api/v1/auth/login",
        json={"email": REGISTRATION["email"], "password": "a-brand-new-passphrase"},
    )
    assert new.status_code == 200


def test_wrong_current_password_does_not_change_the_credential(anon_client):
    token = anon_client.post("/api/v1/auth/register", json=REGISTRATION).json()["access_token"]
    response = anon_client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "not-the-password", "new_password": "another-passphrase"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 401


def test_sessions_lists_only_live_sessions(anon_client):
    token = anon_client.post("/api/v1/auth/register", json=REGISTRATION).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert len(anon_client.get("/api/v1/auth/sessions", headers=headers).json()) == 1

    anon_client.post("/api/v1/auth/logout")
    assert anon_client.get("/api/v1/auth/sessions", headers=headers).json() == []


def test_production_requires_a_strong_bcrypt_cost():
    """The suite lowers the cost factor; production must not be able to."""
    from app.core.config import Settings

    with pytest.raises(ValueError, match="BCRYPT_ROUNDS"):
        Settings(
            ENVIRONMENT="production",
            DATABASE_URL="postgresql://u:p@localhost:5432/db",
            SECRET_KEY="x" * 48,
            SMS_API_KEY="k",
            BCRYPT_ROUNDS=4,
            CORS_ORIGINS="https://kinyamed.rw",
        )
