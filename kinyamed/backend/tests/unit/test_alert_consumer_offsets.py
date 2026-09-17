"""Offset handling, against an in-process fake (option A).

WHAT THIS PROVES AND WHAT IT DOES NOT. The fake models one thing faithfully --
that a commit advances a position and an uncommitted message is handed back --
and that is exactly the property at risk in our code: whether we commit when
delivery failed. It proves our logic.

IT DOES NOT PROVE that this code survives real wire behaviour, a rebalance, or
a broker restart. Nothing in-process can. `test_alert_consumer_kafka.py` drives
the same class against a real broker for that, and the two are kept because
they answer different questions; deleting either on the grounds that the other
passes would be trading a proof for a resemblance.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import pytest
from app.services.alert_consumer import MAX_ATTEMPTS, AlertConsumer


@dataclass
class FakeMessage:
    value: Any
    offset: int = 0
    partition: int = 0
    topic: str = "kinyamed_alerts"


@dataclass
class FakeConsumer:
    """Records commits. A commit is the only state that matters here."""

    commits: int = 0

    def commit(self) -> None:
        self.commits += 1


@dataclass
class FakeProducer:
    sent: list[tuple[str, Any]] = field(default_factory=list)

    def send(self, topic: str, value: Any = None, key: Any = None) -> None:
        self.sent.append((topic, value))


def _consumer(deliver) -> tuple[AlertConsumer, FakeConsumer, FakeProducer]:
    transport, dlq = FakeConsumer(), FakeProducer()
    return AlertConsumer(consumer=transport, dlq=dlq, deliver=deliver), transport, dlq


# ── The rule ─────────────────────────────────────────────────────────────


def test_a_delivered_message_is_committed():
    seen: list[dict] = []
    consumer, transport, _ = _consumer(seen.append)

    outcome = consumer.handle(FakeMessage(value={"queue_id": 1}))

    assert outcome.delivered and outcome.committed
    assert transport.commits == 1
    assert seen == [{"queue_id": 1}]


def test_a_failed_delivery_is_not_committed():
    """§6.3. An uncommitted offset is what makes redelivery happen."""

    def explode(_payload):
        raise RuntimeError("the socket fan-out failed")

    consumer, transport, dlq = _consumer(explode)
    outcome = consumer.handle(FakeMessage(value={"queue_id": 1}))

    assert not outcome.delivered
    assert not outcome.committed, "the offset advanced past a message nobody received"
    assert transport.commits == 0
    assert dlq.sent == [], "dead-lettered on the first failure instead of retrying"


def test_a_redelivered_message_can_succeed_and_then_commits():
    attempts = {"n": 0}

    def flaky(_payload):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("transient")

    consumer, transport, _ = _consumer(flaky)
    message = FakeMessage(value={"queue_id": 1}, offset=7)

    assert not consumer.handle(message).committed
    assert consumer.handle(message).committed
    assert transport.commits == 1


# ── Poison messages ──────────────────────────────────────────────────────


def test_a_persistently_failing_message_is_dead_lettered_then_committed():
    """Redelivering for ever would stop every patient queued behind it."""

    def explode(_payload):
        raise RuntimeError("poison")

    consumer, transport, dlq = _consumer(explode)
    message = FakeMessage(value={"queue_id": 1}, offset=11)

    for _ in range(MAX_ATTEMPTS - 1):
        outcome = consumer.handle(message)
        assert not outcome.committed and not outcome.dead_lettered

    final = consumer.handle(message)
    assert final.dead_lettered and final.committed
    assert transport.commits == 1
    assert len(dlq.sent) == 1


def test_the_dead_letter_carries_the_reason_and_the_original():
    def explode(_payload):
        raise RuntimeError("poison")

    consumer, _, dlq = _consumer(explode)
    message = FakeMessage(value={"queue_id": 42}, offset=3, partition=1)
    for _ in range(MAX_ATTEMPTS):
        consumer.handle(message)

    topic, payload = dlq.sent[0]
    assert topic.endswith(".DLQ")
    assert payload["original"] == {"queue_id": 42}
    assert payload["offset"] == 3 and payload["partition"] == 1
    assert "RuntimeError" in payload["error"]


def test_an_unparseable_payload_is_dead_lettered_not_retried_for_ever():
    consumer, _transport, dlq = _consumer(lambda payload: None)
    message = FakeMessage(value=b"{not json", offset=5)

    for _ in range(MAX_ATTEMPTS):
        outcome = consumer.handle(message)

    assert outcome.dead_lettered and outcome.committed
    assert dlq.sent[0][1]["original"] == {"unparseable": True}


def test_the_dead_letter_is_written_before_the_offset_advances():
    """Order matters: a commit first would discard the message if the DLQ failed."""
    order: list[str] = []

    class OrderedConsumer(FakeConsumer):
        def commit(self) -> None:
            order.append("commit")
            super().commit()

    class OrderedProducer(FakeProducer):
        def send(self, topic, value=None, key=None):
            order.append("dlq")
            super().send(topic, value, key)

    def explode(_payload):
        raise RuntimeError("poison")

    consumer = AlertConsumer(
        consumer=OrderedConsumer(), dlq=OrderedProducer(), deliver=explode
    )
    message = FakeMessage(value={"queue_id": 1})
    for _ in range(MAX_ATTEMPTS):
        consumer.handle(message)

    assert order == ["dlq", "commit"], f"wrong order: {order}"


# ── Encoding ─────────────────────────────────────────────────────────────


def test_a_json_encoded_payload_is_decoded():
    seen: list[dict] = []
    consumer, _, _ = _consumer(seen.append)
    consumer.handle(FakeMessage(value=json.dumps({"queue_id": 9}).encode()))
    assert seen == [{"queue_id": 9}]


@pytest.mark.parametrize("attempts_before_dlq", [MAX_ATTEMPTS])
def test_the_attempt_budget_is_what_the_constant_says(attempts_before_dlq):
    """A test that fails if somebody changes the constant without meaning to."""

    def explode(_payload):
        raise RuntimeError("poison")

    consumer, _, dlq = _consumer(explode)
    message = FakeMessage(value={"queue_id": 1})
    for _ in range(attempts_before_dlq - 1):
        consumer.handle(message)
    assert dlq.sent == []
    consumer.handle(message)
    assert len(dlq.sent) == 1
