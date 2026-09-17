"""The same consumer, against a real broker (option B).

WHY BOTH THIS AND THE FAKE. `tests/unit/test_alert_consumer_offsets.py` proves
our offset logic: that we do not commit when delivery failed. It cannot prove
that the logic survives real wire behaviour, a group rebalance, or a broker
handing back an uncommitted message after a restart, because an in-process fake
models what we told it to model. This file answers that second question and
nothing else; neither file substitutes for the other.

SKIPS LOCALLY, FAILS ON THE RUNNER. A developer machine may have no broker, and
skipping is a reasonable courtesy there. In CI it is not: the job would go green
having run none of this, and "CI is green" would say nothing about whether a
CRITICAL survives a consumer restart. The runner sets CI=true, so the absence of
a broker is a failure that names the service to check -- the same gate the Redis
blocklist tests use, for the same reason.

THE LATENCY FIGURE IS NOT A GATE. It is measured and reported and nothing
asserts a threshold on it. Runner variance would make a sub-second assertion
flaky, and a flaky safety test is a test somebody disables -- at which point the
no-loss assertions in this file go with it. Gating on no-loss and reporting the
number keeps the valuable half enforceable.
"""

from __future__ import annotations

import json
import os
import time
import uuid

import pytest

pytestmark = pytest.mark.usefixtures("kafka_broker")

BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
CONNECT_TIMEOUT_MS = 10_000


def _reachable() -> bool:
    try:
        from kafka import KafkaAdminClient

        admin = KafkaAdminClient(
            bootstrap_servers=BOOTSTRAP.split(","),
            request_timeout_ms=CONNECT_TIMEOUT_MS,
        )
        admin.close()
        return True
    except Exception:  # noqa: BLE001 - any failure means "no broker"
        return False


@pytest.fixture(scope="module")
def kafka_broker():
    """A real broker, or skip locally and fail on the runner."""
    if _reachable():
        return BOOTSTRAP
    if os.environ.get("CI"):
        pytest.fail(
            f"No Kafka broker at {BOOTSTRAP} on the runner, so these cases would "
            "have skipped and the job would have gone green without running "
            "them. Check the kafka service in .github/workflows/ci.yml."
        )
    pytest.skip(f"No Kafka broker at {BOOTSTRAP}; the fake-broker tests still run")
    return None


@pytest.fixture
def topic(kafka_broker):
    """A topic of its own, so one case cannot see another's messages."""
    from kafka import KafkaAdminClient
    from kafka.admin import NewTopic

    name = f"kinyamed_alerts_test_{uuid.uuid4().hex[:8]}"
    admin = KafkaAdminClient(bootstrap_servers=kafka_broker.split(","))
    admin.create_topics([NewTopic(name=name, num_partitions=1, replication_factor=1)])
    yield name
    try:
        admin.delete_topics([name])
    finally:
        admin.close()


def _producer(bootstrap: str):
    from kafka import KafkaProducer

    return KafkaProducer(
        bootstrap_servers=bootstrap.split(","),
        value_serializer=lambda v: json.dumps(v).encode(),
        acks="all",
    )


def _consumer(bootstrap: str, topic: str, group: str):
    from kafka import KafkaConsumer

    return KafkaConsumer(
        topic,
        bootstrap_servers=bootstrap.split(","),
        group_id=group,
        # The whole point. Offsets advance only when we say so.
        enable_auto_commit=False,
        auto_offset_reset="earliest",
        consumer_timeout_ms=15_000,
    )


# ── No message lost across a consumer restart ────────────────────────────


def test_no_message_is_lost_when_the_consumer_restarts(kafka_broker, topic):
    """The §13 requirement, against a real broker.

    Three messages are produced. The first consumer takes one, commits it, and
    dies without touching the rest -- a crash mid-shift. A second consumer joins
    the SAME group and must receive the two that were never committed.
    """
    from app.services.alert_consumer import AlertConsumer

    group = f"group-{uuid.uuid4().hex[:8]}"
    producer = _producer(kafka_broker)
    for queue_id in (1, 2, 3):
        producer.send(topic, value={"queue_id": queue_id})
    producer.flush()

    first_seen: list[int] = []
    first = _consumer(kafka_broker, topic, group)
    driver = AlertConsumer(
        consumer=first,
        dlq=_producer(kafka_broker),
        deliver=lambda payload: first_seen.append(payload["queue_id"]),
    )
    for message in first:
        driver.handle(message)
        break  # crash after exactly one
    first.close()

    assert first_seen == [1]

    second_seen: list[int] = []
    second = _consumer(kafka_broker, topic, group)
    driver = AlertConsumer(
        consumer=second,
        dlq=_producer(kafka_broker),
        deliver=lambda payload: second_seen.append(payload["queue_id"]),
    )
    for message in second:
        driver.handle(message)
        if len(second_seen) == 2:
            break
    second.close()

    assert second_seen == [2, 3], (
        f"the restarted consumer received {second_seen}; messages 2 and 3 were "
        "committed by a consumer that never delivered them"
    )


def test_an_uncommitted_message_is_redelivered(kafka_broker, topic):
    """Delivery raised, so the offset stayed put and the broker hands it back."""
    from app.services.alert_consumer import AlertConsumer

    group = f"group-{uuid.uuid4().hex[:8]}"
    producer = _producer(kafka_broker)
    producer.send(topic, value={"queue_id": 99})
    producer.flush()

    def explode(_payload):
        raise RuntimeError("fan-out failed")

    first = _consumer(kafka_broker, topic, group)
    driver = AlertConsumer(consumer=first, dlq=_producer(kafka_broker), deliver=explode)
    for message in first:
        outcome = driver.handle(message)
        assert not outcome.committed
        break
    first.close()

    seen: list[int] = []
    second = _consumer(kafka_broker, topic, group)
    driver = AlertConsumer(
        consumer=second,
        dlq=_producer(kafka_broker),
        deliver=lambda payload: seen.append(payload["queue_id"]),
    )
    for message in second:
        driver.handle(message)
        break
    second.close()

    assert seen == [99], "an uncommitted message was not redelivered"


# ── Latency: MEASURED, NOT GATED ─────────────────────────────────────────


def test_end_to_end_latency_is_measured_and_reported(kafka_broker, topic, capsys):
    """NOT A GATE. The figure is reported; nothing asserts a threshold on it.

    §13 wants CRITICAL -> Kafka -> consumer -> client inside a second. Asserting
    that on a shared runner would be flaky, and a flaky safety test is one
    somebody disables -- taking the no-loss assertions above with it. So this
    measures and prints, and the only assertion is that a message arrived at
    all.
    """
    from app.services.alert_consumer import AlertConsumer

    group = f"group-{uuid.uuid4().hex[:8]}"
    consumer = _consumer(kafka_broker, topic, group)
    # Join the group before producing, so the measurement excludes the
    # first-connection handshake a real dashboard pays once.
    consumer.poll(timeout_ms=5_000)

    arrived: list[float] = []
    driver = AlertConsumer(
        consumer=consumer,
        dlq=_producer(kafka_broker),
        deliver=lambda payload: arrived.append(time.perf_counter()),
    )

    producer = _producer(kafka_broker)
    sent_at = time.perf_counter()
    producer.send(topic, value={"queue_id": 1234})
    producer.flush()

    for message in consumer:
        driver.handle(message)
        break
    consumer.close()

    assert arrived, "nothing arrived at all"
    elapsed_ms = (arrived[0] - sent_at) * 1000
    with capsys.disabled():
        print(
            f"\n  [NOT A GATE] publish -> consume latency: {elapsed_ms:.1f} ms "
            f"(§13 target < 1000 ms, not asserted: runner variance)"
        )
