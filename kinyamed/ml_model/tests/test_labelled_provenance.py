"""A metric from the labelled corpus must never appear without its provenance.

WHY THIS TEST EXISTS. The labels in `dataset/labelled/triage_labels_ALL.csv`
were assigned by one person who is not a clinician, with no second annotator and
no agreement statistic. A figure computed from them, quoted without that caveat,
is indistinguishable on the page from a figure computed against clinical ground
truth. This paper's whole argument is that such a figure is a defect, so the
caveat is enforced rather than remembered.

The rule: any report file that prints a number derived from this corpus must
also print the provenance line. Not a paraphrase of it, the line itself, so it
cannot weaken by degrees across rewrites.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

lc = pytest.importorskip("dataset.labelled_corpus")

REPORTS = ROOT.parent / "reports"

# Files that report on the labelled corpus. A new one must be added here, which
# is the point: adding a report is a deliberate act and so is its caveat.
LABELLED_REPORTS = (
    REPORTS / "LABELLED_CORPUS.md",
    REPORTS / "labelled_missing_text.csv",
    REPORTS / "labelled_missing_ids.txt",
    REPORTS / "labelled_record_voice.csv",
)

# The substrings that make the caveat what it is. Present together, in order,
# the reader has been told who labelled, that nobody validated, and that the
# result is not ground truth.
REQUIRED = (
    "annotator single, non-clinician",
    "validated_by NONE",
    "NOT clinical ground truth",
)


def test_provenance_line_carries_all_three_facts() -> None:
    line = lc.provenance_line()
    for fragment in REQUIRED:
        assert fragment in line, f"the provenance line no longer states: {fragment}"


@pytest.mark.parametrize("path", LABELLED_REPORTS, ids=lambda p: p.name)
def test_every_labelled_report_carries_the_provenance(path: Path) -> None:
    if not path.exists():
        pytest.skip(f"{path.name} not generated yet")
    head = path.read_text(encoding="utf-8")
    for fragment in REQUIRED:
        assert fragment in head, (
            f"{path.name} reports on the labelled corpus but does not state "
            f"'{fragment}'. Regenerate with review/report_labelled_corpus.py."
        )


@pytest.mark.parametrize("path", LABELLED_REPORTS, ids=lambda p: p.name)
def test_the_caveat_precedes_the_first_number(path: Path) -> None:
    """A caveat below the figures is read after the figures, or not at all."""
    if not path.exists():
        pytest.skip(f"{path.name} not generated yet")
    text = path.read_text(encoding="utf-8")
    where = text.find("NOT clinical ground truth")
    assert where != -1, f"{path.name} does not carry the caveat at all"

    before = text[:where]
    # Ignore digits inside the file's own header text and any sha256.
    stripped = re.sub(r"\b[0-9a-f]{16,}\b", "", before)
    numbers = re.findall(r"(?<![\w.])\d[\d,]*(?![\w])", stripped)
    assert not numbers, (
        f"{path.name} prints {numbers[:5]} before the provenance caveat; the "
        "caveat must come first, not as a footer"
    )


def test_rows_without_text_are_excluded_from_measurement_not_dropped() -> None:
    """201 unwritten rows must stay in the file and out of every count."""
    rows = lc.load()
    blank = [r for r in rows if not r.has_text]
    assert blank, "no rows without text; has the corpus been filtered in place?"
    assert len(lc.measurable(rows)) == len(rows) - len(blank)
    assert lc.diversity(rows)["rows_with_text"] == len(rows) - len(blank)


def test_cannot_classify_is_not_a_triage_label() -> None:
    """It is a judgement that the text does not support a decision."""
    assert "CANNOT CLASSIFY" in lc.LABELS
    assert "CANNOT CLASSIFY" not in lc.TRIAGE_LABELS


def test_the_tokeniser_keeps_apostrophes_inside_words() -> None:
    """Kinyarwanda elides with an apostrophe; splitting on it inflates types."""
    assert lc.tokenise("n'umwana y'umuntu") == ["n'umwana", "y'umuntu"]
    assert lc.tokenise("Yaje, arwaye.") == ["yaje", "arwaye"]
