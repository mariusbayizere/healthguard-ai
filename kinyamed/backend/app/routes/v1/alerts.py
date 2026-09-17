"""The alert socket (step 3 of reports/ALERT_DELIVERY_DESIGN.md).

AUTHENTICATION IS THE POINT OF THIS MODULE, as much as delivery is. A doctor's
queue is patient data, and a socket that accepts any connection is an endpoint
without RBAC wearing a different hat -- easier to miss, because nothing here
looks like a route decorator and no dependency runs on its own.

THE TOKEN ARRIVES AS THE FIRST FRAME, NOT IN THE QUERY STRING. A bearer
credential in a URL lands in access logs, proxy logs and browser history. This
project already strips phones out of query strings for that reason
(`core/pii.py`), and a fifteen-minute session token there would undo the point.
The cost is that the socket must be accepted before the caller is known, so the
handler does the minimum until it is: read one frame, verify, or close.

WHAT THE SOCKET SENDS is a notification, not a record: identifiers, urgency and
a masked phone. Never the symptom text. A patient's own words about their body
are the most sensitive field in this system and a socket payload is one more
place for them to end up (L11).
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core import token_blocklist
from app.core.database import SessionLocal
from app.core.pii import mask_phone
from app.core.security import ACCESS_TOKEN, TokenError, decode_token
from app.models.user import User, UserRole
from app.repositories import user_repository
from app.services import alerts

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/alerts", tags=["Alerts"])

# Close codes. 1008 is "policy violation", which is what an unauthenticated or
# unauthorised connection is.
POLICY_VIOLATION = 1008
# A client that connects and says nothing holds a socket open for free.
AUTH_TIMEOUT_SECONDS = 10.0

# Clinical staff, matching the queue endpoints these alerts are about. A
# patient may see their own position; nobody but staff sees the board.
ALLOWED_ROLES = frozenset({UserRole.DOCTOR, UserRole.ADMIN})


def _alert_payload(entry: Any) -> dict[str, Any]:
    """One alert frame. Identifiers and urgency; never the symptom text."""
    patient = entry.triage_result.symptom_report.patient
    return {
        "queue_id": entry.id,
        "queue_number": entry.queue_number,
        "urgency": entry.triage_result.urgency_level.value,
        "status": entry.status.value,
        "patient_name": patient.name,
        "patient_phone": mask_phone(patient.phone) if patient.phone else None,
        "created_at": entry.created_at.isoformat(),
    }


async def _authenticate(socket: WebSocket, db: Session) -> User | None:
    """Read the opening frame and resolve the caller, or close and return None."""
    try:
        frame = await asyncio.wait_for(
            socket.receive_json(), timeout=AUTH_TIMEOUT_SECONDS
        )
    except (TimeoutError, WebSocketDisconnect, ValueError):
        await socket.close(code=POLICY_VIOLATION)
        return None

    if not isinstance(frame, dict) or frame.get("type") != "auth":
        await socket.close(code=POLICY_VIOLATION)
        return None

    try:
        claims = decode_token(str(frame.get("token", "")), expected_type=ACCESS_TOKEN)
    except TokenError:
        await socket.close(code=POLICY_VIOLATION)
        return None

    # The same checks `get_current_user` makes, in the same order. A socket that
    # skipped the blocklist would reopen the window logout closes, and hold it
    # open for the life of the connection.
    if token_blocklist.is_blocked(claims.jti):
        await socket.close(code=POLICY_VIOLATION)
        return None

    user = user_repository.get_by_id(db, claims.subject)
    if user is None or not user.is_active or user.role not in ALLOWED_ROLES:
        logger.info(
            "alert_socket_refused",
            reason="role" if user and user.is_active else "inactive_or_unknown",
            role=user.role.value if user else None,
        )
        await socket.close(code=POLICY_VIOLATION)
        return None

    return user


@router.websocket("/ws")
async def alert_socket(socket: WebSocket) -> None:
    """Deliver outstanding CRITICALs on connect, then accept acknowledgements.

    The backfill is sent BEFORE anything else, so a doctor who has been away
    sees what they missed without having to ask. It is state-derived, so it is
    correct after a disconnection of any length.
    """
    await socket.accept()
    db = SessionLocal()
    user: User | None = None
    try:
        user = await _authenticate(socket, db)
        if user is None:
            return

        outstanding = alerts.outstanding_for(db, user_id=user.id)
        await socket.send_json(
            {
                "type": "ready",
                "outstanding": [_alert_payload(entry) for entry in outstanding],
            }
        )
        logger.info(
            "alert_socket_opened", user_id=user.id, outstanding=len(outstanding)
        )

        while True:
            frame = await socket.receive_json()
            if not isinstance(frame, dict):
                continue
            if frame.get("type") == "ack":
                queue_id = frame.get("queue_id")
                if isinstance(queue_id, int):
                    alerts.acknowledge(db, queue_id=queue_id, user_id=user.id)
                    await socket.send_json({"type": "acked", "queue_id": queue_id})
    except WebSocketDisconnect:
        logger.info("alert_socket_closed", user_id=user.id if user else None)
    finally:
        db.close()
