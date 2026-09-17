"""Password reset by six-digit code (FR-05-12).

FOUR PROPERTIES, each of which fails quietly if it is only assumed:

1. ENUMERATION. An unknown email must be indistinguishable from a known one in
   body, status AND elapsed time. Bodies are easy and timing is where this is
   normally lost: the known path hashes a code and writes a row, the unknown
   path returns immediately, and the difference is measurable from the far side
   of the internet. So the unknown path does the same work.

2. SINGLE USE. A consumed code fails on replay even well inside its window. A
   code that works twice is a code that works for whoever reads the SMS second.

3. STORED AS A HASH. The database holds a digest, never the code. The threat is
   a read of the table -- a backup, a log of a query, a support export --
   turning into the ability to take over accounts that have a reset in flight.

4. PER-ACCOUNT REQUEST LIMIT. Without one, anybody who knows an address can make
   this service send unlimited SMS to that person's phone, at the project's
   expense and to the victim's annoyance. The IP limiter does not cover it: the
   attacker rotates addresses, and the victim is chosen by email, not by IP.

The window is ten minutes and the code is six digits, both from FR-05-12.
"""

from __future__ import annotations

import time

import pytest
from app.core.config import settings

REQUEST = "/api/v1/auth/password-reset/request"
CONFIRM = "/api/v1/auth/password-reset/confirm"

KNOWN = {
    "email": "resetme@kinyamed.rw",
    "password": "Correct-Horse9-battery",
    "full_name": "Reset Me",
    "phone": "0788125222",
}
UNKNOWN_EMAIL = "nobody-at-all@kinyamed.rw"
NEW_PASSWORD = "Brand-New-Horse9"


@pytest.fixture
def registered(anon_client, db):
    response = anon_client.post("/api/v1/auth/register", json=KNOWN)
    assert response.status_code in (200, 201), response.text
    anon_client.headers.pop("Authorization", None)
    return response


def _issued_code(db, email: str) -> str:
    """The plaintext code, read from where the test double recorded it.

    The service never returns it and never stores it, so a test cannot read it
    from the response or the table. That is the point of the design, and it is
    why delivery is a seam.
    """
    from app.services import password_reset

    return password_reset.LAST_DELIVERED[email]


# ── 1. Enumeration ───────────────────────────────────────────────────────


def test_an_unknown_email_gets_the_same_status_and_body(registered, anon_client):
    known = anon_client.post(REQUEST, json={"email": KNOWN["email"]})
    unknown = anon_client.post(REQUEST, json={"email": UNKNOWN_EMAIL})

    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json(), (
        f"the bodies differ, which is an account oracle: "
        f"{known.json()} vs {unknown.json()}"
    )


def test_an_unknown_email_takes_comparable_time(registered, anon_client, monkeypatch):
    """Timing is where enumeration resistance is usually lost.

    The known path hashes a code and writes a row. If the unknown path returns
    without doing that work, the difference is visible to a remote caller and
    the identical body was decoration.

    RUN AT PRODUCTION COST ON PURPOSE. The suite hashes at cost 4, about two
    milliseconds, which HTTP overhead swamps: written at the suite cost this
    test passed with the equaliser deleted, proving nothing. At cost 12 the
    hash is the dominant term, so its absence is what the measurement sees.
    Verified by deleting the equaliser and watching this fail.

    Medians of five, so one scheduler hiccup cannot decide the result.
    """
    monkeypatch.setattr(settings, "BCRYPT_ROUNDS", 12)

    def sample(email: str) -> float:
        started = time.perf_counter()
        anon_client.post(REQUEST, json={"email": email})
        return time.perf_counter() - started

    # Warm the path once; the first call pays import and connection costs.
    sample(KNOWN["email"])
    sample(UNKNOWN_EMAIL)

    known = sorted(sample(KNOWN["email"]) for _ in range(5))[2]
    unknown = sorted(sample(UNKNOWN_EMAIL) for _ in range(5))[2]

    slower, faster = max(known, unknown), min(known, unknown)
    assert slower < faster * 3, (
        f"known={known:.4f}s unknown={unknown:.4f}s, a {slower / faster:.1f}x "
        "difference: the two paths do measurably different work"
    )


# ── 2. Single use ────────────────────────────────────────────────────────


def test_a_code_works_once(registered, anon_client, db):
    anon_client.post(REQUEST, json={"email": KNOWN["email"]})
    code = _issued_code(db, KNOWN["email"])

    first = anon_client.post(
        CONFIRM,
        json={"email": KNOWN["email"], "code": code, "new_password": NEW_PASSWORD},
    )
    assert first.status_code == 200, first.text

    replay = anon_client.post(
        CONFIRM,
        json={"email": KNOWN["email"], "code": code, "new_password": "Other-Horse9-x"},
    )
    assert replay.status_code == 400, (
        "the code was accepted twice; whoever reads the SMS second gets the account"
    )


def test_the_new_password_actually_works(registered, anon_client, db):
    anon_client.post(REQUEST, json={"email": KNOWN["email"]})
    code = _issued_code(db, KNOWN["email"])
    anon_client.post(
        CONFIRM,
        json={"email": KNOWN["email"], "code": code, "new_password": NEW_PASSWORD},
    )

    assert (
        anon_client.post(
            "/api/v1/auth/login",
            json={"email": KNOWN["email"], "password": NEW_PASSWORD},
        ).status_code
        == 200
    )
    assert (
        anon_client.post(
            "/api/v1/auth/login",
            json={"email": KNOWN["email"], "password": KNOWN["password"]},
        ).status_code
        == 401
    ), "the old password still works"


def test_a_reset_ends_every_existing_session(registered, anon_client, db):
    """A reset is what someone does when they fear the account is compromised."""
    from app.models.user import RefreshToken, User
    from sqlalchemy import func, select

    user = db.scalars(select(User).where(User.email == KNOWN["email"])).one()
    anon_client.post(REQUEST, json={"email": KNOWN["email"]})
    code = _issued_code(db, KNOWN["email"])
    anon_client.post(
        CONFIRM,
        json={"email": KNOWN["email"], "code": code, "new_password": NEW_PASSWORD},
    )

    db.expire_all()
    live = db.scalar(
        select(func.count())
        .select_from(RefreshToken)
        .where(RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None))
    )
    assert live == 0


def test_an_expired_code_is_refused(registered, anon_client, db, monkeypatch):
    from app.services import password_reset

    monkeypatch.setattr(password_reset, "CODE_LIFETIME_MINUTES", 0)
    anon_client.post(REQUEST, json={"email": KNOWN["email"]})
    code = _issued_code(db, KNOWN["email"])

    response = anon_client.post(
        CONFIRM,
        json={"email": KNOWN["email"], "code": code, "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 400


def test_the_window_is_ten_minutes(registered) -> None:
    from app.services import password_reset

    assert password_reset.CODE_LIFETIME_MINUTES == 10


def test_a_wrong_code_is_refused(registered, anon_client, db):
    anon_client.post(REQUEST, json={"email": KNOWN["email"]})
    real = _issued_code(db, KNOWN["email"])
    wrong = "000000" if real != "000000" else "111111"

    response = anon_client.post(
        CONFIRM,
        json={"email": KNOWN["email"], "code": wrong, "new_password": NEW_PASSWORD},
    )
    assert response.status_code == 400


def test_the_code_is_six_digits(registered, anon_client, db):
    anon_client.post(REQUEST, json={"email": KNOWN["email"]})
    code = _issued_code(db, KNOWN["email"])
    assert len(code) == 6 and code.isdigit(), code


# ── 3. Stored as a hash ──────────────────────────────────────────────────


def test_the_plaintext_code_is_never_stored(registered, anon_client, db):
    from app.models.password_reset import PasswordResetCode
    from sqlalchemy import select

    anon_client.post(REQUEST, json={"email": KNOWN["email"]})
    code = _issued_code(db, KNOWN["email"])

    db.expire_all()
    rows = db.scalars(select(PasswordResetCode)).all()
    assert rows, "nothing was recorded"
    for row in rows:
        stored = " ".join(
            str(getattr(row, column.key)) for column in row.__table__.columns
        )
        assert code not in stored, (
            "the code itself is in the table; a backup or a support export "
            "becomes account takeover for every reset in flight"
        )


# ── 4. Per-account request limit ─────────────────────────────────────────


def test_requests_for_one_account_are_capped(registered, anon_client):
    """Otherwise anyone who knows an address bills us for unlimited SMS to it.

    The IP limiter does not cover this: an attacker rotates addresses, and the
    victim is chosen by email rather than by IP.
    """
    from app.services import password_reset

    statuses = [
        anon_client.post(REQUEST, json={"email": KNOWN["email"]}).status_code
        for _ in range(password_reset.MAX_REQUESTS_PER_WINDOW + 3)
    ]
    assert set(statuses) == {202}, (
        f"the cap leaked into the response and became an oracle: {statuses}"
    )

    from app.models.password_reset import PasswordResetCode
    from sqlalchemy import func, select

    issued = anon_client.app  # noqa: F841 - readability only
    from app.core.database import SessionLocal

    with SessionLocal() as session:
        count = session.scalar(select(func.count()).select_from(PasswordResetCode))
    assert count is not None and count <= password_reset.MAX_REQUESTS_PER_WINDOW, (
        f"{count} codes were issued for one account; the cap does not hold"
    )


def test_the_cap_is_silent(registered, anon_client):
    """Refusing visibly would tell an attacker the address exists."""
    from app.services import password_reset

    for _ in range(password_reset.MAX_REQUESTS_PER_WINDOW + 2):
        anon_client.post(REQUEST, json={"email": KNOWN["email"]})

    capped = anon_client.post(REQUEST, json={"email": KNOWN["email"]})
    unknown = anon_client.post(REQUEST, json={"email": UNKNOWN_EMAIL})
    assert capped.status_code == unknown.status_code == 202
    assert capped.json() == unknown.json()


# ── Delivery carries no PII into logs ────────────────────────────────────


def test_the_code_never_reaches_a_log(registered, anon_client, db, capsys):
    anon_client.post(REQUEST, json={"email": KNOWN["email"]})
    code = _issued_code(db, KNOWN["email"])
    captured = capsys.readouterr()
    assert code not in captured.out + captured.err, (
        "the reset code was logged; anyone with log access can take the account"
    )
