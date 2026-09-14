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

import threading
import time
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


class ModelClassifier:
    """Fine-tuned sequence classifier implementing `SymptomClassifier`."""

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
        self._lock = threading.Lock()

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

    def warm_up(self) -> float:
        """Run one inference so a patient does not pay the cold start.

        Returns the milliseconds it took, for the startup log.
        """
        start = time.perf_counter()
        self.classify("mfite umuriro")
        return (time.perf_counter() - start) * 1000.0

    def classify(self, text: str) -> Classification:
        torch = self._torch
        # A single lock around inference. torch is not guaranteed thread-safe
        # for concurrent forward passes on one module instance, and correctness
        # outranks throughput on a two-core box serving one clinic.
        with self._lock, torch.no_grad():
            encoded = self._tokenizer(
                text, return_tensors="pt", truncation=True, max_length=self._max_length
            )
            logits = self._model(**encoded).logits
            probs = torch.softmax(logits, dim=-1)[0]
            index = int(probs.argmax())
            confidence = float(probs[index])
        label = self._labels[index]
        urgency = _URGENCY[label]
        # Urgency and confidence only: the model names no condition and writes
        # no advice. What a patient reads is `patient_message.patient_receipt`.
        return Classification(urgency=urgency, confidence=confidence)


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

    try:
        classifier = ModelClassifier(
            path,
            max_length=settings.MODEL_MAX_LENGTH,
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
    logger.info("triage_model_loaded", path=str(path), warm_up_ms=round(warm_ms, 1))
    return classifier, f"fine-tuned model from {path} (warm-up {warm_ms:.0f} ms)"
