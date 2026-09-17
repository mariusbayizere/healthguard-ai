"""Publishing CRITICAL alerts to the event stream (step 4).

KAFKA IS THE LATENCY HALF OF THIS DESIGN AND NOTHING MORE. The alert is durable
in Postgres before a publish is attempted, and the reconnect backfill
(`services/alerts.outstanding_for`) never reads from here. So every failure in
this module costs seconds of notification delay and nothing else, which is why
every call is wrapped and none of them can fail a triage.

Three rules follow from that, and each is asserted by a test:

  * PUBLISH AFTER COMMIT. The clinical record lands first, exactly as the SMS
    receipt does. A publish inside the transaction could roll one back.
  * NEVER BLOCK. Short timeouts, because a hung broker must not become a hung
    triage endpoint.
  * NEVER RAISE. A broker outage is logged once per transition and swallowed.

THE PAYLOAD CARRIES NO PERSONAL DATA AT ALL -- not the symptom text, not a
phone, and not a name. Only identifiers, urgency and a timestamp.

That is stricter than the socket frame a doctor receives, deliberately. A
dashboard needs a name to be useful and its audience is a clinician looking at
that patient. A Kafka topic is retained, replicated, and frequently mirrored
into an analytics estate nobody on this project controls, and its audience is
whoever ends up with read access years from now. The consumer already has a
database connection, so it resolves the name itself before pushing to a socket;
carrying it through the topic buys nothing and spreads it (L11).
"""

from __future__ import annotations

import json
import threading
from typing import Any

import structlog

from app.core.config import settings

logger = structlog.get_logger(__name__)

_producer: Any | None = None
_resolved = False
_lock = threading.Lock()
_failure_logged = False


def reset_producer() -> None:
    """Drop the cached producer. For tests, and after a config change."""
    global _producer, _resolved, _failure_logged
    with _lock:
        _producer = None
        _resolved = False
        _failure_logged = False


def _build_producer() -> Any:
    """A configured KafkaProducer. Replaced wholesale in tests."""
    from kafka import KafkaProducer

    return KafkaProducer(
        bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","),
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
        key_serializer=lambda key: key.encode("utf-8") if key else None,
        # Short, because this sits just after a request's transaction. A
        # clinician waiting on a broker handshake is a broker outage becoming a
        # triage outage.
        max_block_ms=int(settings.KAFKA_TIMEOUT_SECONDS * 1000),
        request_timeout_ms=int(settings.KAFKA_TIMEOUT_SECONDS * 1000),
        # Every replica must have it before we count it sent. A CRITICAL alert
        # is not worth the throughput saved by acks=1.
        acks="all",
        retries=1,
    )


def _get_producer() -> Any | None:
    global _producer, _resolved
    if _resolved:
        return _producer
    with _lock:
        if _resolved:
            return _producer
        _resolved = True
        if not settings.KAFKA_ENABLED:
            _producer = None
            return None
        try:
            _producer = _build_producer()
        except Exception as error:  # noqa: BLE001 - any failure means "no stream"
            _degraded(error)
            _producer = None
        return _producer


def _degraded(error: Exception) -> None:
    """Log the first failure of a run, not one per triage."""
    global _failure_logged
    if _failure_logged:
        return
    _failure_logged = True
    logger.warning(
        "alert_stream_unavailable",
        error=type(error).__name__,
        effect=(
            "CRITICAL alerts are not being pushed in real time; they remain "
            "outstanding and are delivered when a dashboard connects"
        ),
    )


def publish_critical(*, queue_id: int, queue_number: int, created_at: str) -> bool:
    """Announce a CRITICAL. True if it was handed to the broker.

    False means the stream is unavailable, which the caller treats as a delay
    rather than a failure: the alert is already durable and the dashboards will
    receive it on their next connection.
    """
    producer = _get_producer()
    if producer is None:
        return False
    payload = {
        "queue_id": queue_id,
        "queue_number": queue_number,
        "urgency": "CRITICAL",
        "created_at": created_at,
    }
    try:
        producer.send(settings.KAFKA_TOPIC_ALERTS, value=payload, key=str(queue_id))
        return True
    except Exception as error:  # noqa: BLE001
        _degraded(error)
        return False


def status() -> str:
    """'ok', 'degraded' or 'disabled', for readiness."""
    if not settings.KAFKA_ENABLED:
        return "disabled"
    return "ok" if _get_producer() is not None else "degraded"
