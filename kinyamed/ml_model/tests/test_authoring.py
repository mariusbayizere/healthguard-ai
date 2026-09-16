"""annotation/authoring.py: the pilot authoring instrument (EVAL_SET_SPEC §7, CORPUS_REBUILD §3).

The instrument holds what a native-speaker clinician author fills in. It contains NO
vignette text and NO urgency label:
  * the text is written by native Kinyarwanda authors (ENGINEERING_SPEC §10.2 T1);
  * the label is the annotator's job, and pre-labelling would anchor them
    (annotation/store.py already refuses an urgency column at import).

What is tested here is the instrument and the gates it enforces at authoring time, not
any clinical content. Every fixture below uses placeholder tokens, never a symptom.
"""

from __future__ import annotations

import csv

import pytest
from annotation import authoring

PLACEHOLDER = "<<to be written by the author>>"


def _row(**overrides):
    row = {
        "item_id": "kw-0001",
        "text": PLACEHOLDER,
        "language": "kinyarwanda",
        "split": "test",
        "scenario_id": "kw-seed-0001",
        "seed_id": "kw-seed-0001",
        "reporter": "self",
        "patient_age_group": "adult",
        "domain": "DOMAIN-1",
        "voice": "first_person",
        "length": "sentence",
        "negation": "no",
        "multiple_complaints": "no",
        "register": "everyday",
        "author_code": "A1",
        "generation_method": "native_author",
        "validated_by": "PENDING",
        "date": "2026-09-16",
    }
    row.update(overrides)
    return row


def _rows(n, **overrides):
    """Five authors by default: G8 caps any author at 20% of a language x domain."""
    return [
        _row(
            item_id=f"kw-{k:04d}",
            scenario_id=f"kw-seed-{k:04d}",
            seed_id=f"kw-seed-{k:04d}",
            **{
                "author_code": f"A{k % 5}",
                # Distinct placeholder tokens: identical text on two seeds is an exact
                # duplicate, and G4 is right to refuse it.
                "text": f"placeholder alpha{k} beta{k} gamma{k} delta{k}",
                **overrides,
            },
        )
        for k in range(n)
    ]


# ── The sheet itself ──────────────────────────────────────────────────────────
def test_the_sheet_carries_no_urgency_column_and_no_text(tmp_path):
    """Two separate refusals: the label anchors the annotator, the text is the author's."""
    path = authoring.write_sheet(
        tmp_path / "sheet.csv", language="kinyarwanda", items=12, domains=None
    )
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert len(rows) == 12
    assert not any(c.lower() in {"urgency", "gold_label", "label"} for c in rows[0])
    assert {r["text"] for r in rows} == {""}
    assert {r["validated_by"] for r in rows} == {"PENDING"}


def test_every_sheet_row_carries_the_metadata_the_grid_and_the_gates_need():
    assert set(authoring.SHEET_COLUMNS) >= {
        "item_id",
        "text",
        "language",
        "split",
        "scenario_id",
        "seed_id",
        "reporter",
        "patient_age_group",
        "domain",
        "voice",
        "length",
        "negation",
        "multiple_complaints",
        "register",
        "author_code",
        "generation_method",
        "validated_by",
        "date",
    }


def test_the_domain_column_is_left_blocked_until_a_ratified_taxonomy_exists(tmp_path):
    """EVAL_SET_SPEC §7: the domain axis comes from the national triage protocol, which is
    not in the repository (H4). The instrument must not invent one."""
    path = authoring.write_sheet(
        tmp_path / "s.csv", language="kinyarwanda", items=3, domains=None
    )
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert {r["domain"] for r in rows} == {authoring.BLOCKED}
    assert authoring.BLOCKED_AXES["domain"].startswith("docs/clinical/")


def test_a_ratified_domain_list_is_used_when_one_is_supplied(tmp_path):
    domains = tmp_path / "domains.csv"
    domains.write_text("domain,source\nD-A,MoH protocol p.12\nD-B,MoH protocol p.13\n")
    path = authoring.write_sheet(
        tmp_path / "s.csv", language="kinyarwanda", items=4, domains=domains
    )
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    assert {r["domain"] for r in rows} == {"D-A", "D-B"}


def test_a_domain_list_without_a_source_for_every_domain_is_refused(tmp_path):
    domains = tmp_path / "domains.csv"
    domains.write_text("domain,source\nD-A,MoH protocol p.12\nD-B,\n")
    with pytest.raises(authoring.AuthoringError, match="source"):
        authoring.write_sheet(
            tmp_path / "s.csv", language="kinyarwanda", items=2, domains=domains
        )


# ── Gates enforced at authoring time (CORPUS_REBUILD §3) ──────────────────────
def test_a_clean_sheet_passes_every_gate_that_can_be_checked():
    problems = authoring.check_rows(_rows(40), scope="pilot")
    assert problems == []


def test_g1_more_than_fifty_rows_from_one_seed_is_refused():
    extra = [
        _row(item_id=f"dup-{k}", seed_id="kw-seed-0000", scenario_id=f"sc-{k}")
        for k in range(51)
    ]
    rows = [*_rows(40), *extra]
    problems = authoring.check_rows(rows, scope="pilot")
    assert any(p.startswith("G1") and "kw-seed-0000" in p for p in problems)


def test_g5_a_machine_person_transformation_is_refused():
    rows = [*_rows(5), _row(item_id="x-1", generation_method="person_transform")]
    problems = authoring.check_rows(rows, scope="pilot")
    assert any(p.startswith("G5") and "person_transform" in p for p in problems)


def test_g5_a_first_and_third_person_pair_from_one_author_is_refused():
    """The ban is enforced on metadata, not by a concord detector (CORPUS_REBUILD §3)."""
    rows = [
        *_rows(5),
        _row(
            item_id="p-1",
            seed_id="s-p",
            scenario_id="sc-p1",
            voice="first_person",
            author_code="A9",
            text="alpha beta gamma",
        ),
        _row(
            item_id="p-2",
            seed_id="s-p",
            scenario_id="sc-p2",
            voice="reported",
            author_code="A9",
            text="alpha beta gamma",
        ),
    ]
    problems = authoring.check_rows(rows, scope="pilot")
    assert any(p.startswith("G5") and "A9" in p for p in problems)


def test_the_same_pair_from_two_different_authors_is_allowed():
    rows = [
        *_rows(5),
        _row(
            item_id="p-1",
            seed_id="s-p",
            scenario_id="sc-p1",
            voice="first_person",
            author_code="A9",
            text="alpha beta gamma",
        ),
        _row(
            item_id="p-2",
            seed_id="s-p",
            scenario_id="sc-p2",
            voice="reported",
            author_code="B2",
            text="alpha beta gamma",
        ),
    ]
    assert not any(
        p.startswith("G5") for p in authoring.check_rows(rows, scope="pilot")
    )


def test_g7_a_row_missing_provenance_is_refused():
    rows = [*_rows(5), _row(item_id="n-1", author_code="")]
    problems = authoring.check_rows(rows, scope="pilot")
    assert any(p.startswith("G7") and "author_code" in p for p in problems)


def test_g8_one_author_writing_more_than_a_fifth_of_a_language_and_domain_is_refused():
    rows = _rows(10, author_code="A1")  # one author, one domain
    problems = authoring.check_rows(rows, scope="pilot")
    assert any(p.startswith("G8") and "A1" in p for p in problems)


def test_g4_near_duplicate_seeds_above_two_percent_are_refused():
    shared = "alpha beta gamma delta epsilon zeta eta theta iota kappa lambda mu nu xi omicron pi rho sigma tau"
    rows = _rows(50, author_code="A1")
    for k, r in enumerate(rows):
        r["text"] = f"{shared} unique{k}"
        r["author_code"] = f"A{k % 6}"
    problems = authoring.check_rows(rows, scope="pilot")
    assert any(p.startswith("G4") for p in problems)


def test_an_urgency_column_in_a_returned_sheet_is_refused():
    rows = _rows(3)
    rows[0]["urgency"] = "CRITICAL"
    problems = authoring.check_rows(rows, scope="pilot")
    assert any("urgency" in p and "label" in p for p in problems)


def test_the_test_split_allows_only_one_item_per_scenario():
    """EVAL_SET_SPEC §8: paraphrase variants may exist only in the calibration split."""
    rows = [
        *_rows(4),
        _row(item_id="t-2", scenario_id="kw-seed-0001", seed_id="kw-seed-0001"),
    ]
    problems = authoring.check_rows(rows, scope="pilot")
    assert any("scenario" in p and "test" in p for p in problems)
    calibration = [dict(r, split="calibration") for r in rows]
    assert not any(
        "scenario" in p and "test" in p
        for p in authoring.check_rows(calibration, scope="pilot")
    )


# ── Capacity: where each gate binds ───────────────────────────────────────────
def test_capacity_reports_where_each_gate_binds_for_the_kinyarwanda_pilot():
    capacity = authoring.capacity(
        language="kinyarwanda", items=2354, authors=5, domains=None
    )
    binding = {c["gate"]: c for c in capacity}
    assert (
        binding["G1"]["binds_at_items"] is None
        or binding["G1"]["binds_at_items"] >= 2354
    )
    assert binding["G8"]["minimum_authors"] == 5
    assert binding["G2"]["cells_unknown"] is True  # the domain axis is BLOCKED
    assert any("domain" in c.get("blocked_by", "") for c in capacity)


def test_capacity_says_how_many_authors_a_set_size_needs():
    assert authoring.minimum_authors(items_in_language_and_domain=100) == 5
    assert authoring.minimum_authors(items_in_language_and_domain=1) == 1


def test_the_report_names_every_blocked_axis():
    text = authoring.report(language="kinyarwanda", items=2354, authors=5, domains=None)
    assert "BLOCKED" in text
    assert "domain" in text and "H4" in text
    assert "no urgency label" in text.lower()
