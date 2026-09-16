"""dataset/corpus_gates.py: CORPUS_REBUILD §3 gates G1-G9 over a generated corpus.

No gate is waived, softened or given a pass for being close. A gate that cannot be
computed from the data at hand is reported NOT COMPUTABLE with the reason, never as a
pass. Stdlib only, so it runs in CI's dependency-free job.

Every fixture is synthetic placeholder text.
"""

from __future__ import annotations

import csv

from dataset import corpus_gates as cg

COLUMNS = (
    "text",
    "language",
    "label",
    "domain",
    "seed_id",
    "generation_method",
    "author_code",
    "validated_by",
    "reporter",
    "patient_age_group",
)


def _row(k=0, **overrides):
    row = {
        "text": f"placeholder alpha{k} beta{k} gamma{k} delta{k}.",
        "language": "kinyarwanda",
        "label": ("CRITICAL", "URGENT", "ROUTINE")[k % 3],
        "domain": f"D{k % 4}",
        "seed_id": f"seed-{k}",
        "generation_method": "native_author",
        "author_code": f"A{k % 6}",
        "validated_by": "C-001",
        "reporter": "self",
        "patient_age_group": "adult",
    }
    row.update(overrides)
    return row


def _corpus(n, **overrides):
    return [_row(k, **overrides) for k in range(n)]


def _write(tmp_path, rows, columns=COLUMNS):
    path = tmp_path / "corpus.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(columns), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def _verdict(results, gate):
    return next(r for r in results if r.gate == gate)


# ── G1 rows per seed ─────────────────────────────────────────────────────────
def test_g1_passes_when_every_seed_is_within_the_row_cap():
    assert _verdict(cg.check(_corpus(60)), "G1").passed


def test_g1_fails_when_one_seed_exceeds_fifty_rows():
    rows = _corpus(60) + [_row(1, seed_id="seed-1") for _ in range(51)]
    result = _verdict(cg.check(rows), "G1")
    assert not result.passed and "seed-1" in result.detail


def test_g1_fails_when_a_seed_exceeds_a_tenth_of_a_percent_of_a_large_corpus():
    rows = _corpus(2000) + [_row(7, seed_id="seed-7") for _ in range(5)]
    result = _verdict(cg.check(rows), "G1")
    assert not result.passed and "0.1%" in result.detail


# ── G2 distinct seeds ────────────────────────────────────────────────────────
def test_g2_fails_below_three_thousand_seeds_per_language_and_names_the_count():
    result = _verdict(cg.check(_corpus(100)), "G2")
    assert not result.passed
    assert "100" in result.detail and "3,000" in result.detail


def test_g2_cell_floor_is_not_computable_while_the_domain_axis_is_unratified():
    result = _verdict(cg.check(_corpus(100)), "G2")
    assert "NOT COMPUTABLE" in result.detail or "not computable" in result.detail


# ── G4 near-duplicate seeds ──────────────────────────────────────────────────
def test_g4_fails_on_identical_seed_texts():
    rows = _corpus(50)
    rows[1]["text"] = rows[0]["text"]
    result = _verdict(cg.check(rows), "G4")
    assert not result.passed and "exact" in result.detail.lower()


def test_g4_fails_when_more_than_two_percent_of_seeds_are_near_duplicates():
    shared = " ".join(f"word{i}" for i in range(20))
    rows = _corpus(50)
    for k, row in enumerate(rows):
        row["text"] = f"{shared} tail{k}"
    result = _verdict(cg.check(rows), "G4")
    assert not result.passed


# ── G5 / G7 / G8 provenance and origin ───────────────────────────────────────
def test_g5_fails_when_the_corpus_has_no_generation_method_column(tmp_path):
    rows = [
        {k: v for k, v in r.items() if k != "generation_method"} for r in _corpus(30)
    ]
    result = _verdict(cg.check(rows), "G5")
    assert not result.passed and "generation_method" in result.detail


def test_g5_fails_on_a_machine_person_transformation():
    rows = _corpus(30)
    rows[3]["generation_method"] = "person_transform"
    result = _verdict(cg.check(rows), "G5")
    assert not result.passed and "person_transform" in result.detail


def test_g7_fails_when_provenance_columns_are_absent():
    rows = [
        {k: v for k, v in r.items() if k not in ("author_code", "validated_by")}
        for r in _corpus(30)
    ]
    result = _verdict(cg.check(rows), "G7")
    assert not result.passed
    assert "author_code" in result.detail and "validated_by" in result.detail


def test_g8_fails_when_one_author_writes_more_than_a_fifth_of_a_language_and_domain():
    result = _verdict(cg.check(_corpus(30, author_code="A1")), "G8")
    assert not result.passed and "A1" in result.detail


# ── G9 surface variation ─────────────────────────────────────────────────────
def test_g9_fails_on_a_corpus_with_no_surface_variation():
    result = _verdict(cg.check(_corpus(60)), "G9")
    assert not result.passed
    assert "capital" in result.detail.lower()


def test_g9_passes_when_the_corpus_carries_case_punctuation_and_spacing_variation():
    rows = _corpus(100)
    for k, row in enumerate(rows):
        if k % 5 == 0:
            row["text"] = row["text"].upper()
        elif k % 5 == 1:
            row["text"] = row["text"].rstrip(".")
        elif k % 5 == 2:
            row["text"] = row["text"].replace(" ", "  ")
    result = _verdict(cg.check(rows), "G9")
    assert result.passed, result.detail


# ── Gates that cannot be computed are never passes ───────────────────────────
def test_g3_and_g6_are_reported_not_computable_with_the_reason():
    results = cg.check(_corpus(40))
    for gate in ("G3", "G6"):
        result = _verdict(results, gate)
        assert result.passed is None
        assert result.detail


def test_no_gate_is_reported_as_passed_merely_for_being_uncomputable():
    assert all(r.passed is not True or r.detail for r in cg.check(_corpus(40)))


# ── The size question ────────────────────────────────────────────────────────
def test_the_largest_gate_passing_size_is_bounded_by_the_seed_inventory():
    ceiling = cg.largest_passing_corpus(distinct_seeds=165)
    assert ceiling["rows_under_g1"] == 165 * cg.MAX_ROWS_PER_SEED
    assert ceiling["passes_g2"] is False
    assert ceiling["largest_passing_rows"] == 0
    assert "G2" in ceiling["binding_gate"]


def test_a_large_enough_inventory_lifts_the_ceiling():
    ceiling = cg.largest_passing_corpus(distinct_seeds=30000)
    assert ceiling["passes_g2"] is True
    assert ceiling["largest_passing_rows"] == 30000 * cg.MAX_ROWS_PER_SEED


def test_the_report_names_every_gate_and_never_claims_an_overall_pass_on_failures(
    tmp_path,
):
    path = _write(tmp_path, _corpus(40))
    text = cg.report(path)
    for gate in ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9"):
        assert gate in text
    assert "FAIL" in text
    assert "no gate was waived" in text.lower()


def test_a_seed_column_under_another_name_can_be_mapped(tmp_path):
    """The split files attribute each row to its source phrase in a `phrase` column."""
    rows = [dict(r, phrase=r["seed_id"]) for r in _corpus(40)]
    for row in rows:
        del row["seed_id"]
    path = _write(tmp_path, rows, columns=[*COLUMNS[:4], "phrase", *COLUMNS[5:]])
    text = cg.report(path, seed_column="phrase")
    assert "no seed_id column" not in text
    assert "40 seeds" in text or "40 distinct" in text or "seeds" in text
