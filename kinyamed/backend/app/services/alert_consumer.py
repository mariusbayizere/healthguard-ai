"""Consuming the alert topic and pushing to connected dashboards (step 5).

OFFSETS ARE COMMITTED ONLY AFTER FAN-OUT HAS BEEN ATTEMPTED. That single rule is
what `enable_auto_commit=False` exists to make possible, and it is the whole of
§6.3's "offset not committed; no message lost": if delivery raises, the offset
stays where it was and the broker hands the message back.

A POISON MESSAGE MUST NOT WEDGE THE PARTITION. Redelivering for ever would stop
every patient queued behind it, which is a worse failure than dropping one
malformed payload. So a message that fails `MAX_ATTEMPTS` times is written to
the dead-letter topic WITH its failure reason and only then committed. The order
matters: DLQ first, commit second, because a commit before the DLQ write would
discard the message if the write failed.

WHAT THIS IS NOT. It is not what makes an alert durable -- the row in `queue`
is, and `services/alerts.outstanding_for` reads it. If this consumer is down for
an hour, the alerts of that hour are delivered by the reconnect backfill. That
is why the consumer is allowed to be simple and why none of its failure modes
lose a CRITICAL.

SINGLE-WORKER ASSUMPTION, stated because it is load-bearing. The group id is
stable, so partitions are shared across workers in a group -- but the sockets
are in-process, so a worker that consumes an alert can only push to the
dashboards connected to ITSELF. With one API process that is correct. With
several, a worker would consume alerts whose recipients are attached elsewhere,
and the real-time push for those would be missed (the backfill still covers
them, so nothing is lost, but the latency property degrades). Fixing it properly
needs either a group per worker or a Redis relay; neither is built, and
`reports/ALERT_DELIVERY_DESIGN.md` records it.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

# After this many failures a message is dead-lettered rather than redelivered
# for ever. Three is enough to ride out a transient fan-out error and few
# enough that a genuinely poisonous payload does not hold up a queue.
MAX_ATTEMPTS = 3


@dataclass
class ConsumeOutcome:
    """What happened to one message, for tests and for logging."""

    delivered: bool = False
    committed: bool = False
    dead_lettered: bool = False
    attempts: int = 0
    error: str | None = None


@dataclass
class AlertConsumer:
    """Drives one message at a time. The transport is injected.

    `consumer`, `dlq` and `deliver` are passed in rather than constructed here
    so the same code runs against an in-process fake (which proves the offset
    logic) and against a real broker (which proves it survives real wire
    behaviour). Neither substitutes for the other.
    """

    consumer: Any
    dlq: Any
    deliver: Callable[[dict[str, Any]], None]
    dlq_topic: str = "kinyamed_alerts.DLQ"
    _attempts: dict[str, int] = field(default_factory=dict)

    def _key(self, message: Any) -> str:
        return f"{message.topic}:{message.partition}:{message.offset}"

    def handle(self, message: Any) -> ConsumeOutcome:
        """Deliver one message, then decide whether the offset may advance."""
        key = self._key(message)
        outcome = ConsumeOutcome(attempts=self._attempts.get(key, 0) + 1)
        self._attempts[key] = outcome.attempts

        try:
            payload = message.value
            if isinstance(payload, bytes | bytearray):
                payload = json.loads(payload.decode("utf-8"))
            self.deliver(payload)
        except Exception as error:  # noqa: BLE001 - the point is to not commit
            outcome.error = f"{type(error).__name__}: {error}"
            if outcome.attempts >= MAX_ATTEMPTS:
                # DLQ FIRST, commit second. A commit before the dead-letter
                # write would discard the message if that write failed, which
                # is the one way this design can actually lose one.
                self._dead_letter(message, outcome)
                outcome.dead_lettered = True
                self.consumer.commit()
                outcome.committed = True
                logger.warning(
                    "alert_dead_lettered",
                    offset=message.offset,
                    attempts=outcome.attempts,
                    error=outcome.error,
                )
            else:
                # Offset deliberately NOT committed: the broker redelivers.
                logger.warning(
                    "alert_delivery_failed",
                    offset=message.offset,
                    attempt=outcome.attempts,
                    error=outcome.error,
                    effect="offset not committed; the message will be redelivered",
                )
            return outcome

        outcome.delivered = True
        self.consumer.commit()
        outcome.committed = True
        self._attempts.pop(key, None)
        return outcome

    def _dead_letter(self, message: Any, outcome: ConsumeOutcome) -> None:
        raw = message.value
        if isinstance(raw, bytes | bytearray):
            try:
                raw = json.loads(raw.decode("utf-8"))
            except Exception:  # noqa: BLE001 - a payload we cannot parse is the point
                raw = {"unparseable": True}
        self.dlq.send(
            self.dlq_topic,
            value={
                "original": raw,
                "offset": message.offset,
                "partition": message.partition,
                "attempts": outcome.attempts,
                "error": outcome.error,
            },
        )
