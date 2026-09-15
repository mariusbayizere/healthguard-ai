"""Micro-batched inference replaces the single lock that serialised every forward pass.

The lock made the Nth concurrent request wait for N-1 full inferences (MODEL_AUDIT
§3.1, NOT REPRODUCIBLE: p50 7.9 s at 50 concurrent). One worker thread now owns the
model and runs waiting requests as one batch.

The property that matters most is not speed: NO REQUEST MAY RECEIVE ANOTHER
REQUEST'S RESULT. A mix-up would hand one patient another patient's urgency.

A fake forward function stands in for the model; nothing here loads torch.
"""

from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
from app.services.model_classifier import BatchedInference, InferenceTimeoutError

LABELS = ("CRITICAL", "URGENT", "ROUTINE")


def _probs_for(text: str) -> tuple[float, float, float]:
    """A deterministic distribution that identifies the text it came from."""
    k = int(text.rsplit("-", 1)[1])
    top = k % 3
    confidence = 0.5 + (k % 1000) / 2000  # unique per text, in [0.5, 1.0)
    rest = (1 - confidence) / 2
    probs = [rest, rest, rest]
    probs[top] = confidence
    return tuple(probs)


class FakeForward:
    def __init__(self, cost_s: float = 0.0, fail_on: str | None = None) -> None:
        self.batches: list[int] = []
        self.cost_s = cost_s
        self.fail_on = fail_on
        self.threads: set[int] = set()

    def __call__(self, texts: list[str]) -> list[tuple[float, float, float]]:
        self.threads.add(threading.get_ident())
        self.batches.append(len(texts))
        time.sleep(self.cost_s)
        if self.fail_on and self.fail_on in texts:
            raise RuntimeError("inference failed")
        return [_probs_for(t) for t in texts]


def _run_concurrently(engine: BatchedInference, texts: list[str], workers: int):
    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(engine.infer, texts))


def test_every_concurrent_request_gets_its_own_result():
    forward = FakeForward(cost_s=0.002)
    engine = BatchedInference(forward, max_batch_size=16, max_wait_ms=5, timeout_s=30)
    try:
        texts = [f"text-{k}" for k in range(1000)]
        results = _run_concurrently(engine, texts, workers=64)
    finally:
        engine.close()
    assert [tuple(r) for r in results] == [_probs_for(t) for t in texts]
    assert max(forward.batches) > 1, "concurrent requests were never batched"
    assert max(forward.batches) <= 16
    assert sum(forward.batches) == 1000
    assert len(forward.threads) == 1, "the model must be touched by one thread only"


def test_fifty_concurrent_requests_are_not_serialised():
    """Forward costs 100 ms whatever the batch size. Serialised, 50 requests take
    about 5 s; batched 16 at a time, about four forwards."""
    forward = FakeForward(cost_s=0.1)
    engine = BatchedInference(forward, max_batch_size=16, max_wait_ms=5, timeout_s=30)
    try:
        start = time.perf_counter()
        _run_concurrently(engine, [f"text-{k}" for k in range(50)], workers=50)
        elapsed = time.perf_counter() - start
    finally:
        engine.close()
    assert elapsed < 2.0, f"50 concurrent requests took {elapsed:.2f} s"
    assert len(forward.batches) <= 10


def test_a_single_request_is_not_held_for_a_full_batch():
    forward = FakeForward()
    engine = BatchedInference(forward, max_batch_size=16, max_wait_ms=5, timeout_s=30)
    try:
        start = time.perf_counter()
        engine.infer("text-1")
        assert time.perf_counter() - start < 0.5
    finally:
        engine.close()
    assert forward.batches == [1]


def test_a_failed_forward_fails_every_request_in_its_batch():
    """Every waiting caller sees the error, so triage fails closed (503) for each;
    nobody is left waiting and nobody receives a partial result."""
    forward = FakeForward(cost_s=0.05, fail_on="text-7")
    engine = BatchedInference(forward, max_batch_size=64, max_wait_ms=50, timeout_s=30)
    outcomes: list[str] = []

    def call(text: str) -> None:
        try:
            engine.infer(text)
            outcomes.append("ok")
        except RuntimeError:
            outcomes.append("error")

    try:
        with ThreadPoolExecutor(max_workers=20) as pool:
            list(pool.map(call, [f"text-{k}" for k in range(20)]))
    finally:
        engine.close()
    assert "error" in outcomes
    assert len(outcomes) == 20


def test_the_engine_keeps_serving_after_a_failed_batch():
    forward = FakeForward(fail_on="text-0")
    engine = BatchedInference(forward, max_batch_size=4, max_wait_ms=1, timeout_s=30)
    try:
        with pytest.raises(RuntimeError):
            engine.infer("text-0")
        assert tuple(engine.infer("text-5")) == _probs_for("text-5")
    finally:
        engine.close()


def test_a_stuck_model_times_out_instead_of_hanging_the_request():
    forward = FakeForward(cost_s=2.0)
    engine = BatchedInference(forward, max_batch_size=1, max_wait_ms=1, timeout_s=0.2)
    try:
        with pytest.raises(InferenceTimeoutError):
            engine.infer("text-1")
    finally:
        engine.close()


def test_a_closed_engine_refuses_new_requests():
    engine = BatchedInference(
        FakeForward(), max_batch_size=4, max_wait_ms=1, timeout_s=5
    )
    engine.close()
    with pytest.raises(RuntimeError, match="closed"):
        engine.infer("text-1")


# ── Adversarial interleaving: no request ever receives another's result ───────
def test_adversarial_interleaving_never_crosses_results():
    """Random arrival jitter, random forward latency, random batch limits and many
    rounds. Each request carries a unique id, so a result delivered to the wrong
    caller cannot hide behind an identical text."""
    import random

    rng = random.Random(20260915)
    for round_ in range(12):

        class JitteryForward(FakeForward):
            def __call__(self, texts):
                time.sleep(rng.random() * 0.01)
                return super().__call__(texts)

        engine = BatchedInference(
            JitteryForward(),
            max_batch_size=rng.choice([1, 2, 3, 7, 16, 64]),
            max_wait_ms=rng.choice([0, 1, 5, 20]),
            timeout_s=30,
        )
        texts = [f"round{round_}-{k}" for k in range(300)]

        def call(text: str, engine: BatchedInference = engine):
            time.sleep(rng.random() * 0.005)
            return text, tuple(engine.infer(text))

        try:
            with ThreadPoolExecutor(max_workers=rng.choice([8, 32, 96])) as pool:
                results = list(pool.map(call, texts))
        finally:
            engine.close()
        for text, probs in results:
            assert probs == _probs_for(text), (
                f"round {round_}: {text} got another result"
            )


def test_a_late_result_is_never_delivered_to_a_later_request():
    """Request A times out while its forward is still running. When that forward
    finishes, its result must be discarded, not handed to request B."""
    gate = threading.Event()

    class SlowFirst(FakeForward):
        def __call__(self, texts):
            if "text-1" in texts:
                gate.wait(5)
            return super().__call__(texts)

    engine = BatchedInference(
        SlowFirst(), max_batch_size=1, max_wait_ms=0, timeout_s=0.2
    )
    with pytest.raises(InferenceTimeoutError):
        engine.infer("text-1")
    gate.set()
    # A generous timeout for B, on the same engine and worker, which is still
    # finishing A's forward when B arrives.
    engine.timeout_s = 5
    try:
        assert tuple(engine.infer("text-2")) == _probs_for("text-2")
        assert tuple(engine.infer("text-3")) == _probs_for("text-3")
    finally:
        engine.close()


@pytest.mark.parametrize("returned", [0, 1, 3])
def test_a_forward_returning_the_wrong_number_of_results_fails_the_whole_batch(
    returned,
):
    """Positional matching is only safe if the forward returns exactly one result
    per input. Anything else must fail every caller, never assign partially."""

    class Wrong(FakeForward):
        def __call__(self, texts):
            out = super().__call__(texts)
            return (out + out)[:returned] if len(texts) == 2 else out

    engine = BatchedInference(Wrong(), max_batch_size=2, max_wait_ms=200, timeout_s=10)
    errors = []

    def call(text):
        try:
            engine.infer(text)
        except RuntimeError as error:
            errors.append(str(error))

    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(call, ["text-1", "text-2"]))
    finally:
        engine.close()
    assert len(errors) == 2 and all("expected 2" in e for e in errors)


# ── Fail-closed through triage ────────────────────────────────────────────────
@pytest.mark.parametrize("failure", ["error", "timeout"])
def test_a_batch_error_or_timeout_fails_triage_closed(failure):
    """The classifier raises, `run_triage` turns it into a 503 before any write."""
    from app.core.exceptions import TriageModelUnavailableError
    from app.services import triage_service
    from app.services.model_classifier import ModelClassifier

    forward = (
        FakeForward(cost_s=1.0)
        if failure == "timeout"
        else FakeForward(fail_on="text-9")
    )
    engine = BatchedInference(forward, max_batch_size=4, max_wait_ms=1, timeout_s=0.1)
    classifier = ModelClassifier.with_engine(engine)
    try:
        with pytest.raises(TriageModelUnavailableError):
            triage_service._classify(classifier, "text-9")
    finally:
        engine.close()


def test_the_classifier_maps_probabilities_to_urgency_in_label_order():
    from app.models.triage_result import UrgencyLevel
    from app.services.model_classifier import ModelClassifier

    engine = BatchedInference(
        FakeForward(), max_batch_size=4, max_wait_ms=1, timeout_s=5
    )
    classifier = ModelClassifier.with_engine(engine)
    try:
        for k, expected in (
            (0, UrgencyLevel.CRITICAL),
            (1, UrgencyLevel.URGENT),
            (2, UrgencyLevel.ROUTINE),
        ):
            result = classifier.classify(f"text-{k}")
            assert result.urgency is expected
            assert result.confidence == pytest.approx(max(_probs_for(f"text-{k}")))
    finally:
        engine.close()
