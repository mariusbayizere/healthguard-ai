"""Writing audit rows (FR-03-09, L11).

One function, `record`, called by the service that performs the change, inside
that change's transaction. It is deliberately not middleware: middleware sees a
request and a status code, not which row moved from what to what, and an audit
trail whose entries say "PATCH /api/v1/doctors/3 -> 200" answers none of the
questions an audit is for.

`commit=False` matches the repository convention: the caller owns the
transaction boundary, so a rolled-back change takes its audit row with it.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.core.pii import scrub_payload
from app.models.audit_log import AuditLog
from app.models.base import TimestampedModel
from app.models.user import User

# Columns copied from no model, ever. A digest is as sensitive as the secret it
# stands for, and a token identifier lets a reader correlate sessions.
NEVER_COPIED = frozenset({"hashed_password", "password", "jti", "token"})


def snapshot(instance: TimestampedModel | None) -> dict[str, Any] | None:
    """A plain-dict view of a row, minus the columns that must never be copied.

    Taken before and after a change so the audit row carries the transition
    rather than only its endpoint. Scrubbing happens in `record`, once, so a
    caller cannot forget it.
    """
    if instance is None:
        return None
    mapper = instance.__class__.__mapper__
    return {
        column.key: getattr(instance, column.key)
        for column in mapper.column_attrs
        if column.key not in NEVER_COPIED
    }


def record(
    db: Session,
    *,
    action: str,
    table_name: str,
    record_id: int | None = None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    actor: User | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    commit: bool = False,
) -> AuditLog:
    """Append one audit row. The caller commits.

    `before` and `after` are scrubbed here rather than at the call site, for the
    same reason phones are masked in one structlog processor: a call site that
    forgets is how personal data reaches permanent storage.
    """
    entry = AuditLog(
        user_id=actor.id if actor else None,
        user_name=actor.full_name if actor else None,
        user_role=actor.role.value if actor else None,
        action=action,
        table_name=table_name,
        record_id=record_id,
        before_value=scrub_payload(before),
        after_value=scrub_payload(after),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(entry)
    if commit:
        db.commit()
    else:
        # Flush so the row participates in the caller's transaction and its id
        # is available, without ending that transaction.
        db.flush()
    return entry
