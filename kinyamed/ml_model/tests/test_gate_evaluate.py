"""training/evaluate.py: the 15-metric gate, its intervals, and its refusals.

All data here is synthetic and says nothing about any model. It exists to pin the
arithmetic and, above all, that too little data produces a refusal, not a number.
"""

from __future__ import annotations

import csv
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

np = pytest.importorskip("numpy", reason="the gate's bootstrap needs numpy")

from training import eval_spec as spec  # noqa: E402
from training import evaluate as gate  # noqa: E402

CLASSES = spec.CLASSES


def _probs(pred: str, confidence: float = 0.9) -> dict[str, str]:
    rest = (1 - confidence) / 2
    values = {c: rest for c in CLASSES}
    values[pred] = confidence
    return {
        "p_critical": str(values["CRITICAL"]),
        "p_urgent": str(values["URGENT"]),
        "p_routine": str(values["ROUTINE"]),
    }


def _write(tmp: Path, rows: list[dict]) -> tuple[Path, Path]:
    """rows: dicts with language, gold, pred, and optional scenario/confidence/detected."""
    gold, preds = tmp / "gold.csv", tmp / "preds.csv"
    with (
        gold.open("w", newline="", encoding="utf-8") as g,
        preds.open("w", newline="", encoding="utf-8") as p,
    ):
        gw = csv.DictWriter(
            g, ["item_id", "text", "language", "gold_label", "scenario_id", "split"]
        )
        pw = csv.DictWriter(
            p, ["item_id", "p_critical", "p_urgent", "p_routine", "detected_language"]
        )
        gw.writeheader()
        pw.writeheader()
        for i, r in enumerate(rows):
            item_id = f"it{i:05d}"
            gw.writerow(
                {
                    "item_id": item_id,
                    "text": "synthetic",
                    "language": r["language"],
                    "gold_label": r["gold"],
                    "scenario_id": r.get("scenario", item_id),
                    "split": "test",
                }
            )
            pw.writerow(
                {
                    "item_id": item_id,
                    **_probs(r["pred"], r.get("confidence", 0.9)),
                    "detected_language": r.get("detected", r["language"]),
                }
            )
    return gold, preds


def _full_allocation(
    correct=lambda lang, cls, k: True, confidence: float = 0.9
) -> list[dict]:
    rows = []
    for a in spec.TEST_ALLOCATION:
        for cls, count in (
            ("CRITICAL", a.critical),
            ("URGENT", a.urgent),
            ("ROUTINE", a.routine),
        ):
            for k in range(count):
                ok = correct(a.language, cls, k)
                wrong = "URGENT" if cls != "URGENT" else "ROUTINE"
                rows.append(
                    {
                        "language": a.language,
                        "gold": cls,
                        "pred": cls if ok else wrong,
                        "confidence": confidence,
                    }
                )
    return rows


def _run(tmp: Path, rows: list[dict], *extra: str, capsys) -> tuple[int, str]:
    gold, preds = _write(tmp, rows)
    code = gate.main(
        ["--gold", str(gold), "--predictions", str(preds), "--bootstrap", "200", *extra]
    )
    return code, capsys.readouterr().out


def _line(output: str, needle: str) -> str:
    matches = [line for line in output.splitlines() if needle in line]
    assert matches, f"no report line contains {needle!r}"
    return matches[0]


# ── Refusal ───────────────────────────────────────────────────────────────────
def test_too_little_data_prints_insufficient_data_and_no_number(tmp_path, capsys):
    rows = [
        {"language": "kinyarwanda", "gold": "CRITICAL", "pred": "CRITICAL"}
        for _ in range(4)
    ]
    rows += [
        {"language": "kinyarwanda", "gold": "ROUTINE", "pred": "ROUTINE"}
        for _ in range(5)
    ]
    code, out = _run(tmp_path, rows, capsys=capsys)

    line = _line(out, "CRITICAL recall [kinyarwanda]")
    assert "INSUFFICIENT DATA (n=4, need 365)" in line
    # Strip the gate id, the threshold and the refusal itself: nothing numeric may remain.
    results = (
        re.sub(r"^\S+", "", line)
        .replace(">= 0.91", "")
        .replace("INSUFFICIENT DATA (n=4, need 365)", "")
    )
    assert not re.search(r"\d", results), (
        f"a number was printed beside a refusal: {line}"
    )
    assert "INSUFFICIENT DATA (n=9, need 710)" in _line(out, "overall accuracy")
    assert code == 1, "an incomplete gate must not permit deployment"


def test_the_nine_sentence_set_reports_nothing_but_refusals(tmp_path, capsys):
    rows = [
        {"language": "kinyarwanda", "gold": c, "pred": c}
        for c in ["CRITICAL"] * 4 + ["URGENT"] * 4 + ["ROUTINE"]
    ]
    _, out = _run(tmp_path, rows, capsys=capsys)
    table = out.split("Verdict", 1)[1].split("gate rows MET")[0]
    rows_ = [
        line
        for line in table.splitlines()
        if line.strip() and not line.startswith(("0 of", "1 of"))
    ]
    assert rows_, "no table rows parsed"
    for line in rows_:
        assert not line.rstrip().endswith((" MET", "NOT DEMONSTRATED")), line


def test_every_gate_row_is_present(tmp_path, capsys):
    _, out = _run(
        tmp_path,
        [{"language": "english", "gold": "URGENT", "pred": "URGENT"}],
        capsys=capsys,
    )
    for gate_id in [str(i) for i in range(1, 16)] + [
        "X-ECE",
        "X-LID-pure",
        "X-LID-mixed",
    ]:
        assert re.search(rf"^{re.escape(gate_id)}\s", out, re.MULTILINE), (
            f"gate {gate_id} missing"
        )
    for lang in spec.PURE_LANGUAGES:
        assert f"CRITICAL recall [{lang}]" in out


def test_a_mixed_pair_below_its_floor_blocks_the_pooled_mixed_metric(tmp_path, capsys):
    rows = []
    for pair in spec.MIXED_LANGUAGES:
        count = 50 if pair == "french+swahili" else 200
        rows += [
            {"language": pair, "gold": "URGENT", "pred": "URGENT"} for _ in range(count)
        ]
    _, out = _run(tmp_path, rows, capsys=capsys)
    line = _line(out, "mixed-language accuracy")
    assert "INSUFFICIENT DATA" in line and "french+swahili n=50" in line


# ── Arithmetic and verdicts ───────────────────────────────────────────────────
def test_points_are_exact_on_a_known_confusion(tmp_path, capsys):
    # Kinyarwanda CRITICAL: 380 correct, 12 -> URGENT, 8 -> ROUTINE.
    rows = [
        {"language": "kinyarwanda", "gold": "CRITICAL", "pred": p}
        for p in ["CRITICAL"] * 380 + ["URGENT"] * 12 + ["ROUTINE"] * 8
    ]
    _, out = _run(tmp_path, rows, capsys=capsys)
    assert "0.9500" in _line(out, "CRITICAL recall [kinyarwanda]")


def test_recall_exactly_at_the_threshold_is_not_demonstrated(tmp_path, capsys):
    rows = [
        {
            "language": "swahili",
            "gold": "CRITICAL",
            "pred": "CRITICAL" if k < 364 else "URGENT",
        }
        for k in range(400)
    ]
    _, out = _run(tmp_path, rows, capsys=capsys)
    line = _line(out, "CRITICAL recall [swahili]")
    assert "0.9100" in line and "NOT DEMONSTRATED" in line


def test_recall_clearly_below_the_threshold_is_not_met(tmp_path, capsys):
    rows = [
        {
            "language": "french",
            "gold": "CRITICAL",
            "pred": "CRITICAL" if k < 320 else "ROUTINE",
        }
        for k in range(400)
    ]
    _, out = _run(tmp_path, rows, capsys=capsys)
    assert _line(out, "CRITICAL recall [french]").rstrip().endswith("NOT MET")


def test_critical_to_routine_is_counted_against_gold_critical(tmp_path, capsys):
    rows = [
        {
            "language": "english",
            "gold": "CRITICAL",
            "pred": "ROUTINE" if k < 30 else "CRITICAL",
        }
        for k in range(1000)
    ]
    _, out = _run(tmp_path, rows, capsys=capsys)
    line = _line(out, "CRITICAL -> ROUTINE rate")
    assert "0.0300" in line and "NOT MET" in line


def test_a_strong_synthetic_model_with_measurements_is_permitted(tmp_path, capsys):
    rows = _full_allocation(correct=lambda lang, cls, k: k % 50 != 0, confidence=0.97)
    latency = tmp_path / "latency.json"
    latency.write_text(
        json.dumps({"rows": 1000, "warm_ms": {"median": 60.0, "p95": 110.0}})
    )
    memory = tmp_path / "memory.json"
    memory.write_text(json.dumps({"peak_rss_mb": 1400.0, "concurrency": 50}))
    code, out = _run(
        tmp_path,
        rows,
        "--latency",
        str(latency),
        "--memory",
        str(memory),
        capsys=capsys,
    )
    assert "Deployment PERMITTED" in out, out
    assert code == 0


def test_missing_measurements_block_deployment(tmp_path, capsys):
    code, out = _run(tmp_path, _full_allocation(confidence=0.97), capsys=capsys)
    assert "NOT MEASURED (no --latency file)" in out
    assert "NOT MEASURED (no --memory file)" in out
    assert code == 1


def test_clustered_scenarios_widen_the_bootstrap_interval(tmp_path, capsys):
    def rows(scenario_size: int) -> list[dict]:
        out = []
        for k in range(800):
            scenario = f"s{k // scenario_size}"
            ok = (
                k // scenario_size
            ) % 10 != 0  # errors arrive a whole scenario at a time
            out.append(
                {
                    "language": "kinyarwanda",
                    "gold": "URGENT",
                    "pred": "URGENT" if ok else "ROUTINE",
                    "scenario": scenario,
                }
            )
        return out

    def width(path: Path, data: list[dict]) -> float:
        path.mkdir()
        gold, preds = _write(path, data)
        items, _ = gate.load_items(gold, gate.load_predictions(preds))
        row = next(
            r
            for r in gate.evaluate(items, bootstrap=400)
            if r.metric == "accuracy [kinyarwanda]"
        )
        return row.ci_bootstrap[1] - row.ci_bootstrap[0]

    assert width(tmp_path / "clustered", rows(20)) > 2 * width(
        tmp_path / "independent", rows(1)
    )


# ── Input validation ──────────────────────────────────────────────────────────
def test_a_missing_prediction_refuses_the_whole_run(tmp_path, capsys):
    gold, preds = _write(
        tmp_path, [{"language": "english", "gold": "URGENT", "pred": "URGENT"}] * 3
    )
    lines = preds.read_text().splitlines()
    preds.write_text("\n".join(lines[:-1]) + "\n")
    assert gate.main(["--gold", str(gold), "--predictions", str(preds)]) == 2
    assert "REFUSED" in capsys.readouterr().err


def test_probabilities_that_are_not_a_distribution_are_refused(tmp_path, capsys):
    gold, preds = _write(
        tmp_path, [{"language": "english", "gold": "URGENT", "pred": "URGENT"}]
    )
    preds.write_text(preds.read_text().replace("0.9", "0.99", 1))
    assert gate.main(["--gold", str(gold), "--predictions", str(preds)]) == 2


def test_unclassifiable_items_are_excluded_and_counted(tmp_path, capsys):
    gold, preds = _write(
        tmp_path, [{"language": "english", "gold": "URGENT", "pred": "URGENT"}] * 3
    )
    text = gold.read_text().splitlines()
    text[1] = text[1].replace("URGENT", spec.UNCLASSIFIABLE)
    gold.write_text("\n".join(text) + "\n")
    gate.main(["--gold", str(gold), "--predictions", str(preds)])
    assert "'unclassifiable': 1" in capsys.readouterr().out


# ── Calibration output ────────────────────────────────────────────────────────
def test_reliability_diagram_is_written_only_with_enough_items(tmp_path, capsys):
    small = tmp_path / "small"
    small.mkdir()
    _, _ = _run(
        small,
        [{"language": "english", "gold": "URGENT", "pred": "URGENT"}] * 10,
        "--out",
        str(small / "r"),
        capsys=capsys,
    )
    assert not (small / "r" / "reliability.svg").exists()
    assert (
        "INSUFFICIENT DATA" in (small / "r" / "reliability.NOT_DRAWN.txt").read_text()
    )

    big = tmp_path / "big"
    big.mkdir()
    _run(big, _full_allocation(confidence=0.8), "--out", str(big / "r"), capsys=capsys)
    svg = ET.parse(big / "r" / "reliability.svg").getroot()
    bars = [el for el in svg.iter() if el.get("class") == "bin"]
    assert sum(int(b.get("data-count")) for b in bars) == 4900
    report = json.loads((big / "r" / "gate_report.json").read_text())
    assert any(r["gate"] == "X-ECE" and r["point"] is not None for r in report["rows"])


def test_ece_of_a_known_miscalibration(tmp_path, capsys):
    """Everything right at confidence 0.7: ECE is exactly 0.3."""
    _, out = _run(tmp_path, _full_allocation(confidence=0.7), capsys=capsys)
    line = _line(out, "expected calibration error")
    assert "0.3000" in line and "NOT MET" in line


def test_the_repository_latency_record_is_scored_not_retyped():
    record = Path(__file__).resolve().parents[1] / "training" / "latency_v2d.json"
    rows = gate.measurement_rows(record, None)
    latency = rows[0]
    assert latency.gate == "14" and latency.n == 1000
    assert latency.verdict == gate.VERDICT_MET
    assert "p95 103.25" in latency.note


def test_legacy_names_are_still_importable():
    from training.evaluate import (  # noqa: F401
        MINIMUM_CRITICAL_RECALL,
        load_manifest,
        triage_gate,
    )

    assert MINIMUM_CRITICAL_RECALL == 0.95
