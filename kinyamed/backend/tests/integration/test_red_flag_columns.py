"""triage_results records the red-flag layer's decision, and PostgreSQL itself
refuses any row in which the rules layer lowered urgency (CLAUDE.md L2).

Raw SQL on purpose: these tests are about the constraints, which must hold for
any writer, not only for the ORM.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError


def _report_id(db) -> int:
    patient_id = db.execute(
        text(
            "INSERT INTO patients (name, phone) VALUES ('Fixture', '+250788111222') "
            "RETURNING id"
        )
    ).scalar_one()
    return db.execute(
        text(
            "INSERT INTO symptom_reports (patient_id, raw_input) "
            "VALUES (:p, 'fixture text') RETURNING id"
        ),
        {"p": patient_id},
    ).scalar_one()


def _insert(db, **columns) -> None:
    columns = {"symptom_report_id": _report_id(db), **columns}
    names = ", ".join(columns)
    values = ", ".join(
        f"CAST(:{k} AS urgencylevel)"
        if k in ("urgency_level", "model_urgency_raw")
        else f":{k}"
        for k in columns
    )
    db.execute(text(f"INSERT INTO triage_results ({names}) VALUES ({values})"), columns)
    db.flush()


def test_a_red_flag_escalation_to_critical_is_accepted(db):
    _insert(
        db,
        urgency_level="CRITICAL",
        model_urgency_raw="ROUTINE",
        rules_layer_triggered=True,
        rules_layer_reason="red_flag:FAKE01",
    )


def test_an_untriggered_row_keeps_the_model_urgency(db):
    _insert(db, urgency_level="URGENT", model_urgency_raw="URGENT")
    row = db.execute(
        text("SELECT rules_layer_triggered, rules_layer_reason FROM triage_results")
    ).one()
    assert row == (False, None)  # the column defaults: nothing triggered


def test_rows_from_before_the_migration_may_have_no_model_urgency(db):
    _insert(db, urgency_level="ROUTINE")


@pytest.mark.parametrize(
    ("final", "raw"),
    [("ROUTINE", "CRITICAL"), ("URGENT", "CRITICAL"), ("ROUTINE", "URGENT")],
)
def test_the_database_refuses_any_de_escalation(db, final, raw):
    with pytest.raises(IntegrityError, match="ck_triage_results_rules_escalate_only"):
        _insert(
            db,
            urgency_level=final,
            model_urgency_raw=raw,
            rules_layer_triggered=True,
            rules_layer_reason="red_flag:FAKE01",
        )


def test_the_database_refuses_a_changed_urgency_without_a_trigger(db):
    with pytest.raises(
        IntegrityError, match="ck_triage_results_untriggered_keeps_model_urgency"
    ):
        _insert(db, urgency_level="CRITICAL", model_urgency_raw="ROUTINE")


@pytest.mark.parametrize(
    "columns",
    [
        {"rules_layer_triggered": True},
        {"rules_layer_triggered": False, "rules_layer_reason": "red_flag:FAKE01"},
    ],
)
def test_a_reason_is_recorded_exactly_when_the_layer_triggered(db, columns):
    with pytest.raises(
        IntegrityError, match="ck_triage_results_rules_reason_iff_triggered"
    ):
        _insert(db, urgency_level="CRITICAL", model_urgency_raw="CRITICAL", **columns)
