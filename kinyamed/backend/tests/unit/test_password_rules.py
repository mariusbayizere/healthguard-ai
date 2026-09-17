"""Password composition rules (FR-05-11).

Until 2026-09-17 the only rule was length, so `aaaaaaaaaaaa` was a valid
password: twelve characters, one distinct letter, and nothing to stop it.

A NOTE ON THE LENGTH FLOOR. FR-05-11 says eight characters; this code requires
twelve and keeps doing so. The specification is a floor, not a target, and
lowering a limit that already holds in order to match a document would weaken a
live gate for no gain. The character-class rules are what was missing.

ERRORS NAME THE RULE THAT FAILED, and all of them at once. "Password is not
valid" teaches nobody anything, and reporting one failure per attempt turns a
single fix into four round trips.
"""

from __future__ import annotations

import pytest
from app.schemas.auth import PasswordChangeRequest, RegisterRequest, UserCreate
from pydantic import ValidationError

VALID = "Correct-Horse9"


def _register(password: str) -> None:
    RegisterRequest(
        email="someone@kinyamed.rw",
        password=password,
        full_name="Some One",
        phone="0788123456",
    )


def _message(password: str) -> str:
    with pytest.raises(ValidationError) as raised:
        _register(password)
    return str(raised.value)


# ── The case that prompted this ──────────────────────────────────────────


def test_a_single_repeated_letter_is_rejected() -> None:
    """The password the old length-only rule accepted."""
    with pytest.raises(ValidationError):
        _register("aaaaaaaaaaaa")


# ── Each rule, and the message that names it ─────────────────────────────


@pytest.mark.parametrize(
    ("password", "rule"),
    [
        ("correct-horse9", "uppercase"),
        ("CORRECT-HORSE9", "lowercase"),
        ("Correct-Horses", "digit"),
        ("CorrectHorse999", "special"),
    ],
)
def test_each_missing_class_is_rejected_and_named(password: str, rule: str) -> None:
    assert rule in _message(password).lower()


def test_every_broken_rule_is_reported_at_once() -> None:
    """One attempt, the whole list: four round trips is not a user experience."""
    message = _message("aaaaaaaaaaaa").lower()
    for rule in ("uppercase", "digit", "special"):
        assert rule in message, f"{rule} was not reported: {message}"


def test_a_compliant_password_is_accepted() -> None:
    _register(VALID)


# ── The limits that already held must keep holding ───────────────────────


def test_the_twelve_character_floor_is_not_lowered() -> None:
    """FR-05-11 says eight; this code says twelve and keeps saying twelve."""
    with pytest.raises(ValidationError):
        _register("Ab3-cdefghi")  # 11 characters, every class present
    _register("Ab3-cdefghij")  # 12


def test_the_bcrypt_input_limit_still_applies() -> None:
    """bcrypt truncates silently past 72 bytes; the schema refuses instead."""
    with pytest.raises(ValidationError):
        _register("Ab3-" + "x" * 80)


# ── The rules apply wherever a password is set ───────────────────────────


def test_an_administrator_cannot_create_an_account_with_a_weak_password() -> None:
    with pytest.raises(ValidationError):
        UserCreate(
            email="staff@kinyamed.rw",
            password="aaaaaaaaaaaa",
            full_name="Staff Member",
            role="DOCTOR",
        )


def test_a_password_change_cannot_move_to_a_weak_password() -> None:
    with pytest.raises(ValidationError):
        PasswordChangeRequest(
            current_password="whatever-it-was", new_password="aaaaaaaaaaaa"
        )


def test_the_current_password_field_is_not_composition_checked() -> None:
    """It is a credential being verified, not a new password being set.

    Applying the new rules here would lock out anyone whose existing password
    predates them, which is the opposite of the intent.
    """
    PasswordChangeRequest(current_password="short", new_password=VALID)
