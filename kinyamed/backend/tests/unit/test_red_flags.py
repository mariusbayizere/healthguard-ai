"""The red-flag lexicon: loading, validation and matching (CLAUDE.md L2, §10.6).

EVERY TERM IN THIS FILE IS FICTIONAL ("zorblax", "quenthari", "vellimor"). No real
clinical term appears here or in the shipped lexicon: validated terms come from a
clinical lead (STATE.md H10), and until then the shipped table is empty.
"""

from __future__ import annotations

import csv
from pathlib import Path

import pytest
from app.models.triage_result import UrgencyLevel
from app.services import red_flags as rf

SHIPPED = Path(__file__).resolve().parents[3] / "data" / "lexicon" / "red_flags.csv"


def _row(**overrides: str) -> dict[str, str]:
    row = dict.fromkeys(rf.COLUMNS, "")
    row.update(
        concept_id="FAKE01",
        en="zorblax fever",
        red_flag="true",
        source="fixture: fictional term, not clinical",
        validated_by="FIXTURE",
        date="2026-09-15",
    )
    row.update(overrides)
    return row


def _write(tmp_path: Path, rows: list[dict[str, str]], header=rf.COLUMNS) -> Path:
    path = tmp_path / "red_flags.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, list(header), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _refusal(path: Path) -> str:
    with pytest.raises(rf.RedFlagLexiconError) as refused:
        rf.load_lexicon(path)
    return str(refused.value)


# ── The shipped table ─────────────────────────────────────────────────────────
def test_the_columns_are_the_section_10_6_lexicon_columns():
    assert rf.COLUMNS == (
        "concept_id",
        "icd11_or_snomed",
        "en",
        "fr",
        "sw",
        "rw",
        "rw_colloquial_variants",
        "sw_variant",
        "register",
        "red_flag",
        "source",
        "validated_by",
        "date",
    )


def test_the_shipped_lexicon_is_empty_and_loads_as_a_no_op():
    with SHIPPED.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.reader(handle))
    assert rows == [list(rf.COLUMNS)], (
        "the shipped lexicon must hold a header and no terms"
    )
    lexicon = rf.load_lexicon(SHIPPED)
    assert lexicon.is_empty
    assert not lexicon.match("zorblax fever and anything else").triggered


# ── Rejection at load ─────────────────────────────────────────────────────────
@pytest.mark.parametrize("missing", ["source", "validated_by"])
def test_a_row_without_source_or_validator_is_rejected_by_line(tmp_path, missing):
    path = _write(tmp_path, [_row(), _row(concept_id="FAKE02", **{missing: ""})])
    with pytest.raises(rf.RedFlagLexiconError) as refused:
        rf.load_lexicon(path)
    message = str(refused.value)
    assert "line 3" in message and "FAKE02" in message and missing in message


def test_a_row_without_both_names_both(tmp_path):
    path = _write(tmp_path, [_row(source="", validated_by="")])
    message = _refusal(path)
    assert "source" in message and "validated_by" in message


@pytest.mark.parametrize(
    ("overrides", "needle"),
    [
        ({"concept_id": "has space"}, "concept_id"),
        ({"red_flag": "maybe"}, "red_flag"),
        ({"date": "15/09/2026"}, "date"),
        ({"en": ""}, "no term"),
    ],
)
def test_malformed_rows_are_rejected(tmp_path, overrides, needle):
    path = _write(tmp_path, [_row(**overrides)])
    assert needle in _refusal(path)


def test_a_duplicate_concept_is_rejected(tmp_path):
    path = _write(tmp_path, [_row(), _row(en="vellimor")])
    assert "duplicate" in _refusal(path)


def test_a_wrong_header_is_rejected(tmp_path):
    path = _write(tmp_path, [], header=("concept_id", "en", "red_flag"))
    assert "header" in _refusal(path)


def test_a_missing_file_is_an_error_not_an_empty_lexicon(tmp_path):
    with pytest.raises(rf.RedFlagLexiconError, match="not found"):
        rf.load_lexicon(tmp_path / "absent.csv")


# ── Matching ──────────────────────────────────────────────────────────────────
def _lexicon(tmp_path: Path) -> rf.RedFlagLexicon:
    return rf.load_lexicon(
        _write(
            tmp_path,
            [
                _row(),
                _row(
                    concept_id="FAKE02",
                    en="",
                    rw="quenthari",
                    rw_colloquial_variants="kwenthari|quen thari",
                ),
                _row(concept_id="FAKE03", en="vellimor", red_flag="false"),
            ],
        )
    )


@pytest.mark.parametrize(
    "text",
    [
        "I have zorblax fever",
        "ZORBLAX   FEVER since morning",
        "zörblax fèver",  # accents dropped on feature-phone keypads
        "fixture: zorblax fever.",
    ],
)
def test_terms_match_whole_words_regardless_of_case_accents_and_spacing(tmp_path, text):
    match = _lexicon(tmp_path).match(text)
    assert match.concept_ids == ("FAKE01",)


def test_colloquial_variants_match_and_ids_are_sorted_and_unique(tmp_path):
    match = _lexicon(tmp_path).match("kwenthari, zorblax fever, quenthari")
    assert match.concept_ids == ("FAKE01", "FAKE02")


@pytest.mark.parametrize("text", ["zorblaxian feverish", "vellimor", "nothing here"])
def test_no_match_inside_words_and_non_red_flag_rows_never_match(tmp_path, text):
    assert not _lexicon(tmp_path).match(text).triggered


# ── Escalation ────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("model", list(UrgencyLevel))
def test_a_match_escalates_to_critical_whatever_the_model_said(tmp_path, model):
    decision = rf.apply(model, _lexicon(tmp_path).match("zorblax fever"))
    assert decision.urgency is UrgencyLevel.CRITICAL
    assert decision.triggered and decision.reason == "red_flag:FAKE01"
    assert decision.model_urgency is model


@pytest.mark.parametrize("model", list(UrgencyLevel))
def test_no_match_leaves_the_model_urgency_untouched(tmp_path, model):
    decision = rf.apply(model, _lexicon(tmp_path).match("nothing here"))
    assert decision.urgency is model
    assert not decision.triggered and decision.reason is None


def test_the_reason_holds_concept_ids_only_and_fits_the_column():
    ids = tuple(f"FAKE{k:03d}" for k in range(60))
    reason = rf.format_reason(ids)
    assert reason is not None and len(reason) <= 200
    assert reason.startswith("red_flag:FAKE000,FAKE001")
    assert reason.endswith("more")
