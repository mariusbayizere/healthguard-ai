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

THE SERVED DECISION IS THE RECORDED ONE, OR NOTHING
---------------------------------------------------
A model trained by `ml_model/training/pipeline.py` records, beside `max_length`, the
temperature fitted on its calibration split and the decision thresholds tuned to
CRITICAL safety. The deployment gate scores THAT thresholded decision. Serving the
argmax of uncalibrated probabilities instead would serve a decision nobody measured.
`read_decision_rule` reads the record, `calibrated_probabilities` applies the
temperature inside the forward pass, and `DecisionRule.decide` applies the thresholds.
A record this service cannot apply exactly (half a rule, an invalid value, an unknown
rule text or key, a different label order) raises `ModelConfigurationError` through
start-up, the same contract as `max_length`. The two implementations are held
together by golden cases (`ml_model/tests/fixtures/decision_rule_cases.json`).

A model recording neither (v2d) is served by argmax, which is also what the gate
scores when predictions carry no decision.

CONFIDENCE IS THE PROBABILITY OF THE CLASS SERVED
-------------------------------------------------
`Classification.confidence` is the probability of the class actually served, not the
maximum, so a CRITICAL chosen by a low threshold carries its low probability into the
review flag. Without a recorded temperature it is an uncalibrated softmax value (v2d
was never calibrated, and its evaluation set has four distinct CRITICAL sentences). Do
not report it to a patient as a likelihood.
"""

from __future__ import annotations

import json
import math
import queue
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypeGuard

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


# The only thresholded rule this service implements, verbatim as training records it
# (ml_model/training/thresholds.py RULE). Any other recorded rule text is refused.
THRESHOLD_RULE = (
    "CRITICAL if p_C >= critical; URGENT if p_C + p_U >= urgent; else ROUTINE"
)

# Keys the service applies (max_length, temperature, thresholds, labels) or knows to be
# provenance only (the rest). Anything else might change the decision in a way this
# service does not implement, so it is refused rather than ignored.
KNOWN_METADATA_KEYS = frozenset(
    {
        "max_length",
        "temperature",
        "thresholds",
        "labels",
        "source",
        "recorded_at",
        "cost_matrix",
        "base_model",
        "seed",
    }
)


@dataclass(frozen=True)
class DecisionRule:
    """How probabilities become an urgency: a temperature, then thresholds or argmax."""

    temperature: float = 1.0
    thresholds: tuple[float, float] | None = None  # (critical, urgent)

    def decide(self, probs: Sequence[float]) -> int:
        """The served class index, in LABEL_ORDER."""
        if self.thresholds is None:
            # Ties resolve to the more urgent class, as the gate's argmax does.
            return max(range(len(probs)), key=lambda k: probs[k])
        critical, urgent = self.thresholds
        if probs[0] >= critical:
            return 0
        if probs[0] + probs[1] >= urgent:
            return 1
        return 2

    def describe(self) -> str:
        if self.thresholds is None:
            return (
                f"argmax at temperature {self.temperature:g} "
                "(the model records no calibrated thresholds)"
            )
        critical, urgent = self.thresholds
        return (
            f"temperature {self.temperature:g}; CRITICAL if p_C >= {critical:g}; "
            f"URGENT if p_C + p_U >= {urgent:g}; else ROUTINE"
        )


ARGMAX = DecisionRule()


def calibrated_probabilities(
    logits: Sequence[Sequence[float]], temperature: float
) -> list[list[float]]:
    """softmax(logits / temperature) per row, computed as training/calibration.py does."""
    rows = []
    for row in logits:
        scaled = [value / temperature for value in row]
        top = max(scaled)
        exps = [math.exp(value - top) for value in scaled]
        total = sum(exps)
        rows.append([value / total for value in exps])
    return rows


def _is_number(value: object) -> TypeGuard[int | float]:
    return (
        isinstance(value, int | float)
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def read_decision_rule(model_path: Path) -> DecisionRule:
    """The decision rule the model was calibrated and gated with, as its directory records
    it. Refuses anything this service cannot apply exactly."""
    location = model_path / TRAINING_METADATA
    try:
        metadata = json.loads(location.read_text())
    except (OSError, ValueError) as error:
        raise ModelConfigurationError(
            f"{location} cannot be read for the decision rule ({type(error).__name__})"
        ) from error
    if not isinstance(metadata, dict):
        raise ModelConfigurationError(f"{location} is not a JSON object")

    def refuse(reason: str) -> ModelConfigurationError:
        return ModelConfigurationError(
            f"{location}: {reason}. Refusing to start: serving any other decision rule "
            "would serve a decision the deployment gate never scored."
        )

    unknown = sorted(set(metadata) - KNOWN_METADATA_KEYS)
    if unknown:
        raise refuse(f"records {unknown}, which this service does not apply")
    if "labels" in metadata and metadata["labels"] != list(LABEL_ORDER):
        raise refuse(f"labels {metadata['labels']!r} are not {list(LABEL_ORDER)}")

    has_temperature = metadata.get("temperature") is not None
    has_thresholds = metadata.get("thresholds") is not None
    if not has_temperature and not has_thresholds:
        return ARGMAX
    if not has_thresholds:
        raise refuse("records a temperature without thresholds")
    if not has_temperature:
        raise refuse("records thresholds without a temperature")

    temperature = metadata["temperature"]
    if not _is_number(temperature) or temperature <= 0:
        raise refuse(f"temperature must be a finite number > 0 (found {temperature!r})")
    recorded = metadata["thresholds"]
    if not isinstance(recorded, dict):
        raise refuse(f"thresholds must be an object (found {recorded!r})")
    if recorded.get("rule") != THRESHOLD_RULE:
        raise refuse(
            f"thresholds rule {recorded.get('rule')!r} is not the rule this service "
            f"implements ({THRESHOLD_RULE!r})"
        )
    values = []
    for name in ("critical", "urgent"):
        value = recorded.get(name)
        if not _is_number(value) or not 0.0 <= value <= 1.0:
            raise refuse(
                f"thresholds.{name} must be a number in [0, 1] (found {value!r})"
            )
        values.append(float(value))
    return DecisionRule(
        temperature=float(temperature), thresholds=(values[0], values[1])
    )


def read_training_max_length(model_path: Path) -> int:
    """The max_length the model was fine-tuned at, as its directory records it."""
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
    _rule: DecisionRule
    model_path: Path | None

    @classmethod
    def with_engine(
        cls,
        engine: BatchedInference,
        labels: tuple[str, ...] = LABEL_ORDER,
        rule: DecisionRule = ARGMAX,
    ) -> ModelClassifier:
        """A classifier over an existing engine. Used by tests with a fake forward."""
        classifier = cls.__new__(cls)
        classifier._engine = engine
        classifier._labels = labels
        classifier._rule = rule
        classifier.model_path = None
        return classifier

    def __init__(
        self,
        model_path: Path,
        max_length: int,
        *,
        rule: DecisionRule,
        threads: int | None = None,
    ):
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
        self._rule = rule

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
            logits: list[list[float]] = self._model(**encoded).logits.tolist()
        return calibrated_probabilities(logits, self._rule.temperature)

    def warm_up(self) -> float:
        """Run one inference so a patient does not pay the cold start.

        Returns the milliseconds it took, for the startup log.
        """
        start = time.perf_counter()
        self.classify("mfite umuriro")
        return (time.perf_counter() - start) * 1000.0

    def classify(self, text: str) -> Classification:
        probs = self._engine.infer(text)
        index = self._rule.decide(probs)
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
    rule = read_decision_rule(path)

    try:
        classifier = ModelClassifier(
            path,
            max_length=max_length,
            rule=rule,
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
        decision_rule=rule.describe(),
        warm_up_ms=round(warm_ms, 1),
    )
    return classifier, f"fine-tuned model from {path} (warm-up {warm_ms:.0f} ms)"
