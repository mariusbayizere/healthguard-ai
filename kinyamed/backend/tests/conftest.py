"""Test fixtures.

Tests run against a dedicated Postgres database that is created and migrated
once per session, then truncated between tests. The real database is exercised
deliberately: the behaviour under test (cascade rules, sequences, enum types,
FILTER aggregates) is enforced by Postgres and would not appear under SQLite.
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import psycopg2
import pytest
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

TEST_DB_NAME = os.environ.get("TEST_DB_NAME", "kinyamed_test")


def _admin_url() -> str:
    """Connection URL for the maintenance database, from the developer's .env."""
    from dotenv import dotenv_values

    url = os.environ.get("DATABASE_URL") or dotenv_values(".env").get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL must be set (directly or in .env) to run the tests")
    return url


def _swap_database(url: str, name: str) -> str:
    base, _, _ = url.rpartition("/")
    return f"{base}/{name}"


# The test database URL must be in the environment before any application
# module is imported, because Settings is read at import time.
_TEST_URL = _swap_database(_admin_url(), TEST_DB_NAME)
os.environ["DATABASE_URL"] = _TEST_URL
os.environ.setdefault("SMS_ENABLED", "false")
# The limiter keeps per-process state; leaving it on would throttle the suite
# itself. `test_rate_limit.py` turns it back on deliberately for its own case.
os.environ.setdefault("RATE_LIMIT_ENABLED", "false")
# bcrypt at cost 12 takes ~0.4s per hash by design. Test users are created per
# test, so the production cost factor would add minutes to every run; the
# configured production value is asserted in test_auth.py instead.
os.environ.setdefault("BCRYPT_ROUNDS", "4")
# The TestClient speaks http://, and a Secure cookie is not sent over http.
# Production is held to Secure by the hardening validator.
os.environ.setdefault("REFRESH_COOKIE_SECURE", "false")


@pytest.fixture(scope="session", autouse=True)
def _database() -> Iterator[None]:
    """Create and migrate the test database for the whole session."""
    admin = psycopg2.connect(_swap_database(_TEST_URL, "postgres"))
    admin.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    with admin.cursor() as cursor:
        # Evict stragglers (a dev server left pointing at the test database)
        # so the drop cannot fail with ObjectInUse.
        cursor.execute(
            "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
            "WHERE datname = %s AND pid <> pg_backend_pid()",
            (TEST_DB_NAME,),
        )
        cursor.execute(f'DROP DATABASE IF EXISTS "{TEST_DB_NAME}"')
        cursor.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    admin.close()

    from alembic import command
    from alembic.config import Config

    config = Config("alembic.ini")
    command.upgrade(config, "head")

    yield

    from app.core.database import engine

    engine.dispose()


@pytest.fixture
def db() -> Iterator["Session"]:  # noqa: F821 - imported lazily below
    """A session that is rolled back and whose tables are cleared after the test."""
    from app.core.database import SessionLocal, engine
    from sqlalchemy import text

    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        with engine.begin() as connection:
            connection.execute(
                text(
                    "TRUNCATE patients, doctors, symptom_reports, triage_results, "
                    "queue, consultations, sms_logs, analytics, users, refresh_tokens "
                    "RESTART IDENTITY CASCADE"
                )
            )
            connection.execute(text("ALTER SEQUENCE queue_number_seq RESTART WITH 1"))


@pytest.fixture
def make_client(db):
    """Build independent TestClients that share the test's database session.

    Each call returns a *separate* client. Role fixtures must not share one
    instance: they set an Authorization header on it, so a shared client would
    silently run every request as whichever role was resolved last.
    """
    from fastapi.testclient import TestClient

    import main
    from app.core.database import get_db

    main.app.dependency_overrides[get_db] = lambda: db
    created: list[TestClient] = []

    def _build() -> TestClient:
        test_client = TestClient(main.app)
        test_client.__enter__()
        created.append(test_client)
        return test_client

    try:
        yield _build
    finally:
        for test_client in created:
            test_client.__exit__(None, None, None)
        main.app.dependency_overrides.clear()


@pytest.fixture
def anon_client(make_client) -> "TestClient":  # noqa: F821
    """An unauthenticated TestClient whose requests share the test's session."""
    return make_client()


@pytest.fixture
def user_factory(db):
    """Create accounts directly, bypassing HTTP."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    counter = {"n": 0}

    def _create(
        role: "UserRole" = None, password: str = "correct-horse-battery", **extra
    ) -> "User":
        counter["n"] += 1
        role = role or UserRole.ADMIN
        user = User(
            email=extra.pop("email", f"{role.value.lower()}{counter['n']}@kinyamed.rw"),
            hashed_password=hash_password(password),
            full_name=extra.pop("full_name", f"Test {role.value.title()}"),
            role=role,
            **extra,
        )
        db.add(user)
        db.commit()
        return user

    return _create


def _authenticated(test_client, user, password: str = "correct-horse-battery"):
    """Log a user in and attach their bearer token to the client."""
    response = test_client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    test_client.headers["Authorization"] = f"Bearer {token}"
    return test_client


@pytest.fixture
def admin_user(user_factory):
    from app.models.user import UserRole

    return user_factory(UserRole.ADMIN)


@pytest.fixture
def client(make_client, admin_user) -> "TestClient":  # noqa: F821
    """The default client: authenticated as an administrator.

    Most tests exercise behaviour rather than authorisation, so they run with
    full access. Authorisation itself is tested in `test_authorization.py`.
    """
    return _authenticated(make_client(), admin_user)


@pytest.fixture
def doctor_client(make_client, user_factory, db):
    """A client authenticated as a clinician, linked to a Doctor record."""
    from app.models.doctor import Doctor
    from app.models.user import UserRole

    doctor = Doctor(name="Dr Test", email="dr.test@kinyamed.rw")
    db.add(doctor)
    db.commit()
    user = user_factory(UserRole.DOCTOR, doctor_id=doctor.id)
    return _authenticated(make_client(), user)


@pytest.fixture
def patient_client_factory(make_client, user_factory, db):
    """Build a client authenticated as a patient linked to a Patient record."""
    from app.models.patient import Patient
    from app.models.user import UserRole

    def _build(patient_id: int | None = None):
        if patient_id is None:
            patient = Patient(name="Self Patient", phone="+250788700001")
            db.add(patient)
            db.commit()
            patient_id = patient.id
        user = user_factory(UserRole.PATIENT, patient_id=patient_id)
        return _authenticated(make_client(), user), patient_id

    return _build


@pytest.fixture
def patient_factory(client):
    """Register patients through the API."""
    counter = {"n": 0}

    def _create(name: str = "Uwimana", phone: str | None = None, **extra) -> dict:
        counter["n"] += 1
        response = client.post(
            "/api/v1/patients",
            json={
                "name": name,
                "phone": phone or f"078812{counter['n']:04d}",
                **extra,
            },
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _create


@pytest.fixture
def doctor_factory(client):
    counter = {"n": 0}

    def _create(name: str = "Dr Mukamana", **extra) -> dict:
        counter["n"] += 1
        response = client.post(
            "/api/v1/doctors",
            json={"name": name, "email": f"doctor{counter['n']}@kinyamed.rw", **extra},
        )
        assert response.status_code == 201, response.text
        return response.json()

    return _create
