"""The sign-in form posts the fields the API requires.

THE BUG THIS EXISTS FOR. `useLogin` sent `{username, password}` while
`LoginRequest` requires `email: EmailStr`. FastAPI rejected every attempt with
422 before any credential was checked, so the sign-in page could not work at
all -- and it shipped that way, with the field labelled "Username" in the UI.

Nothing caught it, and the reason is worth stating: the frontend component
tests never cross the network, and the backend tests construct their own
payloads from the schema. Both sides were green about a contract neither of
them tested. That is the same gap AUDIT 3.1 describes -- `schema.gen.ts` is
still not generated, so the hand-written client is free to drift from the
server it talks to.

Generating the client is the real fix. Until that lands, this reads the
mutation's payload type out of the TypeScript source and compares it to the
Pydantic model, which is cheap and would have caught this on day one.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from app.models.queue import QueueStatus
from app.models.triage_result import UrgencyLevel
from app.schemas.auth import LoginRequest

HOOKS = (
    Path(__file__).resolve().parents[2].parent / "frontend" / "src" / "api" / "hooks.ts"
)

# `mutationFn: async (input: { email: string; password: string }) => {`
# Captured rather than imported: there is no TypeScript runtime here, and
# adding one to check four characters would be its own kind of mistake.
_LOGIN_INPUT = re.compile(
    r"export function useLogin\(\).*?mutationFn:\s*async\s*\(\s*input:\s*\{([^}]*)\}",
    re.DOTALL,
)


def _frontend_login_fields() -> set[str]:
    source = HOOKS.read_text(encoding="utf-8")
    match = _LOGIN_INPUT.search(source)
    assert match, (
        "could not find useLogin's payload type in hooks.ts. If the shape of "
        "that function changed, update this regex -- do not delete the test."
    )
    # "email: string; password: string" -> {"email", "password"}
    return {
        part.split(":")[0].strip()
        for part in match.group(1).split(";")
        if part.strip() and not part.strip().startswith("//")
    }


def _required_api_fields() -> set[str]:
    return {
        name for name, field in LoginRequest.model_fields.items() if field.is_required()
    }


@pytest.mark.skipif(not HOOKS.exists(), reason="frontend package absent")
def test_the_form_sends_every_field_the_api_requires() -> None:
    sent = _frontend_login_fields()
    required = _required_api_fields()

    missing = required - sent
    assert not missing, (
        f"the sign-in form does not send {sorted(missing)}, which LoginRequest "
        f"requires. Every sign-in attempt will be rejected 422 before the "
        f"password is checked. The form sends {sorted(sent)}."
    )


@pytest.mark.skipif(not HOOKS.exists(), reason="frontend package absent")
def test_the_form_sends_nothing_the_api_will_not_accept() -> None:
    """An extra field is not fatal, but it means one side has moved.

    `username` sat in this payload for the life of the feature. Nobody looked,
    because nothing failed loudly -- the server ignored what it did not know
    and rejected the request for what was absent instead.
    """
    sent = _frontend_login_fields()
    known = set(LoginRequest.model_fields)

    unknown = sent - known
    assert not unknown, (
        f"the sign-in form sends {sorted(unknown)}, which LoginRequest does not "
        f"declare. It accepts {sorted(known)}."
    )


def test_login_is_addressed_by_email_not_username() -> None:
    """Pin the direction, not just the agreement.

    Renaming the Pydantic field to `username` would make the two tests above
    pass and would still be wrong: the User model stores `email`, and the
    account a clinician is given is an email address.
    """
    assert "email" in _required_api_fields()
    assert "username" not in LoginRequest.model_fields


# ── Enums the client mirrors by hand ────────────────────────────────────────
#
# The SECOND contract bug this file was extended for. The frontend's
# QueueStatus union said "COMPLETED" while the server enum has always said
# "DONE", so `PATCH /queue/{id}/status` was rejected 422 and the Done button on
# the doctor board had never worked once. Identical in shape to the
# username/email bug: a hand-written union drifting from a server enum that
# nothing compared it against.

TYPES = (
    Path(__file__).resolve().parents[2].parent / "frontend" / "src" / "api" / "types.ts"
)


def _union_members(source: str, name: str) -> set[str]:
    """Read the string members of `export type <name> = "A" | "B";`.

    Tolerates the declaration spanning lines, which is how both of these are
    actually written.
    """
    match = re.search(rf"export type {name}\s*=\s*(.*?);", source, re.DOTALL)
    assert match, f"could not find `export type {name}` in types.ts"
    return set(re.findall(r'"([^"]+)"', match.group(1)))


@pytest.mark.skipif(not TYPES.exists(), reason="frontend package absent")
def test_queue_status_union_matches_the_server_enum() -> None:
    declared = _union_members(TYPES.read_text(encoding="utf-8"), "QueueStatus")
    server = {member.value for member in QueueStatus}
    assert declared == server, (
        f"QueueStatus has drifted. The client declares {sorted(declared)}; the "
        f"server accepts {sorted(server)}. A status the server does not know is "
        "rejected 422 at the moment a clinician taps the button."
    )


@pytest.mark.skipif(not TYPES.exists(), reason="frontend package absent")
def test_urgency_union_matches_the_server_enum() -> None:
    """The urgency ordering is generated, but the NAMES are still written twice.

    `urgency.gen.ts` is generated from the enum, so this should never fail --
    which is exactly why it is cheap to assert.
    """
    source = (TYPES.parent / "urgency.gen.ts").read_text(encoding="utf-8")
    declared = set(re.findall(r'"([A-Z]+)"', source))
    assert declared == {member.value for member in UrgencyLevel}
