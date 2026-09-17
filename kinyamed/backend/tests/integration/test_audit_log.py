"""Every state-changing operation leaves exactly one audit row (FR-03-09, L11).

WHY THIS FILE IS SHAPED LIKE THIS. The requirement is not "there is an audit
table" but "nothing changes state without being recorded". A test that audits
three endpoints it happens to know about proves nothing about the fourth, and
the fourth is the one somebody adds next month.

So the completeness test enumerates the application's own route table. Adding a
POST, PATCH, PUT or DELETE without either exercising it here or exempting it
with a written reason fails the suite. That is the only form of this test that
keeps working as the API grows.

The audit row is written inside the same transaction as the change it records,
so a rolled-back operation leaves no row claiming it happened.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

# Routes that change no state the audit log is accountable for. Each needs a
# reason, not a shrug. Empty today: every state-changing route is exercised.
EXEMPT: dict[str, str] = {}


def _state_changing_routes() -> set[str]:
    """Every POST/PATCH/PUT/DELETE the application serves, as 'METHOD /path'."""
    import main

    found = set()
    for route in main.app.routes:
        for method in sorted(getattr(route, "methods", set()) or set()):
            if method in {"POST", "PATCH", "PUT", "DELETE"}:
                found.add(f"{method} {route.path}")
    return found


# ── Scenarios ────────────────────────────────────────────────────────────
# Each returns the response of exactly one state-changing call. Set-up calls
# inside a scenario are made through `ctx.setup`, which is not counted.


class Ctx:
    """Fixtures a scenario may use, plus a non-counting set-up client."""

    def __init__(self, client, anon_client, patient_factory, doctor_factory, db):
        self.client = client
        self.anon_client = anon_client
        self.patient_factory = patient_factory
        self.doctor_factory = doctor_factory
        self.db = db
        self._made = 0

    def a_patient(self) -> dict:
        return self.patient_factory()

    def a_doctor(self) -> dict:
        return self.doctor_factory()

    def a_queue_entry(self) -> dict:
        patient = self.a_patient()
        response = self.client.post(
            "/api/v1/triage",
            json={"patient_id": patient["id"], "symptoms_input": "mfite umuriro"},
        )
        assert response.status_code == 201, response.text
        return response.json()

    def a_user(self) -> dict:
        self._made += 1
        response = self.client.post(
            "/api/v1/users",
            json={
                "email": f"audited.user{self._made}@kinyamed.rw",
                "password": "Correct-Horse9-battery",
                "confirm_password": "Correct-Horse9-battery",
                "first_name": "Audited",
                "last_name": "User",
                "role": "DOCTOR",
            },
        )
        assert response.status_code in (200, 201), response.text
        return response.json()

    def a_snapshot(self) -> dict:
        response = self.client.post("/api/v1/analytics/daily/snapshot")
        assert response.status_code in (200, 201), response.text
        return response.json()

    def a_registered_email(self) -> str:
        self._made += 1
        email = f"signer{self._made}@kinyamed.rw"
        response = self.anon_client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "Correct-Horse9-battery",
                "confirm_password": "Correct-Horse9-battery",
                "first_name": "Sign",
                "last_name": "Er",
                "phone": f"07889911{self._made:02d}",
            },
        )
        assert response.status_code in (200, 201), response.text
        return email

    def a_reset_code(self) -> tuple[str, str]:
        """An address with a live reset code, and the code itself."""
        from app.services import password_reset

        email = self.a_registered_email()
        response = self.anon_client.post(
            "/api/v1/auth/password-reset/request", json={"email": email}
        )
        assert response.status_code == 202, response.text
        return email, password_reset.LAST_DELIVERED[email]

    def a_signed_in_client(self):
        """A client holding a live session: the counted call is the only change."""
        email = self.a_registered_email()
        login = self.anon_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "Correct-Horse9-battery"},
        )
        assert login.status_code == 200, login.text
        self.anon_client.headers["Authorization"] = (
            f"Bearer {login.json()['access_token']}"
        )
        return self.anon_client


# Each entry takes the context, performs any set-up, and returns a zero-argument
# callable that makes exactly ONE state-changing request. Only that call is
# counted: set-up writes audit rows of its own, and counting those would let a
# missing row hide behind a present one.
SCENARIOS: dict[str, Callable[[Ctx], Callable[[], Any]]] = {
    "POST /api/v1/patients": lambda c: (
        lambda: c.client.post(
            "/api/v1/patients", json={"name": "Audited", "phone": "0788990011"}
        )
    ),
    "PATCH /api/v1/patients/{patient_id}": lambda c: (
        lambda pid=c.a_patient()["id"]: c.client.patch(
            f"/api/v1/patients/{pid}", json={"name": "Renamed"}
        )
    ),
    "DELETE /api/v1/patients/{patient_id}": lambda c: (
        lambda pid=c.a_patient()["id"]: c.client.delete(f"/api/v1/patients/{pid}")
    ),
    "POST /api/v1/doctors": lambda c: (
        lambda: c.client.post(
            "/api/v1/doctors",
            json={"name": "Dr Audited", "email": "audited@kinyamed.rw"},
        )
    ),
    "PATCH /api/v1/doctors/{doctor_id}": lambda c: (
        lambda did=c.a_doctor()["id"]: c.client.patch(
            f"/api/v1/doctors/{did}", json={"specialty": "Paediatrics"}
        )
    ),
    "PATCH /api/v1/doctors/{doctor_id}/toggle-duty": lambda c: (
        lambda did=c.a_doctor()["id"]: c.client.patch(
            f"/api/v1/doctors/{did}/toggle-duty"
        )
    ),
    "DELETE /api/v1/doctors/{doctor_id}": lambda c: (
        lambda did=c.a_doctor()["id"]: c.client.delete(f"/api/v1/doctors/{did}")
    ),
    "POST /api/v1/triage": lambda c: (
        lambda pid=c.a_patient()["id"]: c.client.post(
            "/api/v1/triage",
            json={"patient_id": pid, "symptoms_input": "mfite umuriro"},
        )
    ),
    "PATCH /api/v1/queue/{queue_id}/status": lambda c: (
        lambda qid=c.a_queue_entry()["queue_id"]: c.client.patch(
            f"/api/v1/queue/{qid}/status", json={"status": "IN_PROGRESS"}
        )
    ),
    "PATCH /api/v1/queue/{queue_id}/assign-doctor": lambda c: (
        lambda qid=c.a_queue_entry()["queue_id"], did=c.a_doctor()["id"]: (
            c.client.patch(
                f"/api/v1/queue/{qid}/assign-doctor", json={"doctor_id": did}
            )
        )
    ),
    "DELETE /api/v1/queue/{queue_id}": lambda c: (
        lambda qid=c.a_queue_entry()["queue_id"]: c.client.delete(
            f"/api/v1/queue/{qid}"
        )
    ),
    "POST /api/v1/users": lambda c: (
        lambda: c.client.post(
            "/api/v1/users",
            json={
                "email": "made@kinyamed.rw",
                "password": "Correct-Horse9-battery",
                "confirm_password": "Correct-Horse9-battery",
                "first_name": "Made",
                "last_name": "Staff",
                "role": "DOCTOR",
            },
        )
    ),
    "PATCH /api/v1/users/{user_id}/deactivate": lambda c: (
        lambda uid=c.a_user()["id"]: c.client.patch(f"/api/v1/users/{uid}/deactivate")
    ),
    "PATCH /api/v1/users/{user_id}/activate": lambda c: (
        lambda uid=c.a_user()["id"]: c.client.patch(f"/api/v1/users/{uid}/activate")
    ),
    "POST /api/v1/analytics/daily/snapshot": lambda c: (
        lambda: c.client.post("/api/v1/analytics/daily/snapshot")
    ),
    "DELETE /api/v1/analytics/daily": lambda c: (
        lambda: c.client.delete("/api/v1/analytics/daily?confirm=CLEAR_ALL")
    ),
    "DELETE /api/v1/analytics/daily/{snapshot_date}": lambda c: (
        lambda day=c.a_snapshot()["snapshot_date"]: c.client.delete(
            f"/api/v1/analytics/daily/{day}"
        )
    ),
    "POST /api/v1/auth/register": lambda c: (
        lambda: c.anon_client.post(
            "/api/v1/auth/register",
            json={
                "email": "newcomer@kinyamed.rw",
                "password": "Correct-Horse9-battery",
                "confirm_password": "Correct-Horse9-battery",
                "first_name": "New",
                "last_name": "Comer",
                "phone": "0788990022",
            },
        )
    ),
    "POST /api/v1/auth/login": lambda c: (
        lambda email=c.a_registered_email(): c.anon_client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "Correct-Horse9-battery"},
        )
    ),
    "POST /api/v1/auth/refresh": lambda c: (
        lambda cl=c.a_signed_in_client(): cl.post("/api/v1/auth/refresh")
    ),
    "POST /api/v1/auth/logout": lambda c: (
        lambda cl=c.a_signed_in_client(): cl.post("/api/v1/auth/logout")
    ),
    "POST /api/v1/auth/logout-all": lambda c: (
        lambda cl=c.a_signed_in_client(): cl.post("/api/v1/auth/logout-all")
    ),
    "POST /api/v1/auth/password-reset/request": lambda c: (
        lambda email=c.a_registered_email(): c.anon_client.post(
            "/api/v1/auth/password-reset/request", json={"email": email}
        )
    ),
    "POST /api/v1/auth/password-reset/confirm": lambda c: (
        lambda pair=c.a_reset_code(): c.anon_client.post(
            "/api/v1/auth/password-reset/confirm",
            json={
                "email": pair[0],
                "code": pair[1],
                "new_password": "Reset-Horse9-New",
            },
        )
    ),
    "POST /api/v1/auth/change-password": lambda c: (
        lambda: c.client.post(
            "/api/v1/auth/change-password",
            json={
                "current_password": "Correct-Horse9-battery",
                "new_password": "Another-Correct-Horse9",
            },
        )
    ),
}


@pytest.fixture
def ctx(client, anon_client, patient_factory, doctor_factory, db) -> Ctx:
    return Ctx(client, anon_client, patient_factory, doctor_factory, db)


def _audit_count(db) -> int:
    from app.models.audit_log import AuditLog
    from sqlalchemy import func, select

    db.expire_all()
    return db.scalar(select(func.count()).select_from(AuditLog)) or 0


# ── The completeness test ────────────────────────────────────────────────


def test_every_state_changing_route_is_covered_or_exempt() -> None:
    """A new POST/PATCH/PUT/DELETE must be audited or exempted, deliberately."""
    routes = _state_changing_routes()
    covered = set(SCENARIOS) | set(EXEMPT)

    uncovered = sorted(routes - covered)
    assert not uncovered, (
        "these state-changing routes are neither exercised here nor exempt, so "
        "nothing proves they write an audit row: " + ", ".join(uncovered)
    )

    stale = sorted(covered - routes)
    assert not stale, (
        "these entries name routes the application no longer serves: "
        + ", ".join(stale)
    )


@pytest.mark.parametrize("route", sorted(SCENARIOS))
def test_each_state_change_writes_exactly_one_audit_row(route, ctx, db) -> None:
    """Exactly one, not at least one: a duplicated write is also a defect."""
    act = SCENARIOS[route](ctx)  # set-up happens here and is not counted
    before = _audit_count(db)
    response = act()
    assert response.status_code < 400, f"{route} failed to run: {response.text}"

    after = _audit_count(db)
    assert after == before + 1, (
        f"{route} produced {after - before} audit rows, expected exactly 1"
    )


# ── Content of the row ───────────────────────────────────────────────────


def test_the_row_identifies_the_actor_and_the_target(ctx, db, admin_user) -> None:
    from app.models.audit_log import AuditLog
    from sqlalchemy import select

    doctor = ctx.client.post(
        "/api/v1/doctors", json={"name": "Dr Traced", "email": "traced@kinyamed.rw"}
    ).json()

    row = db.scalars(select(AuditLog).order_by(AuditLog.id.desc())).first()
    assert row is not None, "no audit row was written"
    assert row.user_id == admin_user.id
    assert row.user_role == "ADMIN"
    assert row.action == "CREATE_DOCTOR"
    assert row.table_name == "doctors"
    assert row.record_id == doctor["id"]
    assert row.after_value is not None
    assert row.before_value is None, "a creation has no before state"


def test_an_update_records_before_and_after(ctx, db) -> None:
    from app.models.audit_log import AuditLog
    from sqlalchemy import select

    doctor = ctx.a_doctor()
    ctx.client.patch(
        f"/api/v1/doctors/{doctor['id']}", json={"specialty": "Cardiology"}
    )

    row = db.scalars(select(AuditLog).order_by(AuditLog.id.desc())).first()
    assert row is not None
    assert row.action == "UPDATE_DOCTOR"
    assert row.before_value is not None and row.after_value is not None
    assert row.after_value.get("specialty") == "Cardiology"
    assert row.before_value.get("specialty") != "Cardiology"


# ── The privacy invariant (L11) ──────────────────────────────────────────


def test_payloads_carry_no_raw_phone_or_name(ctx, db) -> None:
    """The JSONB payloads are scrubbed before they are written.

    CLAUDE.md §8.2 permits the dedicated actor-name column and nothing else: a
    raw phone or personal name inside before_value/after_value is a PII leak
    into permanent storage, which is worse than one into a rotating log.
    """
    import json
    import re

    from app.models.audit_log import AuditLog
    from sqlalchemy import select

    phone = "0788445566"
    name = "Mukandayisenga"
    ctx.client.post("/api/v1/patients", json={"name": name, "phone": phone})

    rows = db.scalars(select(AuditLog)).all()
    assert rows, "nothing was audited, so this scan proved nothing"

    payloads = json.dumps(
        [[row.before_value, row.after_value] for row in rows], default=str
    )
    assert name not in payloads, f"a personal name reached an audit payload: {name}"
    assert phone not in payloads, f"a raw phone reached an audit payload: {phone}"
    assert not re.search(r"(?<![\w*+])\+?\d(?:[ \-]?\d){8,14}(?!\w)", payloads), (
        "a phone-shaped digit run reached an audit payload"
    )


def test_a_password_never_reaches_an_audit_payload(ctx, db) -> None:
    import json

    from app.models.audit_log import AuditLog
    from sqlalchemy import select

    secret = "Correct-Horse9-battery"
    ctx.client.post(
        "/api/v1/users",
        json={"email": "pw@kinyamed.rw", "password": secret, "role": "DOCTOR"},
    )

    rows = db.scalars(select(AuditLog)).all()
    payloads = json.dumps(
        [[row.before_value, row.after_value] for row in rows], default=str
    )
    assert secret not in payloads
    assert "hashed_password" not in payloads, (
        "the digest is as sensitive as the password and must not be copied"
    )


# ── Atomicity ────────────────────────────────────────────────────────────


def test_a_rejected_operation_writes_no_audit_row(ctx, db) -> None:
    """A row is written in the change's transaction, not beside it."""
    doctor = ctx.a_doctor()
    before = _audit_count(db)

    conflict = ctx.client.post(
        "/api/v1/doctors", json={"name": "Clash", "email": doctor["email"]}
    )
    assert conflict.status_code == 409

    assert _audit_count(db) == before, (
        "a rejected write left an audit row claiming it happened"
    )
