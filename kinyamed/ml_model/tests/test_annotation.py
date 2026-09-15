"""The annotation tooling keeps annotators independent, blind, and PII-free, and
refuses to produce agreement or a gold set before it is entitled to."""

from __future__ import annotations

import csv
import re
import threading
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest
from annotation.kappa import cohen_kappa, kappa_report, linear_weighted_kappa
from annotation.store import AnnotationError, Store
from training.eval_spec import KAPPA_MINIMUM_ITEMS_PER_LANGUAGE, LANGUAGES


def _items_csv(path: Path, rows: list[dict]) -> Path:
    fields = sorted({k for r in rows for k in r})
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def _store(tmp_path: Path, n: int = 4, language: str = "kinyarwanda") -> Store:
    store = Store(tmp_path / "ann.sqlite3")
    rows = [
        {
            "item_id": f"i{k}",
            "text": f"synthetic item {k}",
            "language": language,
            "scenario_id": f"s{k}",
            "split": "test",
        }
        for k in range(n)
    ]
    store.import_items(_items_csv(tmp_path / "items.csv", rows), LANGUAGES)
    return store


# ── Import guards ─────────────────────────────────────────────────────────────
@pytest.mark.parametrize(
    "text", ["call me on 0788123456", "email josiane@example.rw please"]
)
def test_import_refuses_pii_and_does_not_echo_the_text(tmp_path, text):
    store = Store(tmp_path / "ann.sqlite3")
    rows = [
        {"item_id": "ok1", "text": "fine", "language": "english", "split": "test"},
        {"item_id": "bad1", "text": text, "language": "english", "split": "test"},
    ]
    with pytest.raises(AnnotationError) as refused:
        store.import_items(_items_csv(tmp_path / "items.csv", rows), LANGUAGES)
    assert "bad1" in str(refused.value)
    assert text not in str(refused.value)
    assert store.item_count() == 0, "a refused import must write nothing"


def test_import_refuses_a_label_column(tmp_path):
    store = Store(tmp_path / "ann.sqlite3")
    rows = [
        {
            "item_id": "i1",
            "text": "x",
            "language": "english",
            "split": "test",
            "gold_label": "URGENT",
        }
    ]
    with pytest.raises(AnnotationError, match="label column"):
        store.import_items(_items_csv(tmp_path / "items.csv", rows), LANGUAGES)


def test_import_refuses_a_language_outside_the_spec(tmp_path):
    store = Store(tmp_path / "ann.sqlite3")
    rows = [{"item_id": "i1", "text": "x", "language": "klingon", "split": "test"}]
    with pytest.raises(AnnotationError, match="not in the spec"):
        store.import_items(_items_csv(tmp_path / "items.csv", rows), LANGUAGES)


@pytest.mark.parametrize("bad", ["Josiane", "josiane@example.rw", "a1", "A12345", ""])
def test_annotator_ids_are_opaque_codes(tmp_path, bad):
    store = _store(tmp_path)
    with pytest.raises(AnnotationError, match="opaque codes"):
        store.record(bad, "i0", "URGENT", 2)


# ── Independence and blinding ─────────────────────────────────────────────────
def test_a_first_label_is_final(tmp_path):
    store = _store(tmp_path)
    store.record("A1", "i0", "URGENT", 2)
    with pytest.raises(AnnotationError, match="already labelled"):
        store.record("A1", "i0", "CRITICAL", 3)


def test_each_record_stores_annotator_label_confidence_and_a_utc_timestamp(tmp_path):
    store = _store(tmp_path)
    store.record("A1", "i0", "UNCLASSIFIABLE", 1, "not_enough_information")
    row = store.db.execute(
        "SELECT annotator_id, label, confidence, unclassifiable_reason, created_at FROM annotations"
    ).fetchone()
    assert row[:4] == ("A1", "UNCLASSIFIABLE", 1, "not_enough_information")
    assert re.match(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\+00:00$", row[4])


def test_unclassifiable_needs_a_reason_and_only_it_takes_one(tmp_path):
    store = _store(tmp_path)
    with pytest.raises(AnnotationError):
        store.record("A1", "i0", "UNCLASSIFIABLE", 1)
    with pytest.raises(AnnotationError):
        store.record("A1", "i1", "URGENT", 2, "other")


def test_annotators_get_different_orders(tmp_path):
    store = _store(tmp_path, n=30)
    assert (
        store.next_item("A1").item_id != store.next_item("B1").item_id
        or store.next_item("A2").item_id != store.next_item("B1").item_id
    )


def test_nothing_about_agreement_is_available_before_annotation_is_complete(tmp_path):
    store = _store(tmp_path, n=2)
    store.record("A1", "i0", "URGENT", 2)
    store.record("A1", "i1", "URGENT", 2)
    store.record("B1", "i0", "CRITICAL", 2)
    for call in (
        store.label_pairs,
        store.disagreements,
        lambda: store.export_labels(tmp_path / "x.csv"),
        lambda: store.build_gold(tmp_path / "gold"),
    ):
        with pytest.raises(AnnotationError, match="exactly two labels"):
            call()


# ── Adjudication and the gold set ─────────────────────────────────────────────
def _complete(store: Store, labels_a: list[str], labels_b: list[str]) -> None:
    for k, (a, b) in enumerate(zip(labels_a, labels_b, strict=True)):
        store.record("A1", f"i{k}", a, 3, "other" if a == "UNCLASSIFIABLE" else None)
        store.record("B1", f"i{k}", b, 3, "other" if b == "UNCLASSIFIABLE" else None)


def test_gold_set_refuses_while_disagreements_are_unresolved(tmp_path):
    store = _store(tmp_path, n=3)
    _complete(
        store, ["URGENT", "CRITICAL", "ROUTINE"], ["URGENT", "URGENT", "UNCLASSIFIABLE"]
    )
    assert {d["item_id"] for d in store.disagreements()} == {"i1", "i2"}
    with pytest.raises(AnnotationError, match="not adjudicated"):
        store.build_gold(tmp_path / "gold")


def test_an_annotator_cannot_adjudicate_their_own_item(tmp_path):
    store = _store(tmp_path, n=1)
    _complete(store, ["CRITICAL"], ["URGENT"])
    with pytest.raises(AnnotationError, match="third person"):
        store.adjudicate("i0", "CRITICAL", "A1", "annotator_a_correct")


def test_the_gold_set_is_what_the_gate_reads(tmp_path, capsys):
    pytest.importorskip("numpy")
    from training import evaluate as gate

    store = _store(tmp_path, n=3)
    _complete(
        store, ["URGENT", "CRITICAL", "ROUTINE"], ["URGENT", "URGENT", "UNCLASSIFIABLE"]
    )
    store.adjudicate("i1", "CRITICAL", "C1", "annotator_a_correct")
    store.adjudicate("i2", "UNCLASSIFIABLE", "C1", "unclassifiable_confirmed")
    manifest = store.build_gold(tmp_path / "gold")
    assert len(manifest["files"]["test"]["sha256"]) == 64

    gold = tmp_path / "gold" / "gold_test.csv"
    preds = tmp_path / "preds.csv"
    preds.write_text(
        "item_id,p_critical,p_urgent,p_routine\n"
        "i0,0.1,0.8,0.1\ni1,0.8,0.1,0.1\ni2,0.1,0.1,0.8\n"
    )
    items, excluded = gate.load_items(gold, gate.load_predictions(preds))
    assert [i.item_id for i in items] == ["i0", "i1"]
    assert excluded["unclassifiable"] == 1
    assert (
        gate.main(
            ["--gold", str(gold), "--predictions", str(preds), "--bootstrap", "50"]
        )
        == 1
    )
    assert "INSUFFICIENT DATA (n=2, need 710)" in capsys.readouterr().out


# ── Kappa ─────────────────────────────────────────────────────────────────────
def test_kappa_matches_a_hand_computation():
    # observed 3/4; expected (2*1 + 1*2 + 1*1)/16 = 5/16; kappa = (12/16 - 5/16)/(11/16) = 7/11
    assert cohen_kappa(
        ["CRITICAL", "CRITICAL", "URGENT", "ROUTINE"],
        ["CRITICAL", "URGENT", "URGENT", "ROUTINE"],
    ) == pytest.approx(7 / 11)


def test_perfect_agreement_is_one_and_weighted_kappa_skips_unclassifiable():
    labels = ["CRITICAL", "URGENT", "ROUTINE"] * 10
    assert cohen_kappa(labels, labels) == 1.0
    assert linear_weighted_kappa(labels, labels) == 1.0
    assert linear_weighted_kappa(["UNCLASSIFIABLE"], ["URGENT"]) is None


def test_per_language_kappa_is_refused_below_the_minimum():
    pairs = [("swahili", "URGENT", "URGENT")] * (KAPPA_MINIMUM_ITEMS_PER_LANGUAGE - 1)
    rows = kappa_report(pairs, resamples=50)
    swahili = next(r for r in rows if r.scope == "swahili")
    assert swahili.kappa is None
    assert (
        swahili.verdict
        == f"INSUFFICIENT DATA (n={KAPPA_MINIMUM_ITEMS_PER_LANGUAGE - 1}, need {KAPPA_MINIMUM_ITEMS_PER_LANGUAGE})"
    )


def test_kappa_verdict_uses_the_lower_bound():
    agree = [("english", c, c) for c in ["CRITICAL", "URGENT", "ROUTINE"] * 100]
    rows = kappa_report(agree, resamples=100)
    assert next(r for r in rows if r.scope == "english").verdict == "MET"


def test_compute_kappa_refuses_a_single_file(tmp_path, capsys):
    import importlib.util

    script = Path(__file__).resolve().parents[1] / "scripts" / "compute_kappa.py"
    module_spec = importlib.util.spec_from_file_location("compute_kappa", script)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    assert module.main([str(tmp_path / "only.csv")]) == 2
    assert "REFUSED" in capsys.readouterr().err


# ── The local form ────────────────────────────────────────────────────────────
def test_the_server_binds_to_localhost_only(tmp_path):
    from annotation.server import build_server

    _store(tmp_path)
    with pytest.raises(AnnotationError, match=r"127\.0\.0\.1"):
        build_server(tmp_path / "ann.sqlite3", host="0.0.0.0", port=0)


def test_the_form_escapes_item_text_rejects_foreign_posts_and_records_labels(tmp_path):
    from annotation.server import build_server

    store = Store(tmp_path / "ann.sqlite3")
    rows = [
        {
            "item_id": "x1",
            "text": "<script>alert(1)</script> umuriro",
            "language": "kinyarwanda",
            "scenario_id": "sx1",
            "split": "test",
        }
    ]
    store.import_items(_items_csv(tmp_path / "items.csv", rows), LANGUAGES)
    server, token = build_server(tmp_path / "ann.sqlite3", port=0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        page = urllib.request.urlopen(f"{base}/annotate?a=A1").read().decode()
        assert "<script>" not in page and "&lt;script&gt;" in page
        assert "gold" not in page.lower()

        def post(fields: dict) -> int:
            data = urllib.parse.urlencode(fields).encode()
            try:
                return urllib.request.urlopen(
                    urllib.request.Request(f"{base}/annotate", data=data)
                ).status
            except urllib.error.HTTPError as error:
                return error.code

        assert (
            post(
                {
                    "token": "forged",
                    "a": "A1",
                    "item_id": "x1",
                    "label": "URGENT",
                    "confidence": "2",
                }
            )
            == 403
        )
        assert store.progress("A1") == (0, 1)
        assert (
            post(
                {
                    "token": token,
                    "a": "A1",
                    "item_id": "x1",
                    "label": "URGENT",
                    "confidence": "2",
                }
            )
            == 200
        )
        assert Store(tmp_path / "ann.sqlite3").progress("A1") == (1, 1)
    finally:
        server.shutdown()


def test_the_pii_pattern_matches_the_backends():
    backend = (
        Path(__file__).resolve().parents[2] / "backend" / "app" / "core" / "pii.py"
    )
    if not backend.exists():
        pytest.skip("backend package absent")
    from annotation import store

    match = re.search(
        r'_PHONE: Final = re\.compile\(\s*r"([^"]+)"', backend.read_text()
    )
    assert match, "could not find the backend's phone pattern"
    assert store._PHONE.pattern == match.group(1)


# ── Scenario rules at import (EVAL_SET_SPEC §8, D7 protocol §2.3) ─────────────
def _row(item_id: str, scenario: str | None, split: str = "test") -> dict:
    row = {
        "item_id": item_id,
        "text": f"synthetic {item_id}",
        "language": "kinyarwanda",
        "split": split,
    }
    if scenario is not None:
        row["scenario_id"] = scenario
    return row


def test_import_refuses_items_without_a_scenario_id(tmp_path):
    store = Store(tmp_path / "ann.sqlite3")
    rows = [_row("a", "s1"), _row("b", "")]
    with pytest.raises(AnnotationError, match="scenario_id"):
        store.import_items(_items_csv(tmp_path / "items.csv", rows), LANGUAGES)
    assert store.item_count() == 0


def test_import_refuses_two_test_items_from_one_scenario(tmp_path):
    store = Store(tmp_path / "ann.sqlite3")
    rows = [_row("a", "s1"), _row("b", "s1"), _row("c", "s1", "calibration")]
    with pytest.raises(AnnotationError, match="one test item per scenario"):
        store.import_items(_items_csv(tmp_path / "items.csv", rows), LANGUAGES)


def test_import_refuses_a_scenario_already_used_in_the_other_split(tmp_path):
    store = Store(tmp_path / "ann.sqlite3")
    store.import_items(_items_csv(tmp_path / "one.csv", [_row("a", "s1")]), LANGUAGES)
    with pytest.raises(AnnotationError, match="both the test and calibration"):
        store.import_items(
            _items_csv(tmp_path / "two.csv", [_row("b", "s1", "calibration")]),
            LANGUAGES,
        )
    assert store.item_count() == 1


def test_import_refuses_a_duplicate_item_id_cleanly(tmp_path):
    store = Store(tmp_path / "ann.sqlite3")
    store.import_items(_items_csv(tmp_path / "one.csv", [_row("a", "s1")]), LANGUAGES)
    with pytest.raises(AnnotationError, match="already imported"):
        store.import_items(
            _items_csv(tmp_path / "two.csv", [_row("a", "s2")]), LANGUAGES
        )


# ── Exactly two independent labels ────────────────────────────────────────────
def test_a_third_annotator_is_refused(tmp_path):
    store = _store(tmp_path, n=1)
    store.record("A1", "i0", "URGENT", 2)
    store.record("B1", "i0", "URGENT", 2)
    with pytest.raises(AnnotationError, match="already has two independent labels"):
        store.record("C1", "i0", "CRITICAL", 3)
    assert store.next_item("C1") is None


# ── The two tool gaps named in D7 protocol §4 ─────────────────────────────────
def test_a_withdrawn_item_leaves_kappa_and_the_gold_set_and_is_counted(tmp_path):
    """An annotator recognises an item (e.g. they wrote it). The label is kept as a
    record, but the item is excluded from agreement and gold, and the exclusion is
    reported, never silent."""
    store = _store(tmp_path, n=3)
    store.record("A1", "i0", "URGENT", 3)
    store.withdraw("i0", "A1", "annotator_recognised_item")
    assert store.next_item("B1").item_id != "i0"
    with pytest.raises(AnnotationError, match="withdrawn"):
        store.record("B1", "i0", "URGENT", 3)
    for k in (1, 2):
        store.record("A1", f"i{k}", "URGENT", 3)
        store.record("B1", f"i{k}", "URGENT", 3)
    assert [p[0] for p in store._pairs()] == ["i1", "i2"]
    manifest = store.build_gold(tmp_path / "gold")
    assert manifest["withdrawn"] == {"count": 1, "items": ["i0"]}
    gold = (tmp_path / "gold" / "gold_test.csv").read_text()
    assert "i0," not in gold
    exported = tmp_path / "labels.csv"
    store.export_labels(exported)
    with exported.open(encoding="utf-8", newline="") as handle:
        kept = [r for r in csv.DictReader(handle) if r["item_id"] == "i0"]
    assert [(r["annotator_id"], r["label"], r["withdrawn"]) for r in kept] == [
        ("A1", "URGENT", "yes")
    ]


def test_a_withdrawal_needs_a_known_reason_and_item(tmp_path):
    store = _store(tmp_path, n=1)
    with pytest.raises(AnnotationError, match="reason"):
        store.withdraw("i0", "A1", "because")
    with pytest.raises(AnnotationError, match="unknown item"):
        store.withdraw("nope", "A1", "annotator_recognised_item")


def test_an_agreed_item_can_be_sent_to_adjudication_and_first_labels_stand(tmp_path):
    """An annotator saved the wrong label on an item both chose the same way. The
    first label still counts for kappa; the item must be adjudicated before gold."""
    store = _store(tmp_path, n=2)
    _complete(store, ["URGENT", "ROUTINE"], ["URGENT", "ROUTINE"])
    assert store.disagreements() == []
    with pytest.raises(AnnotationError, match="labelled"):
        store.request_adjudication("i0", "C1", "saved_wrong_label")
    store.request_adjudication("i0", "A1", "saved_wrong_label")
    flagged = store.disagreements()
    assert [d["item_id"] for d in flagged] == ["i0"]
    assert flagged[0]["adjudication_requested_by"] == "A1"
    assert store.label_pairs() == [("kinyarwanda", "URGENT", "URGENT")] * 1 + [
        ("kinyarwanda", "ROUTINE", "ROUTINE")
    ]
    with pytest.raises(AnnotationError, match="not adjudicated"):
        store.build_gold(tmp_path / "gold")
    store.adjudicate("i0", "CRITICAL", "C1", "neither_correct")
    store.build_gold(tmp_path / "gold")
    assert (
        "i0,synthetic item 0,kinyarwanda,CRITICAL"
        in (tmp_path / "gold" / "gold_test.csv").read_text()
    )


# ── Synthetic annotators, end to end through the command line ─────────────────
def test_synthetic_annotators_give_per_language_kappa_through_the_cli(tmp_path, capsys):
    """Two seeded synthetic annotators label 250 Kinyarwanda and 120 Swahili items.
    The CLI's kappa equals a direct computation on the stored labels, and Swahili,
    below the per-language minimum, is refused rather than reported."""
    import random

    from annotation.__main__ import main as cli

    rng = random.Random(11)
    labels = ("CRITICAL", "URGENT", "ROUTINE")
    rows = []
    for lang, n in (("kinyarwanda", 250), ("swahili", 120)):
        rows += [
            {
                "item_id": f"{lang[:2]}{k}",
                "text": f"synthetic {lang} item {k}",
                "language": lang,
                "scenario_id": f"{lang[:2]}-s{k}",
                "split": "test",
            }
            for k in range(n)
        ]
    db = tmp_path / "ann.sqlite3"
    assert (
        cli(
            ["--db", str(db), "import-items", str(_items_csv(tmp_path / "i.csv", rows))]
        )
        == 0
    )
    store = Store(db)
    truth = {r["item_id"]: rng.choice(labels) for r in rows}
    for annotator, accuracy in (("A1", 0.92), ("B1", 0.88)):
        while (item := store.next_item(annotator)) is not None:
            label = (
                truth[item.item_id] if rng.random() < accuracy else rng.choice(labels)
            )
            store.record(annotator, item.item_id, label, rng.choice((1, 2, 3)))
    capsys.readouterr()
    assert cli(["--db", str(db), "kappa"]) == 0
    out = capsys.readouterr().out
    kinyarwanda = [
        (a, b) for lang, a, b in store.label_pairs() if lang == "kinyarwanda"
    ]
    expected = cohen_kappa([a for a, _ in kinyarwanda], [b for _, b in kinyarwanda])
    line = next(
        line for line in out.splitlines() if line.lstrip().startswith("kinyarwanda")
    )
    assert f"{expected:.3f}" in line, (expected, line)
    swahili = next(
        line for line in out.splitlines() if line.lstrip().startswith("swahili")
    )
    assert "INSUFFICIENT DATA (n=120, need 200)" in swahili
