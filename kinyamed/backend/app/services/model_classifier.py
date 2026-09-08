"""C1 — the fine-tuned classifier behind the `SymptomClassifier` seam.

`triage_service.py` already declared this seam: the keyword baseline implements
`SymptomClassifier`, and the fine-tuned model replaces it by implementing the
same protocol and being returned from `get_classifier()`. This module is that
implementation. The protocol is unchanged and no caller changes.

TORCH IS AN OPTIONAL DEPENDENCY, ON PURPOSE
-------------------------------------------
`backend/requirements.txt` says the ML dependencies "belong to
kinyamed/ml_model and are intentionally not installed into the API image".
That decision is respected rather than reversed: torch and transformers are
imported lazily, and an API image without them keeps running on the keyword
baseline. Adding ~2 GB to every API container to serve a 449 MB model is a
deployment choice for the maintainer, not something to smuggle in via an import.

So this module has three outcomes and says which one it took, loudly:

  1. TRIAGE_MODEL_PATH unset            -> baseline, logged as a deliberate default
  2. set but torch/model unavailable    -> baseline, logged as a WARNING with why
  3. set and loadable                   -> model, logged with the path it loaded

It never fails a request because the model is missing, and it never silently
serves the baseline while configuration claims otherwise.

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
from app.services.triage_service import Classification, KeywordClassifier

logger = structlog.get_logger(__name__)

# The model's label order, fixed by training/config.py. Read from the loaded
# model's own id2label where present; this is the fallback and the check.
LABEL_ORDER = ("CRITICAL", "URGENT", "ROUTINE")

_URGENCY = {
    "CRITICAL": UrgencyLevel.CRITICAL,
    "URGENT": UrgencyLevel.URGENT,
    "ROUTINE": UrgencyLevel.ROUTINE,
}

# Reused verbatim from the baseline so a switch of classifier does not silently
# change the advice text a patient receives.
_ADVICE = {
    UrgencyLevel.CRITICAL: "Ikibazo cyawe ni CRITICAL. Jya kwa muganga ako kanya.",
    UrgencyLevel.URGENT: "Ikibazo cyawe ni URGENT. Jya kwa muganga vuba bishoboka.",
    UrgencyLevel.ROUTINE: "Ikibazo cyawe ni ROUTINE. Uzabona muganga vuba.",
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
            str(tokenizer_dir if tokenizer_dir.exists() else model_path))
        self._model = AutoModelForSequenceClassification.from_pretrained(str(model_path))
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
        with self._lock:
            with torch.no_grad():
                encoded = self._tokenizer(text, return_tensors="pt", truncation=True,
                                          max_length=self._max_length)
                logits = self._model(**encoded).logits
                probs = torch.softmax(logits, dim=-1)[0]
                index = int(probs.argmax())
                confidence = float(probs[index])
        label = self._labels[index]
        urgency = _URGENCY[label]
        return Classification(
            urgency=urgency,
            # The model predicts urgency only. It was never trained to name a
            # condition, and inventing one here would put a diagnosis in front
            # of a patient that nothing produced.
            possible_conditions="",
            confidence=confidence,
            advice_rw=_ADVICE[urgency],
        )


def build_classifier() -> tuple[object, str]:
    """Return (classifier, a one-line description of what was selected and why)."""
    raw = getattr(settings, "TRIAGE_MODEL_PATH", "") or ""
    if not raw:
        return KeywordClassifier(), (
            "keyword baseline (TRIAGE_MODEL_PATH unset — this is the default, "
            "not a failure)"
        )

    path = Path(raw).expanduser()
    if not path.exists():
        logger.warning("triage_model_missing", path=str(path),
                       action="falling back to the keyword baseline")
        return KeywordClassifier(), f"keyword baseline (no model at {path})"

    try:
        classifier = ModelClassifier(
            path,
            max_length=getattr(settings, "MODEL_MAX_LENGTH", 96),
            threads=getattr(settings, "TRIAGE_MODEL_THREADS", None),
        )
    except ImportError as error:
        logger.warning("triage_model_deps_missing", error=str(error),
                       action="falling back to the keyword baseline",
                       hint="torch/transformers are deliberately not in the API image")
        return KeywordClassifier(), f"keyword baseline (torch unavailable: {error})"
    except Exception as error:  # a bad artefact must not take the service down
        logger.error("triage_model_load_failed", path=str(path), error=str(error),
                     action="falling back to the keyword baseline")
        return KeywordClassifier(), f"keyword baseline (model failed to load: {error})"

    warm_ms = classifier.warm_up()
    logger.info("triage_model_loaded", path=str(path), warm_up_ms=round(warm_ms, 1))
    return classifier, f"fine-tuned model from {path} (warm-up {warm_ms:.0f} ms)"
