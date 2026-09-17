"""Requesting and consuming a password-reset code (FR-05-12).

THE WHOLE DESIGN IS SHAPED BY ENUMERATION. `request` must behave identically
for an address that exists and one that does not: same status, same body, and
the same elapsed time. The last is the one that is normally lost, because the
real path hashes a code and writes a row while the absent path returns at once,
and that difference is measurable from the far side of the internet. So the
absent path does the same work and throws it away.

The per-account cap is a separate concern from the IP limiter in middleware and
is not covered by it: an attacker rotates addresses, and the victim here is
chosen by email. Without the cap, anyone who knows an address can make this
service send unlimited SMS to that person's phone, at the project's expense.
Hitting the cap is SILENT for the same enumeration reason: a visible refusal
would confirm the address exists.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.audit_context import AuditContext
from app.core.security import hash_password, verify_password
from app.models.password_reset import PasswordResetCode
from app.models.user import User
from app.repositories import refresh_token_repository, user_repository
from app.services import sms_service
from app.services.audit import record as audit_record

logger = structlog.get_logger(__name__)

CODE_LIFETIME_MINUTES = 10
CODE_DIGITS = 6
MAX_REQUESTS_PER_WINDOW = 3
REQUEST_WINDOW_MINUTES = 60
# Guessing a six-digit code is 1 in a million per try; a handful of tries per
# code keeps that where it belongs without punishing a mistyped digit.
MAX_ATTEMPTS = 5

# A bcrypt digest of a value nobody holds, hashed on the absent-account path so
# it costs what the real path costs. The same trick as the login timing guard.
_DUMMY_CODE = "000000"

# TEST SEAM. Delivery is by SMS; the suite has no carrier, so the plaintext is
# recorded here and nowhere else. It is never written to the database, never
# logged, and never returned by the API -- which is exactly why a test cannot
# read it any other way.
LAST_DELIVERED: dict[str, str] = {}


def _now() -> datetime:
    return datetime.now(UTC)


def _new_code() -> str:
    """A uniformly random six-digit code, leading zeros kept."""
    return f"{secrets.randbelow(10**CODE_DIGITS):0{CODE_DIGITS}d}"


def _recent_request_count(db: Session, user_id: int) -> int:
    since = _now() - timedelta(minutes=REQUEST_WINDOW_MINUTES)
    return (
        db.scalar(
            select(func.count())
            .select_from(PasswordResetCode)
            .where(
                PasswordResetCode.user_id == user_id,
                PasswordResetCode.created_at >= since,
            )
        )
        or 0
    )


def request(db: Session, email: str, *, audit: AuditContext | None = None) -> None:
    """Issue a code if the address is known. Reveals nothing either way.

    Returns None in every case. The caller answers 202 unconditionally.
    """
    user = user_repository.get_by_email(db, email.strip().lower())

    if user is None:
        # Do the same work the real path does, so the two cannot be told apart
        # by timing, then discard it.
        hash_password(_DUMMY_CODE)
        logger.info("password_reset_requested", outcome="unknown_address")
        return

    if _recent_request_count(db, user.id) >= MAX_REQUESTS_PER_WINDOW:
        # Silent: a visible refusal would confirm the address exists. Still
        # hash, so the capped path costs what the uncapped one costs.
        hash_password(_DUMMY_CODE)
        logger.warning(
            "password_reset_rate_limited",
            user_id=user.id,
            window_minutes=REQUEST_WINDOW_MINUTES,
        )
        return

    code = _new_code()
    issued = PasswordResetCode(
        user_id=user.id,
        code_hash=hash_password(code),
        expires_at=_now() + timedelta(minutes=CODE_LIFETIME_MINUTES),
    )
    db.add(issued)
    db.flush()
    if audit is not None:
        # actor is None deliberately. This endpoint needs no credentials, so
        # the requester is NOT known to be the account holder -- attributing it
        # to them would record a claim we cannot support, and an attacker
        # requesting a reset would appear in the log as the victim. The address
        # we do know is recorded instead.
        audit_record(
            db,
            action="REQUEST_PASSWORD_RESET",
            table_name="password_reset_codes",
            record_id=issued.id,
            after={"user_id": user.id, "expires_at": issued.expires_at},
            actor=None,
            ip_address=audit.ip_address,
            user_agent=audit.user_agent,
        )
    db.commit()

    LAST_DELIVERED[user.email] = code
    _deliver(db, user, code)
    # The code is never a log field. Nor is the address.
    logger.info("password_reset_requested", outcome="issued", user_id=user.id)


def _deliver(db: Session, user: User, code: str) -> None:
    """Send the code to the account's phone, if it has one.

    A staff account has no patient record and therefore no phone here; that is
    a real gap and it is recorded rather than papered over, because inventing a
    delivery channel would be worse than naming the one that is missing.
    """
    if user.patient_id is None:
        logger.warning(
            "password_reset_undeliverable",
            user_id=user.id,
            reason="account has no phone on record",
            effect="the code was issued and cannot reach anyone",
        )
        return
    patient = user.patient
    if patient is None or not patient.phone:
        logger.warning("password_reset_undeliverable", user_id=user.id)
        return
    sms_service.send_sms(
        db,
        patient_id=patient.id,
        phone=patient.phone,
        message=(
            f"KinyaMed: your password reset code is {code}. "
            f"It expires in {CODE_LIFETIME_MINUTES} minutes. "
            "If you did not ask for it, ignore this message."
        ),
    )


def consume(
    db: Session,
    *,
    email: str,
    code: str,
    new_password: str,
    audit: AuditContext | None = None,
) -> bool:
    """Spend a code and set the new password. False if it is not usable.

    One return value for every failure -- unknown address, wrong code, expired,
    already spent, too many attempts -- because distinguishing them tells a
    caller which part they got right.
    """
    user = user_repository.get_by_email(db, email.strip().lower())
    if user is None:
        verify_password(code, "$2b$12$" + "." * 53)
        return False

    record = db.scalars(
        select(PasswordResetCode)
        .where(PasswordResetCode.user_id == user.id)
        .order_by(PasswordResetCode.created_at.desc())
    ).first()
    if record is None:
        verify_password(code, "$2b$12$" + "." * 53)
        return False

    if not record.is_live() or record.attempts >= MAX_ATTEMPTS:
        return False

    record.attempts += 1
    if not verify_password(code, record.code_hash):
        db.commit()
        logger.info("password_reset_failed", user_id=user.id, reason="wrong_code")
        return False

    record.consumed_at = _now()
    user_repository.update(
        db, user, commit=False, hashed_password=hash_password(new_password)
    )
    # A reset is what someone does when they fear the account is compromised,
    # so every existing session ends with it.
    refresh_token_repository.revoke_all_for_user(db, user.id, commit=False)
    if audit is not None:
        # Attributed to the user here, unlike the request: possession of the
        # code was proved, which is the only evidence this flow can offer.
        audit_record(
            db,
            action="COMPLETE_PASSWORD_RESET",
            table_name="users",
            record_id=user.id,
            after={"user_id": user.id, "sessions_ended": True},
            actor=user,
            ip_address=audit.ip_address,
            user_agent=audit.user_agent,
        )
    db.commit()
    logger.info("password_reset_completed", user_id=user.id)
    return True
