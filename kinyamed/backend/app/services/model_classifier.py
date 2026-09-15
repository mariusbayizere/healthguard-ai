"""C1 — the fine-tuned classifier behind the `SymptomClassifier` seam.

This is the ONLY implementation of `SymptomClassifier` in the service. There
is no fallback. `build_classifier()` returns a loaded model or `None`, and the
triage endpoint turns `None` into a 503 that tells staff to triage manually.

WHY THERE IS NO FALLBACK
------------------------
A keyword matcher used to be served whenever no model was configured. Measured
on the frozen Kinyarwanda holdout it caught 5.7% of CRITICAL cases and sent
94.3% of them to ROUTINE, with a confident "you can wait" message
(reports/MODEL_AUDIT.md §6.2). A classifier that is wrong in the dangerous
direction is worse than no classifier, because nobody triages a patient the
system has already triaged. Absent model => no classification, everywhere.

TORCH IS AN OPTIONAL DEPENDENCY, ON PURPOSE
-------------------------------------------
`backend/requirements.txt` keeps torch and transformers out of the API image.
They are imported lazily. Without them the service still starts and serves
everything except triage, which fails closed.

`build_classifier()` has two outcomes and says which one it took, loudly:

  1. set and loadable                               -> the model
  2. unset, missing, deps absent, or load failure   -> None, logged at ERROR

WARM START IS NOT AN OPTIMISATION HERE
--------------------------------------
Measured on this hardware (`ml_model/training/latency_v2d.json`): the first
inference in a process costs 1341 ms; warm median is 66 ms and p95 is 103 ms.
A worker that loads lazily pays that 1341 ms on a live patient's request, and
the project document claims sub-200 ms. `warm_up()` is called at application
start so the cost lands before the service reports ready.

CONFIDENCE IS A SOFTMAX PROBABILITY, WHICH IS NOT A CALIBRATED ONE
------------------------------------------------------------------
`Classification.confidence` is filled with the softmax maximum because the
dataclass requires a number. It is NOT a calibrated probability: the model was
never calibrated, and the corpus it trained on has four distinct CRITICAL
sentences in its evaluation set. Do not gate clinical behaviour on it, and do
not report it to a patient as a likelihood.
"""

from __future__ import annotations

import queue
import threading
import time
from collections.abc import Callable, Sequence
from pathlib import Path

import structlog

from app.core.config import settings
from app.models.triage_result import UrgencyLevel
from app.services.triage_service import Classification

logger = structlog.get_logger(__name__)

# The model's label order, fixed by training/config.py. Read from the loaded
# model's own id2label where present; this is the fallback and the check.
LABEL_ORDER = ("CRITICAL", "URGENT", "ROUTINE")

_URGENCY = {
    "CRITICAL": UrgencyLevel.CRITICAL,
    "URGENT": UrgencyLevel.URGENT,
    "ROUTINE": UrgencyLevel.ROUTINE,
}


TRAINING_METADATA = "kinyamed_training.json"


class ModelConfigurationError(RuntimeError):
    """The model cannot be served as configured. Stops start-up; never becomes None."""


def read_training_max_length(model_path: Path) -> int:
    """The max_length the model was fine-tuned at, as its directory records it."""
    import json

    metadata = model_path / TRAINING_METADATA
    try:
        recorded = json.loads(metadata.read_text()).get("max_length")
    except (OSError, ValueError, AttributeError) as error:
        raise ModelConfigurationError(
            f"{model_path} does not record its training max_length in {TRAINING_METADATA} "
            f"({type(error).__name__}). Record it from the training run: "
            "python scripts/record_training_length.py --model <dir> --run-record <run json>"
        ) from error
    if isinstance(recorded, bool) or not isinstance(recorded, int) or recorded <= 0:
        raise ModelConfigurationError(
            f"{model_path}/{TRAINING_METADATA} does not record a valid training max_length "
            f"(found {recorded!r})"
        )
    return recorded


def resolve_max_length(model_path: Path, configured: int | None) -> int:
    """The length to serve at: the training length, and never anything else.

    Serving at a different length classifies inputs the model never saw in
    fine-tuning (v2d: trained at 96, served at 512). Unset configuration takes the
    recorded length; a configured length that differs is refused.
    """
    trained = read_training_max_length(model_path)
    if configured is not None and configured != trained:
        raise ModelConfigurationError(
            f"MODEL_MAX_LENGTH={configured} but the model at {model_path} was trained at "
            f"max_length={trained}. Refusing to start: remove MODEL_MAX_LENGTH or set it "
            f"to {trained}."
        )
    return trained


class InferenceTimeoutError(RuntimeError):
    """No result within the timeout. Triage fails closed (503); nothing is written."""


BatchForward = Callable[[list[str]], Sequence[Sequence[float]]]


class _Request:
    """One caller's request. Its result is written here and nowhere else."""

    __slots__ = ("abandoned", "done", "error", "result", "text")

    def __init__(self, text: str) -> None:
        self.text = text
        self.done = threading.Event()
        self.result: Sequence[float] | None = None
        self.error: BaseException | None = None
        self.abandoned = False


class BatchedInference:
    """Micro-batched inference: one worker thread owns the model.

    Replaces a single lock that serialised every forward pass, so the Nth
    concurrent caller waited for N-1 whole inferences. Callers still call
    `infer()` synchronously. The worker takes the first waiting request, gathers
    more for at most `max_wait_ms` (up to `max_batch_size`), and runs them as one
    forward pass.

    NO REQUEST CAN RECEIVE ANOTHER REQUEST'S RESULT:
      * each caller owns its `_Request`; results are written to the request objects
        of the batch that produced them, by position, and only after checking the
        forward returned exactly one result per input;
      * a caller that times out marks its request abandoned. A late result lands on
        that object, which nobody reads, and never on a later request.

    FAILS CLOSED: a forward that raises, or returns the wrong number of results,
    fails every caller in that batch. A caller with no result by `timeout_s` gets
    `InferenceTimeoutError`. `triage_service._classify` turns both into a 503
    before anything is written.
    """

    def __init__(
        self,
        forward: BatchForward,
        *,
        max_batch_size: int,
        max_wait_ms: float,
        timeout_s: float,
    ) -> None:
        if max_batch_size < 1 or max_wait_ms < 0 or timeout_s <= 0:
            raise ValueError("max_batch_size >= 1, max_wait_ms >= 0, timeout_s > 0")
        self._forward = forward
        self.max_batch_size = max_batch_size
        self.max_wait_s = max_wait_ms / 1000.0
        self.timeout_s = timeout_s
        self._queue: queue.Queue[_Request | None] = queue.Queue()
        self._closed = False
        self._state_lock = threading.Lock()
        self._worker = threading.Thread(
            target=self._run, name="triage-inference", daemon=True
        )
        self._worker.start()

    def infer(self, text: str) -> Sequence[float]:
        request = _Request(text)
        with self._state_lock:
            if self._closed:
                raise RuntimeError("inference engine is closed")
            self._queue.put(request)
        if not request.done.wait(self.timeout_s):
            request.abandoned = True
            raise InferenceTimeoutError(
                f"no inference result within {self.timeout_s:g} s"
            )
        if request.error is not None:
            raise request.error
        if request.result is None:  # pragma: no cover - guarded by the worker
            raise RuntimeError("inference finished without a result")
        return request.result

    def close(self) -> None:
        with self._state_lock:
            if self._closed:
                return
            self._closed = True
            self._queue.put(None)
        self._worker.join(timeout=5)

    def _gather(self, first: _Request) -> tuple[list[_Request], bool]:
        """The first request plus whatever arrives within the wait window."""
        batch = [first]
        stop = False
        deadline = time.monotonic() + self.max_wait_s
        while len(batch) < self.max_batch_size:
            remaining = deadline - time.monotonic()
            try:
                item = (
                    self._queue.get(timeout=remaining)
                    if remaining > 0
                    else self._queue.get_nowait()
                )
            except queue.Empty:
                break
            if item is None:
                stop = True
                break
            batch.append(item)
        return batch, stop

    def _run(self) -> None:
        stop = False
        while not stop:
            first = self._queue.get()
            if first is None:
                break
            batch, stop = self._gather(first)
            live = [r for r in batch if not r.abandoned]
            if live:
                try:
                    results = list(self._forward([r.text for r in live]))
                    if len(results) != len(live):
                        raise RuntimeError(
                            f"forward returned {len(results)} results, expected {len(live)}"
                        )
                    for request, result in zip(live, results, strict=True):
                        request.result = result
                except Exception as error:  # noqa: BLE001 — every caller in the batch fails closed
                    for request in live:
                        request.error = error
            for request in batch:
                request.done.set()


class ModelClassifier:
    """Fine-tuned sequence classifier implementing `SymptomClassifier`."""

    _engine: BatchedInference
    _labels: tuple[str, ...]
    model_path: Path | None

    @classmethod
    def with_engine(
        cls, engine: BatchedInference, labels: tuple[str, ...] = LABEL_ORDER
    ) -> ModelClassifier:
        """A classifier over an existing engine. Used by tests with a fake forward."""
        classifier = cls.__new__(cls)
        classifier._engine = engine
        classifier._labels = labels
        classifier.model_path = None
        return classifier

    def __init__(self, model_path: Path, max_length: int, threads: int | None = None):
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        if threads:
            torch.set_num_threads(threads)
        self._torch = torch
        tokenizer_dir = model_path / "tokenizer"
        self._tokenizer = AutoTokenizer.from_pretrained(
            str(tokenizer_dir if tokenizer_dir.exists() else model_path)
        )
        self._model = AutoModelForSequenceClassification.from_pretrained(
            str(model_path)
        )
        self._model.eval()
        self._max_length = max_length

        # The label order must come from the artefact, not from a constant here.
        # A model whose id2label disagrees with LABEL_ORDER would map CRITICAL to
        # ROUTINE with no error, which is the worst failure this service has.
        id2label = getattr(self._model.config, "id2label", None) or {}
        resolved = tuple(str(id2label[i]) for i in sorted(id2label)) if id2label else ()
        if resolved and tuple(resolved) != LABEL_ORDER:
            raise ValueError(
                f"model id2label is {resolved}, expected {LABEL_ORDER}. Refusing to "
                "serve: a label-order mismatch silently maps one urgency to another."
            )
        self._labels = resolved or LABEL_ORDER
        self.model_path = model_path
        self._engine = BatchedInference(
            self._forward_batch,
            max_batch_size=settings.TRIAGE_BATCH_MAX_SIZE,
            max_wait_ms=settings.TRIAGE_BATCH_MAX_WAIT_MS,
            timeout_s=settings.TRIAGE_INFERENCE_TIMEOUT_SECONDS,
        )

    def _forward_batch(self, texts: list[str]) -> list[list[float]]:
        """One padded forward pass. Called only from the engine's worker thread, so
        the tokenizer and model are never used concurrently."""
        torch = self._torch
        with torch.no_grad():
            encoded = self._tokenizer(
                texts,
                return_tensors="pt",
                truncation=True,
                padding=True,
                max_length=self._max_length,
            )
            logits = self._model(**encoded).logits
            probs: list[list[float]] = torch.softmax(logits, dim=-1).tolist()
        return probs

    def warm_up(self) -> float:
        """Run one inference so a patient does not pay the cold start.

        Returns the milliseconds it took, for the startup log.
        """
        start = time.perf_counter()
        self.classify("mfite umuriro")
        return (time.perf_counter() - start) * 1000.0

    def classify(self, text: str) -> Classification:
        probs = self._engine.infer(text)
        index = max(range(len(probs)), key=lambda k: probs[k])
        label = self._labels[index]
        urgency = _URGENCY[label]
        # Urgency and confidence only: the model names no condition and writes
        # no advice. What a patient reads is `patient_message.patient_receipt`.
        return Classification(urgency=urgency, confidence=float(probs[index]))


def _unavailable(reason: str, **context: object) -> tuple[None, str]:
    """Log why triage will fail closed, and return the no-model outcome."""
    logger.error(
        "triage_model_unavailable",
        reason=reason,
        action="triage endpoint will return 503; triage patients manually",
        **context,
    )
    return None, reason


def build_classifier() -> tuple[ModelClassifier | None, str]:
    """Return (the loaded model or None, one line saying what happened and why)."""
    raw = settings.TRIAGE_MODEL_PATH
    if not raw:
        return _unavailable("TRIAGE_MODEL_PATH is unset")

    path = Path(raw).expanduser()
    if not path.exists():
        return _unavailable(f"no model at {path}")

    # A length mismatch, or a model that cannot say what length it was trained at,
    # is a configuration error. It raises through start-up rather than becoming a
    # quiet 503 that nobody investigates.
    max_length = resolve_max_length(path, settings.MODEL_MAX_LENGTH)

    try:
        classifier = ModelClassifier(
            path,
            max_length=max_length,
            threads=settings.TRIAGE_MODEL_THREADS,
        )
    except ImportError as error:
        return _unavailable(
            f"torch/transformers unavailable ({error})",
            hint="torch/transformers are deliberately not in the API image",
        )
    except Exception as error:  # noqa: BLE001 — any load failure means no model, never a crash
        return _unavailable(f"the model at {path} failed to load ({error})")

    warm_ms = classifier.warm_up()
    logger.info(
        "triage_model_loaded",
        path=str(path),
        max_length=max_length,
        warm_up_ms=round(warm_ms, 1),
    )
    return classifier, f"fine-tuned model from {path} (warm-up {warm_ms:.0f} ms)"
