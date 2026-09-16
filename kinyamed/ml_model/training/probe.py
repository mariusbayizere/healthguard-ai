#!/usr/bin/env python
"""A malfunction probe for a served model. **NOT A GATE METRIC.**

    python training/probe.py --model ~/kinyamed-runs/model_v2d_freeze8_lr1e-5 \\
        --texts dataset/processed/eval_phrase_holdout.csv --limit 200

WHAT THIS IS
------------
Six checks that need no clinical judgement and no gold labels, each answering "is this
model grossly broken?":

  determinism            the same text twice gives the same probabilities
  surface invariance     capitalisation, punctuation, spacing and typos do not change the
                         predicted class (a corpus-health signal, never a quality claim)
  class collapse         the model does not answer one class for everything
  label order            the checkpoint's id2label is the dataset's order; an off-by-one
                         here maps CRITICAL to ROUTINE silently (ENGINEERING_SPEC §3.5)
  probability validity   three finite probabilities in [0, 1] summing to 1
  input encoding         the tokenizer actually loaded has a real vocabulary and does not
                         turn the text into unknown tokens
  length robustness      a long input neither crashes nor produces invalid output

WHAT THIS IS NOT
----------------
It is not accuracy, and it is not a deployment gate. The gate is `training/evaluate.py`
on a held-out set meeting EVAL_SET_SPEC; no such set exists, so no quality number may be
reported (ENGINEERING_SPEC L6). Nothing here is written into a model card, a README or a
paper. `evaluate.py` does not import this module, and a test enforces that.

CLINICAL PROBE ITEMS
--------------------
An item asserting that some text is CRITICAL is a clinical claim: it needs a cited
source and a named validator (L5, §10.6). `data/probe/urgency_probe.csv` therefore ships
with a header and no rows, like `data/lexicon/red_flags.csv`. Even once filled, the
report prints the model's answers item by item and **no score**: a set small enough to
read is too small to measure anything.
"""

from __future__ import annotations

import argparse
import csv
import math
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dataset.labels import CLASS_ORDER, ID_TO_LABEL  # noqa: E402

NOT_A_GATE = "NOT A GATE METRIC"
URGENCY_PROBE_PATH = "data/probe/urgency_probe.csv"
URGENCY_PROBE_COLUMNS = (
    "item_id",
    "text",
    "expected_urgency",
    "source",
    "validated_by",
)

#: One class taking more than this share of a varied set is a collapse signal, not a
#: quality judgement: it is the shape of a model that has stopped discriminating.
COLLAPSE_SHARE = 0.95
#: Real patients type in mixed case, with and without punctuation, with stray spaces and
#: with typos. Each variant below is a deterministic, content-preserving perturbation of
#: the surface only. The flip rate under them is a CORPUS-HEALTH signal.
SURFACE_NOTE = (
    "a corpus-health signal, not a quality claim: a model that changes its answer under "
    "surface variation has learned the corpus's uniform surface, not the task"
)
#: Engineering default, not a clinical or gate threshold, and never used to pass anything.
SURFACE_FLIP_SIGNAL = 0.05
PUNCTUATION = ",.;:!?"


def _strip_punctuation(text: str) -> str:
    return "".join(c for c in text if c not in PUNCTUATION)


def _loosen_whitespace(text: str) -> str:
    return "  " + "  ".join(text.split()) + " "


def _typo(text: str) -> str:
    """One edit in every third word: adjacent-character swap, or a doubled first letter."""
    words = text.split()
    out = []
    for index, word in enumerate(words):
        if index % 3 == 2 and len(word) >= 4:
            out.append(word[0] + word[2] + word[1] + word[3:])
        elif index % 3 == 2:
            out.append(word[0] + word)
        else:
            out.append(word)
    return " ".join(out)


SURFACE_VARIANTS: dict[str, Callable[[str], str]] = {
    "capitalisation": str.upper,
    "punctuation": _strip_punctuation,
    "whitespace": _loosen_whitespace,
    "typos": _typo,
}
#: Above this share of unknown tokens the model is not reading the text at all. A model
#: directory with no tokenizer files does NOT raise: transformers returns a vocabulary of
#: 5 and every word becomes <unk>, which looks exactly like a collapsed model.
MAX_UNKNOWN_RATE = 0.20
MIN_VOCAB_SIZE = 1000
LONG_INPUT_WORDS = 120

Classifier = Callable[[Sequence[str]], Sequence[Sequence[float]]]


class ProbeError(ValueError):
    """The probe cannot be run or read as given."""


@dataclass
class Report:
    banner: str
    findings: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    observations: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures

    def render(self) -> str:
        lines = [self.banner, ""]
        lines += [f"  {NOT_A_GATE}: {line}" for line in self.findings]
        if self.observations:
            lines += ["", "Observations (no score, no verdict):"]
            lines += [f"  {line}" for line in self.observations]
        lines += ["", f"{len(self.failures)} malfunction signal(s)."]
        lines += [f"  SIGNAL: {line}" for line in self.failures]
        return "\n".join(lines)


def _valid(row: Sequence[float]) -> bool:
    return (
        len(row) == 3
        and all(
            isinstance(v, (int, float)) and math.isfinite(v) and 0.0 <= v <= 1.0
            for v in row
        )
        and abs(sum(row) - 1.0) <= 1e-4
    )


def _argmax(row: Sequence[float]) -> int:
    return max(range(len(row)), key=lambda k: row[k])


def load_urgency_probe(path: Path) -> list[dict[str, str]]:
    """Clinician-supplied probe items. Every row needs a source and a validator."""
    path = Path(path)
    if not path.is_file():
        raise ProbeError(f"{path} does not exist")
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if rows and not set(URGENCY_PROBE_COLUMNS) <= rows[0].keys():
        raise ProbeError(f"{path} needs columns {list(URGENCY_PROBE_COLUMNS)}")
    for row in rows:
        item = row.get("item_id", "?")
        if not (row.get("source") or "").strip():
            raise ProbeError(
                f"probe item {item!r} has no source. An item asserting an urgency is a "
                "clinical claim and cites the document it comes from (ENGINEERING_SPEC L5)"
            )
        validator = (row.get("validated_by") or "").strip()
        if not validator or validator.upper() == "PENDING":
            raise ProbeError(
                f"probe item {item!r} has validated_by={validator or 'empty'!r}: a clinician "
                "must validate it before it is used for anything"
            )
        if (row.get("expected_urgency") or "").strip() not in CLASS_ORDER:
            raise ProbeError(f"probe item {item!r} has no valid expected_urgency")
    return rows


def resolve_tokenizer_dir(model_dir: Path) -> Path:
    """The tokenizer the service would load: `<model>/tokenizer` when it exists."""
    subdirectory = Path(model_dir) / "tokenizer"
    return subdirectory if subdirectory.exists() else Path(model_dir)


def run(
    classify: Classifier,
    texts: Sequence[str],
    *,
    id2label: dict[int, str] | None = None,
    urgency_items: Sequence[dict[str, str]] | None = None,
    encoding: dict[str, object] | None = None,
) -> Report:
    """Run every malfunction check. Never returns a quality number."""
    import numpy as np

    if len(texts) < 10:
        raise ProbeError("a probe needs at least 10 texts to see a collapse")
    report = Report(
        banner=f"{NOT_A_GATE}. Malfunction probe: is the served model grossly broken?"
    )

    first = [list(map(float, row)) for row in classify(list(texts))]
    invalid = [k for k, row in enumerate(first) if not _valid(row)]
    if invalid:
        report.failures.append(
            f"probability validity: {len(invalid)} of {len(first)} outputs are not three finite "
            "probabilities in [0, 1] summing to 1"
        )
    report.findings.append(
        f"probability validity: {len(first) - len(invalid)}/{len(first)} outputs well formed"
    )

    second = [list(map(float, row)) for row in classify(list(texts))]
    drift = [
        k
        for k, (a, b) in enumerate(zip(first, second, strict=True))
        if any(not math.isclose(x, y, abs_tol=1e-9) for x, y in zip(a, b, strict=True))
    ]
    if drift:
        report.failures.append(
            f"determinism: {len(drift)} of {len(texts)} texts gave different probabilities on a "
            "second identical call"
        )
    report.findings.append(
        f"determinism: {len(texts) - len(drift)}/{len(texts)} texts stable across two calls"
    )

    surface_rates: dict[str, float] = {}
    for name, transform in SURFACE_VARIANTS.items():
        altered = [
            list(map(float, row)) for row in classify([transform(t) for t in texts])
        ]
        flips = sum(
            1
            for base, other in zip(first, altered, strict=True)
            if _valid(base) and _valid(other) and _argmax(other) != _argmax(base)
        )
        surface_rates[name] = flips / len(texts)
    report.findings.append(
        "surface invariance (flip rate by variant): "
        + ", ".join(f"{name} {rate:.1%}" for name, rate in surface_rates.items())
    )
    report.findings.append(f"surface invariance: {SURFACE_NOTE}")
    fragile = {n: r for n, r in surface_rates.items() if r >= SURFACE_FLIP_SIGNAL}
    if fragile:
        report.failures.append(
            "surface invariance: the predicted class changes under "
            + ", ".join(f"{n} ({r:.1%})" for n, r in fragile.items())
            + f", above the {SURFACE_FLIP_SIGNAL:.0%} engineering default. A corpus-health signal "
            "(CORPUS_REBUILD §3 G9), NOT a quality claim"
        )

    classes = [_argmax(row) for row in first if _valid(row)]
    if classes:
        counts = np.bincount(np.array(classes), minlength=3)
        share = counts.max() / counts.sum()
        distribution = ", ".join(f"{CLASS_ORDER[i]} {counts[i]}" for i in range(3))
        report.findings.append(
            f"class collapse: predicted classes over {len(classes)} texts — {distribution}"
        )
        if share > COLLAPSE_SHARE:
            report.failures.append(
                f"class collapse: {CLASS_ORDER[int(counts.argmax())]} is {share:.0%} of predictions "
                f"(above {COLLAPSE_SHARE:.0%})"
            )

    if classes:
        matrix = np.array([row for row in first if _valid(row)], dtype=float)
        means = ", ".join(
            f"{CLASS_ORDER[i]} {matrix[:, i].mean():.2f}" for i in range(3)
        )
        report.findings.append(f"mean probability per class: {means}")
        report.findings.append(
            f"highest p(CRITICAL) over the sample: {matrix[:, 0].max():.2f}"
        )

    if encoding is not None:
        vocab = int(encoding.get("vocab_size", 0))
        unknown = float(encoding.get("unknown_rate", 0.0))
        report.findings.append(
            f"input encoding: vocabulary {vocab:,} from {encoding.get('source', '?')}, "
            f"{unknown:.1%} unknown tokens"
        )
        if vocab < MIN_VOCAB_SIZE or unknown > MAX_UNKNOWN_RATE:
            report.failures.append(
                f"input encoding: vocabulary {vocab:,} with {unknown:.1%} unknown tokens. The "
                "model is not reading the text; any class distribution below is meaningless"
            )

    recorded = id2label if id2label is not None else ID_TO_LABEL
    if {int(k): str(v) for k, v in recorded.items()} != ID_TO_LABEL:
        report.failures.append(
            f"label order: the checkpoint records {recorded}, the dataset uses {ID_TO_LABEL}. "
            "An off-by-one here maps CRITICAL to ROUTINE with no error"
        )
    report.findings.append(f"label order: {recorded}")

    long_text = " ".join(["placeholder"] * LONG_INPUT_WORDS)
    try:
        long_out = [list(map(float, row)) for row in classify([long_text])]
    except Exception as error:  # noqa: BLE001 — any failure on a long input is a signal
        report.failures.append(
            f"length robustness: a {LONG_INPUT_WORDS}-word input raised {error!r}"
        )
    else:
        if not long_out or not _valid(long_out[0]):
            report.failures.append(
                f"length robustness: a {LONG_INPUT_WORDS}-word input produced {long_out[:1]}"
            )
        report.findings.append(
            f"length robustness: {LONG_INPUT_WORDS}-word input handled"
        )

    if urgency_items:
        answers = [
            list(map(float, row))
            for row in classify([r["text"] for r in urgency_items])
        ]
        report.observations.append(
            f"{len(urgency_items)} clinician-validated probe item(s); the model's answer is listed "
            "per item. No score is computed: a readable set is too small to measure anything."
        )
        for item, row in zip(urgency_items, answers, strict=True):
            predicted = CLASS_ORDER[_argmax(row)] if _valid(row) else "INVALID"
            report.observations.append(
                f"  {item['item_id']}: model says {predicted}; the validated expectation is "
                f"{item['expected_urgency']} (source {item['source']})"
            )
    return report


def _texts_from_csv(path: Path, limit: int) -> list[str]:
    with Path(path).open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows or "text" not in rows[0]:
        raise ProbeError(f"{path} needs a text column")
    step = max(1, len(rows) // limit)
    return [rows[k]["text"] for k in range(0, len(rows), step)][:limit]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Malfunction probe. NOT A GATE METRIC."
    )
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument(
        "--texts", type=Path, required=True, help="CSV with a text column"
    )
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--max-length", type=int, default=96)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--urgency-probe", type=Path, default=ROOT / URGENCY_PROBE_PATH)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)

    import torch
    import transformers

    tokenizer_dir = resolve_tokenizer_dir(args.model)
    tokenizer = transformers.AutoTokenizer.from_pretrained(str(tokenizer_dir))
    model = transformers.AutoModelForSequenceClassification.from_pretrained(
        str(args.model)
    )
    model.eval()
    id2label = {int(k): str(v) for k, v in (model.config.id2label or {}).items()}

    def classify(texts: Sequence[str]) -> list[list[float]]:
        out: list[list[float]] = []
        with torch.no_grad():
            for start in range(0, len(texts), args.batch_size):
                batch = list(texts[start : start + args.batch_size])
                encoded = tokenizer(
                    batch,
                    return_tensors="pt",
                    truncation=True,
                    padding=True,
                    max_length=args.max_length,
                )
                out.extend(torch.softmax(model(**encoded).logits, dim=-1).tolist())
        return out

    sample = _texts_from_csv(args.texts, args.limit)
    encoded = tokenizer(list(sample), truncation=True, max_length=args.max_length)[
        "input_ids"
    ]
    flat = [i for row in encoded for i in row]
    encoding = {
        "vocab_size": tokenizer.vocab_size,
        "unknown_rate": (
            sum(1 for i in flat if i == tokenizer.unk_token_id) / len(flat)
            if flat
            else 1.0
        ),
        "source": tokenizer_dir.name,
    }

    items = []
    try:
        items = load_urgency_probe(args.urgency_probe)
    except ProbeError as error:
        print(f"urgency probe not used: {error}", file=sys.stderr)

    report = run(
        classify,
        sample,
        id2label=id2label,
        urgency_items=items,
        encoding=encoding,
    )
    rendered = report.render()
    print(rendered)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(rendered + "\n", encoding="utf-8")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
