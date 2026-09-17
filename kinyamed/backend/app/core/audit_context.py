"""Who is acting, and from where, for the audit trail.

A route already knows the caller; what it lacks is the request metadata an
audit row needs. Bundling both in one dependency keeps the service signature
honest — `create_doctor(db, data, audit)` says it records something — without
each route reaching into `Request` for itself.

The IP comes from `client_ip`, which owns the X-Forwarded-For trust boundary.
Reading the header here instead would reopen a spoof that was already closed
once.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request

from app.core.middleware import client_ip
from app.models.user import User

# A user agent is attacker-controlled free text; it is stored for forensics and
# truncated so it cannot be used to bloat the table.
MAX_USER_AGENT = 512


@dataclass(frozen=True)
class AuditContext:
    """The actor and the request they acted through."""

    actor: User | None
    ip_address: str | None
    user_agent: str | None

    def acting_as(self, actor: User | None) -> AuditContext:
        """The same request, attributed to a specific user.

        Used where the actor is resolved by the service rather than by a
        dependency, such as a login, whose subject is not known until the
        credentials have been checked.
        """
        return AuditContext(
            actor=actor, ip_address=self.ip_address, user_agent=self.user_agent
        )


def get_audit_context(request: Request) -> AuditContext:
    """Request metadata with no actor; routes attach the caller themselves.

    Deliberately not depending on `get_current_user`: this must also resolve on
    anonymous and pre-authentication routes, where requiring a token would turn
    a 401 into a 500.
    """
    agent = request.headers.get("User-Agent")
    return AuditContext(
        actor=None,
        ip_address=client_ip(request),
        user_agent=agent[:MAX_USER_AGENT] if agent else None,
    )


AuditCtx = Annotated[AuditContext, Depends(get_audit_context)]
