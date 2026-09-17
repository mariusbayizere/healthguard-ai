"""What a doctor is owed, and who is there to receive it.

Step 2 of reports/ALERT_DELIVERY_DESIGN.md. Deliberately free of Kafka and
WebSocket imports: the safety property -- a doctor who drops does not miss a
CRITICAL -- lives entirely in these queries, and a transport added later cannot
make them correct or incorrect.

BOUNDED BY STATE, NOT BY TIME. `outstanding_for` has no "since" clause and must
not acquire one. A CRITICAL still waiting after a week is still an emergency; a
time window would suppress exactly the row that matters most. A test asserts the
absence, because "we deliberately did not add a filter" is the kind of decision
that gets undone by somebody optimising a query.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.alert_ack import QueueAlertAcknowledgement
from app.models.doctor import Doctor
from app.models.queue import ACTIVE_STATUSES, Queue
from app.models.triage_result import TriageResult, UrgencyLevel
from app.models.user import User, UserRole

logger = structlog.get_logger(__name__)


def _now() -> datetime:
    return datetime.now(UTC)


def outstanding_for(db: Session, *, user_id: int) -> Sequence[Queue]:
    """Every CRITICAL this doctor has not acknowledged and that is still live.

    This is the reconnect backfill. It answers from current state rather than
    from a message log, so it is correct after an outage of any length and
    after any amount of Kafka downtime.
    """
    acknowledged = (
        select(QueueAlertAcknowledgement.queue_id)
        .where(QueueAlertAcknowledgement.user_id == user_id)
        .scalar_subquery()
    )
    return db.scalars(
        select(Queue)
        .join(TriageResult, TriageResult.id == Queue.triage_result_id)
        .where(
            TriageResult.urgency_level == UrgencyLevel.CRITICAL,
            Queue.status.in_(ACTIVE_STATUSES),
            Queue.id.not_in(acknowledged),
        )
        .order_by(Queue.created_at.asc())
    ).all()


def acknowledge(db: Session, *, queue_id: int, user_id: int) -> None:
    """Record that this alert reached this doctor.

    Idempotent: a reconnect may re-send an alert the client already showed, and
    acknowledging twice is not a second fact. ON CONFLICT DO NOTHING rather
    than a read-then-write, so two dashboards racing cannot raise.

    IT DOES NOT TOUCH `queue`. Nothing in this function may ever change the
    clinical record; see the module docstring of app/models/alert_ack.py.
    """
    db.execute(
        insert(QueueAlertAcknowledgement)
        .values(queue_id=queue_id, user_id=user_id, acknowledged_at=_now())
        .on_conflict_do_nothing(constraint="uq_alert_ack_queue_user")
    )
    db.commit()


def acknowledged_and_still_waiting(
    db: Session, *, longer_than: timedelta
) -> Sequence[Queue]:
    """CRITICALs somebody acknowledged that are STILL waiting after `longer_than`.

    A MEASUREMENT, NOT AN ALARM. Nothing calls this on a timer, nothing
    escalates from it, and `longer_than` has no default: an interval baked in
    here would become policy by accident, and whether such a case should
    re-alert -- and after how long -- is a clinical judgement nobody on this
    project is qualified to make. The query exists so that question can be
    answered from data rather than from intuition.
    """
    cutoff = _now() - longer_than
    acknowledged = (
        select(QueueAlertAcknowledgement.queue_id).distinct().scalar_subquery()
    )
    return db.scalars(
        select(Queue)
        .join(TriageResult, TriageResult.id == Queue.triage_result_id)
        .where(
            TriageResult.urgency_level == UrgencyLevel.CRITICAL,
            Queue.status.in_(ACTIVE_STATUSES),
            Queue.id.in_(acknowledged),
            Queue.created_at <= cutoff,
        )
        .order_by(Queue.created_at.asc())
    ).all()


@dataclass(frozen=True)
class BroadcastAudience:
    """Who a fan-out would reach, and whether that is nobody."""

    count: int

    @property
    def reached_nobody(self) -> bool:
        return self.count == 0


def recipients_for_broadcast(db: Session) -> BroadcastAudience:
    """How many on-duty clinicians a CRITICAL alert would reach.

    FANNING OUT TO ZERO MUST NOT LOOK LIKE DELIVERING. With no doctor on duty a
    CRITICAL alert reaches nobody, and a push that quietly succeeds at
    delivering to an empty set is indistinguishable from one that worked. The
    caller logs the warning; this reports the fact.

    The alert is not lost when this happens -- it stays outstanding and the next
    doctor to connect receives it from `outstanding_for`. What is lost is the
    real-time part, which is precisely the thing worth being told about.
    """
    count = (
        db.scalar(
            select(func.count())
            .select_from(User)
            .join(Doctor, Doctor.id == User.doctor_id)
            .where(
                User.role == UserRole.DOCTOR,
                User.is_active.is_(True),
                Doctor.is_on_duty.is_(True),
            )
        )
        or 0
    )
    return BroadcastAudience(count=count)


def warn_if_unattended(db: Session, *, queue_id: int) -> BroadcastAudience:
    """Report the audience for a CRITICAL, loudly when it is empty."""
    audience = recipients_for_broadcast(db)
    if audience.reached_nobody:
        logger.warning(
            "critical_alert_unattended",
            queue_id=queue_id,
            on_duty_doctors=0,
            effect=(
                "no on-duty clinician received this CRITICAL in real time; it "
                "remains outstanding and will be delivered on the next connection"
            ),
        )
    return audience
