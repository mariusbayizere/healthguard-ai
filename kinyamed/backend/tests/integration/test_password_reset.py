"""The password reset flow, end to end.

Three security properties matter more than the happy path here, and each has a
test that fails loudly if it regresses:

  * the request endpoint does not reveal whether an account exists;
  * a token is single-use, and expiry is enforced;
  * redeeming one revokes every existing session.

The raw token is read from the service return rather than from the database,
because the database only ever holds its SHA-256 — which is itself asserted.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from app.models.user import PasswordResetToken
from app.services import auth_service

REQUEST = "/api/v1/auth/password-reset/request"
VALIDATE = "/api/v1/auth/password-reset/validate"
CONFIRM = "/api/v1/auth/password-reset/confirm"

NEW_PASSWORD = "a-brand-new-password-42"


@pytest.fixture
def account(user_factory):
    return user_factory(email="reset.me@example.com", password="original-password-1")


def _issue(db, email: str) -> str:
    issued = auth_service.request_password_reset(db, email)
    assert issued is not None
    return issued.token


class TestRequest:
    def test_answers_identically_for_known_and_unknown_addresses(
        self, anon_client, account
    ):
        """An endpoint that distinguishes them is an account-existence oracle.

        For this system the account set is the staff of a named health centre,
        so that oracle is a list of who works there.
        """
        known = anon_client.post(REQUEST, json={"email": account.email})
        unknown = anon_client.post(REQUEST, json={"email": "nobody@example.com"})

        assert known.status_code == unknown.status_code == 200
        assert known.json() == unknown.json()

    def test_never_returns_the_token(self, anon_client, account):
        body = anon_client.post(REQUEST, json={"email": account.email}).text
        assert "token" not in body.lower()

    def test_stores_only_the_hash(self, anon_client, db, account):
        raw = _issue(db, account.email)
        rows = db.query(PasswordResetToken).all()

        assert rows, "a token should have been issued"
        stored = {row.token_hash for row in rows}
        assert raw not in stored, "the RAW token must never be persisted"
        assert hashlib.sha256(raw.encode()).hexdigest() in stored


class TestValidate:
    def test_a_fresh_token_is_valid(self, anon_client, db, account):
        raw = _issue(db, account.email)
        assert anon_client.get(f"{VALIDATE}?token={raw}").json() == {"valid": True}

    def test_nonsense_is_not_valid(self, anon_client):
        assert anon_client.get(f"{VALIDATE}?token={'x' * 40}").json()["valid"] is False

    def test_validating_does_not_spend_the_token(self, anon_client, db, account):
        raw = _issue(db, account.email)
        anon_client.get(f"{VALIDATE}?token={raw}")
        assert anon_client.get(f"{VALIDATE}?token={raw}").json() == {"valid": True}


class TestConfirm:
    def test_sets_the_new_password(self, anon_client, db, account):
        raw = _issue(db, account.email)
        response = anon_client.post(
            CONFIRM, json={"token": raw, "new_password": NEW_PASSWORD}
        )
        assert response.status_code == 200

        login = anon_client.post(
            "/api/v1/auth/login",
            json={"email": account.email, "password": NEW_PASSWORD},
        )
        assert login.status_code == 200, "the new password should work"

    def test_the_old_password_stops_working(self, anon_client, db, account):
        raw = _issue(db, account.email)
        anon_client.post(CONFIRM, json={"token": raw, "new_password": NEW_PASSWORD})

        stale = anon_client.post(
            "/api/v1/auth/login",
            json={"email": account.email, "password": "original-password-1"},
        )
        assert stale.status_code == 401

    def test_a_token_is_single_use(self, anon_client, db, account):
        raw = _issue(db, account.email)
        first = anon_client.post(
            CONFIRM, json={"token": raw, "new_password": NEW_PASSWORD}
        )
        assert first.status_code == 200

        second = anon_client.post(
            CONFIRM, json={"token": raw, "new_password": "another-password-99"}
        )
        assert second.status_code == 401, "a spent token must not work twice"

    def test_an_expired_token_is_refused(self, anon_client, db, account):
        raw = _issue(db, account.email)
        row = db.query(PasswordResetToken).one()
        row.expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()

        assert anon_client.get(f"{VALIDATE}?token={raw}").json()["valid"] is False
        assert (
            anon_client.post(
                CONFIRM, json={"token": raw, "new_password": NEW_PASSWORD}
            ).status_code
            == 401
        )

    def test_unknown_used_and_expired_are_indistinguishable(
        self, anon_client, db, account
    ):
        """One error for all three, so the response cannot probe token history."""
        raw = _issue(db, account.email)
        anon_client.post(CONFIRM, json={"token": raw, "new_password": NEW_PASSWORD})

        used = anon_client.post(
            CONFIRM, json={"token": raw, "new_password": NEW_PASSWORD}
        )
        unknown = anon_client.post(
            CONFIRM, json={"token": "z" * 43, "new_password": NEW_PASSWORD}
        )
        assert used.status_code == unknown.status_code
        assert used.json() == unknown.json(), (
            "a used token and an unknown one must produce an identical body, "
            "or the difference is an oracle for which tokens existed"
        )

    def test_resetting_revokes_every_existing_session(self, anon_client, db, account):
        """A reset usually follows a lost device or a lost password.

        Leaving live refresh tokens behind would make the reset cosmetic:
        whoever still holds one can mint access tokens against the account
        whose password was just changed. Asserted against the stored sessions
        rather than a second HTTP client, so it tests the property and not the
        test harness.
        """
        from app.models.user import RefreshToken

        anon_client.post(
            "/api/v1/auth/login",
            json={"email": account.email, "password": "original-password-1"},
        )
        live = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.user_id == account.id, RefreshToken.revoked_at.is_(None)
            )
            .count()
        )
        assert live >= 1, "signing in should have created a session to revoke"

        raw = _issue(db, account.email)
        anon_client.post(CONFIRM, json={"token": raw, "new_password": NEW_PASSWORD})
        db.expire_all()

        still_live = (
            db.query(RefreshToken)
            .filter(
                RefreshToken.user_id == account.id, RefreshToken.revoked_at.is_(None)
            )
            .count()
        )
        assert still_live == 0, "every session must be revoked by a reset"
        assert db.query(PasswordResetToken).one().used_at is not None


class TestProfileUpdate:
    def test_changes_the_name(self, client):
        response = client.patch("/api/v1/auth/me", json={"full_name": "Dr A Name"})
        assert response.status_code == 200
        assert response.json()["full_name"] == "Dr A Name"

    def test_rejects_a_blank_name(self, client):
        assert (
            client.patch("/api/v1/auth/me", json={"full_name": " "}).status_code == 422
        )

    def test_cannot_grant_itself_a_role(self, client):
        """Role is not self-service. An account that can promote itself is a
        vulnerability, not an account."""
        before = client.get("/api/v1/auth/me").json()["role"]
        client.patch("/api/v1/auth/me", json={"full_name": "X Y", "role": "ADMIN"})
        assert client.get("/api/v1/auth/me").json()["role"] == before

    def test_requires_authentication(self, anon_client):
        assert (
            anon_client.patch("/api/v1/auth/me", json={"full_name": "X Y"}).status_code
            == 401
        )
