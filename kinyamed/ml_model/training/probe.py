#!/usr/bin/env python
"""A malfunction probe for a served model. **NOT A GATE METRIC.**

    python training/probe.py --model ~/kinyamed-runs/model_v2d_freeze8_lr1e-5 \\
        --texts dataset/processed/eval_phrase_holdout.csv --limit 200

WHAT THIS IS
------------
Six checks that need no clinical judgement and no gold labels, each answering "is this
model grossly broken?":

  determinism            the same text twice gives the same probabilities
  formatting invariance  leading space, trailing space and capitalisation do not change
                         the predicted class
  class collapse         the model does not answer one class for everything
  label order            the checkpoint's id2label is the dataset's order; an off-by-one
                         here maps CRITICAL to ROUTINE silently (ENGINEERING_SPEC §3.5)
  probability validity   three finite probabilities in [0, 1] summing to 1
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


def run(
    classify: Classifier,
    texts: Sequence[str],
    *,
    id2label: dict[int, str] | None = None,
    urgency_items: Sequence[dict[str, str]] | None = None,
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

    variants = [f" {t} " for t in texts] + [t.upper() for t in texts]
    varied = [list(map(float, row)) for row in classify(variants)]
    flips = 0
    for k, base in enumerate(first):
        if not _valid(base):
            continue
        for offset in (0, len(texts)):
            other = varied[k + offset]
            if _valid(other) and _argmax(other) != _argmax(base):
                flips += 1
    if flips:
        report.failures.append(
            f"formatting invariance: {flips} class changes caused by surrounding whitespace or "
            "capitalisation alone"
        )
    report.findings.append(
        f"formatting invariance: {flips} class change(s) from whitespace or case"
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

    tokenizer = transformers.AutoTokenizer.from_pretrained(str(args.model))
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

    items = []
    try:
        items = load_urgency_probe(args.urgency_probe)
    except ProbeError as error:
        print(f"urgency probe not used: {error}", file=sys.stderr)

    report = run(
        classify,
        _texts_from_csv(args.texts, args.limit),
        id2label=id2label,
        urgency_items=items,
    )
    rendered = report.render()
    print(rendered)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(rendered + "\n", encoding="utf-8")
    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
