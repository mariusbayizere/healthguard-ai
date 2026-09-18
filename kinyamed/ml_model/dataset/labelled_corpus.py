"""The labelled Kinyarwanda triage corpus: loader, provenance, and the tokeniser.

PROVENANCE IS NOT OPTIONAL HERE. Every label in this corpus was assigned by one
person, who is the author of the paper and is not a clinician. There is no
second annotator, so there is no inter-rater agreement: not a low figure, none.
Nothing computed from this corpus is clinical ground truth and it must never be
described as such.

That statement travels with the data rather than beside it. `PROVENANCE` below
is the canonical wording, `provenance_line()` is what every report prints, and
`tests/test_labelled_provenance.py` fails any report that emits a metric from
this corpus without it. A number from this corpus without that caveat is
precisely the defect this project keeps finding in its own work.

THE TOKENISER IS PART OF THE MEASUREMENT. Kinyarwanda writes elided vowels with
an apostrophe (`n'umwana`, `y'umuntu`), so a `\\w+` regex splits one word into
two and inflates the type count while deflating type/token ratio. Splitting on
whitespace and stripping edge punctuation keeps those whole. The two give
materially different answers on this corpus (3,524 types at TTR 0.180 against
3,930 at TTR 0.210), so the choice is recorded here and used everywhere rather
than re-decided per script.

ROWS WITHOUT TEXT ARE EXCLUDED FROM MEASUREMENT, NOT DROPPED. 201 rows carry a
label and no Kinyarwanda. They are real work outstanding, so they stay in the
file, are reported by id, and are excluded from every count by `measurable()`.
Silently dropping them would understate the corpus and hide the gap.
"""

from __future__ import annotations

import csv
import hashlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "dataset" / "labelled" / "triage_labels_ALL.csv"

# The exact wording. Reports quote this; they do not paraphrase it.
PROVENANCE = {
    "annotator": "single, non-clinician, the paper's author",
    "validated_by": "NONE",
    "inter_rater_agreement": "none computed; there is no second annotator",
    "status": "NOT clinical ground truth",
}

LABELS = ("ROUTINE", "URGENT", "CRITICAL", "CANNOT CLASSIFY")

# Labels that a model could be trained or scored on. CANNOT CLASSIFY is a
# judgement that the text does not support a triage decision; it is not a
# fourth urgency class and must not be folded into one.
TRIAGE_LABELS = ("ROUTINE", "URGENT", "CRITICAL")

# Clinical-record voice: a third party reporting what the patient said, rather
# than the patient's or carer's own words. The corpus is patient-voice by
# definition, so these are the wrong construct, not a style preference.
RECORD_VOICE_MARKERS = ("avuga ko", "yabwiwe ko")

# Characters stripped from the edge of a whitespace-delimited token. The
# apostrophe is deliberately NOT here: it is part of the word in Kinyarwanda.
EDGE_PUNCTUATION = ".,;:!?()\"“”"


def tokenise(text: str) -> list[str]:
    """Lowercase, split on whitespace, strip edge punctuation. See module docstring."""
    return [w for w in (t.strip(EDGE_PUNCTUATION) for t in text.lower().split()) if w]


def provenance_line() -> str:
    """The one-line caveat every report carries. Printed, never paraphrased."""
    return (
        f"PROVENANCE: annotator {PROVENANCE['annotator']}; "
        f"validated_by {PROVENANCE['validated_by']}; "
        f"{PROVENANCE['inter_rater_agreement']}. "
        f"These labels are {PROVENANCE['status']}."
    )


@dataclass(frozen=True)
class Row:
    id: int
    cue: str
    reporter: str
    age_group: str
    text: str
    label: str

    @property
    def has_text(self) -> bool:
        return bool(self.text.strip())

    @property
    def record_voice(self) -> bool:
        low = self.text.lower()
        return self.has_text and any(m in low for m in RECORD_VOICE_MARKERS)

    @property
    def register(self) -> str:
        """`record_voice` or `patient_voice`; empty when there is no text to judge."""
        if not self.has_text:
            return ""
        return "record_voice" if self.record_voice else "patient_voice"


def load(path: Path | None = None) -> list[Row]:
    """Every row, including those with no text. Use measurable() to count."""
    path = path or CORPUS
    # utf-8-sig: the file carries a BOM, and without this the first column name
    # becomes '﻿id' and every lookup of 'id' fails.
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [
            Row(
                id=int(r["id"]),
                cue=(r.get("cue") or "").strip(),
                reporter=(r.get("reporter") or "").strip(),
                age_group=(r.get("age_group") or "").strip(),
                text=(r.get("text_kw") or "").strip(),
                label=(r.get("label") or "").strip(),
            )
            for r in csv.DictReader(handle)
        ]


def measurable(rows: list[Row]) -> list[Row]:
    """Rows a count may include: those that actually carry Kinyarwanda text."""
    return [r for r in rows if r.has_text]


def digest(path: Path | None = None) -> str:
    """SHA-256 of the corpus file, for a run manifest."""
    path = path or CORPUS
    return hashlib.sha256(path.read_bytes()).hexdigest()


def missing_ids(rows: list[Row]) -> list[int]:
    """Ids absent from the contiguous range. Unwritten, not lost."""
    present = {r.id for r in rows}
    return [i for i in range(min(present), max(present) + 1) if i not in present]


def as_ranges(values: list[int]) -> list[tuple[int, int]]:
    """Collapse a sorted int list into inclusive ranges."""
    if not values:
        return []
    out, start, prev = [], values[0], values[0]
    for value in values[1:]:
        if value == prev + 1:
            prev = value
        else:
            out.append((start, prev))
            start = prev = value
    out.append((start, prev))
    return out


def diversity(rows: list[Row]) -> dict:
    """Type/token measures over rows that carry text. Tokeniser as above."""
    texts = [r.text for r in measurable(rows)]
    types: Counter[str] = Counter()
    for text in texts:
        types.update(tokenise(text))
    tokens = sum(types.values())
    lengths = sorted(len(tokenise(t)) for t in texts)
    return {
        "rows_with_text": len(texts),
        "distinct_sentences": len(set(texts)),
        "word_types": len(types),
        "word_tokens": tokens,
        "ttr": round(len(types) / tokens, 4) if tokens else 0.0,
        "hapax": sum(1 for _, n in types.items() if n == 1),
        "median_length": lengths[len(lengths) // 2] if lengths else 0,
        "min_length": lengths[0] if lengths else 0,
        "max_length": lengths[-1] if lengths else 0,
    }
