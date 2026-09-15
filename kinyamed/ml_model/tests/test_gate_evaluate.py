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


def _large_allocation(
    correct=lambda lang, cls, k: True, confidence: float = 0.9
) -> list[dict]:
    """Enough per pure language for every per-language row (docs/ENGINEERING_SPEC.md §16): 800
    CRITICAL clears gate 7's 720, 600 URGENT and ROUTINE clear the F1 and URGENT
    minimums of 570. Mixed pairs as the spec's allocation."""
    rows = []
    sizes = [(lang, 800, 600, 600) for lang in spec.PURE_LANGUAGES] + [
        (lang, 60, 45, 45) for lang in spec.MIXED_LANGUAGES
    ]
    for lang, n_c, n_u, n_r in sizes:
        for cls, count in (("CRITICAL", n_c), ("URGENT", n_u), ("ROUTINE", n_r)):
            for k in range(count):
                ok = correct(lang, cls, k)
                wrong = "URGENT" if cls != "URGENT" else "ROUTINE"
                rows.append(
                    {
                        "language": lang,
                        "gold": cls,
                        "pred": cls if ok else wrong,
                        "confidence": confidence,
                    }
                )
    return rows


PER_LANGUAGE_GATES = (
    "weighted F1",
    "macro F1",
    "CRITICAL precision",
    "CRITICAL F1",
    "CRITICAL -> ROUTINE rate",
    "URGENT recall",
)


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


def _data_rows(output: str) -> list[str]:
    table = output.split("Verdict", 1)[1].split("gate rows MET")[0]
    return [
        line
        for line in table.splitlines()
        if line.strip() and not re.match(r"^\d+ of ", line)
    ]


def test_many_rows_from_few_scenarios_are_counted_as_scenarios(tmp_path, capsys):
    """The current reporting set is 17,942 rows built from 9 sentences. Counted as
    rows, 8,962 CRITICAL rows clear every minimum and a number is printed. The
    unit the minimums were powered for is the independent scenario."""
    rows = []
    for gold, scenarios in (("CRITICAL", 4), ("URGENT", 4), ("ROUTINE", 1)):
        for s in range(scenarios):
            rows += [
                {
                    "language": "kinyarwanda",
                    "gold": gold,
                    "pred": gold,
                    "scenario": f"{gold}-{s}",
                }
            ] * 500
    _, out = _run(tmp_path, rows, capsys=capsys)
    assert (
        "INSUFFICIENT DATA (2,000 rows from 4 distinct source sentences; need 365 distinct)"
        in _line(out, "CRITICAL recall [kinyarwanda]")
    )
    assert (
        "INSUFFICIENT DATA (4,500 rows from 9 distinct source sentences; need 780 distinct)"
        in _line(out, "accuracy [kinyarwanda]")
    )
    assert "4500 items in 9 scenarios" in out
    for line in _data_rows(out):
        assert "INSUFFICIENT DATA" in line or "NOT MEASURED" in line, line


def _nine_sentence_gold(tmp: Path) -> Path:
    rows = []
    for gold, scenarios in (("CRITICAL", 4), ("URGENT", 4), ("ROUTINE", 1)):
        for s in range(scenarios):
            rows += [
                {
                    "language": "kinyarwanda",
                    "gold": gold,
                    "pred": gold,
                    "scenario": f"{gold}-{s}",
                }
            ] * 2000
    gold, _ = _write(tmp, rows)
    return gold


def test_check_gold_refuses_the_nine_sentence_shape_without_any_predictions(
    tmp_path, capsys
):
    """No model is run: every population a gate needs is fixed by the gold file,
    except CRITICAL precision, whose denominator the model chooses."""
    code = gate.main(["--gold", str(_nine_sentence_gold(tmp_path)), "--check-gold"])
    out = capsys.readouterr().out
    assert code == 2
    assert (
        "INSUFFICIENT DATA (8,000 rows from 4 distinct source sentences; need 365 distinct)"
        in _line(out, "CRITICAL recall [kinyarwanda]")
    )
    assert "known only after inference" in _line(out, "CRITICAL precision")
    assert "No gate cell can be measured on this gold set" in out


def test_check_gold_passes_a_set_built_to_the_allocation(tmp_path, capsys):
    gold, _ = _write(tmp_path, _full_allocation())
    assert gate.main(["--gold", str(gold), "--check-gold"]) == 0
    out = capsys.readouterr().out
    critical = next(
        a for a in spec.TEST_ALLOCATION if a.language == "kinyarwanda"
    ).critical
    assert f"SUFFICIENT ({critical} distinct" in _line(
        out, "CRITICAL recall [kinyarwanda]"
    )


def test_inference_is_refused_before_the_model_is_loaded(tmp_path, capsys):
    """A model directory that does not exist proves no load was attempted."""
    code = gate.main(
        [
            "--gold",
            str(_nine_sentence_gold(tmp_path)),
            "--model",
            str(tmp_path / "no_such_model"),
        ]
    )
    captured = capsys.readouterr()
    assert code == 2
    assert "before inference" in captured.err


def test_a_gold_item_without_a_scenario_id_is_refused(tmp_path, capsys):
    """Without scenario_id every row would count as its own scenario, which is the
    loophole the scenario count closes (D7 protocol §2.3: every item carries one)."""
    rows = [
        {"language": "kinyarwanda", "gold": "URGENT", "pred": "URGENT", "scenario": ""}
    ]
    gold, preds = _write(tmp_path, rows)
    code = gate.main(
        ["--gold", str(gold), "--predictions", str(preds), "--bootstrap", "50"]
    )
    captured = capsys.readouterr()
    assert code == 2
    assert "scenario_id" in captured.err
    assert "Verdict" not in captured.out


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


def test_every_pooled_gate_is_also_gated_per_pure_language(tmp_path, capsys):
    """docs/ENGINEERING_SPEC.md §16: all 15 metrics met, with intervals, per language."""
    _, out = _run(
        tmp_path,
        [{"language": "english", "gold": "URGENT", "pred": "URGENT"}],
        capsys=capsys,
    )
    for name in PER_LANGUAGE_GATES:
        for lang in spec.PURE_LANGUAGES:
            assert f"{name} [{lang}]" in out, f"no row for {name} [{lang}]"


def test_every_per_language_row_is_measurable_on_the_designed_allocation(
    tmp_path, capsys
):
    """E8 and E8b: on the designed test set no per-language gate row is refused for
    too little data, so a model is judged on its results, not on the set's size."""
    _, out = _run(tmp_path, _full_allocation(), capsys=capsys)
    for name in PER_LANGUAGE_GATES:
        for lang in spec.PURE_LANGUAGES:
            line = _line(out, f"{name} [{lang}]")
            assert "INSUFFICIENT" not in line, line


def test_a_per_language_failure_blocks_deployment(tmp_path, capsys):
    """Swahili sends 3% of its CRITICAL items to ROUTINE; every other language none."""

    def rows():
        out = []
        for r in _large_allocation():
            out.append(r)
        k = 0
        for r in out:
            if r["language"] == "swahili" and r["gold"] == "CRITICAL":
                if k % 33 == 0:
                    r["pred"] = "ROUTINE"
                k += 1
        return out

    code, out = _run(tmp_path, rows(), capsys=capsys)
    assert _line(out, "CRITICAL -> ROUTINE rate [swahili]").rstrip().endswith("NOT MET")
    english = _line(out, "CRITICAL -> ROUTINE rate [english]").rstrip()
    assert re.search(r"(?<!NOT) MET$", english), english
    assert "Deployment BLOCKED" in out
    assert code == 1


# ── The red-flag safety suite (docs/ENGINEERING_SPEC.md L2, §16 hard gate) ──────────────────
def _red_flag_report(tmp: Path, cases: int, passed: int) -> Path:
    path = tmp / "red_flags.json"
    path.write_text(
        json.dumps(
            {
                "suite": "synthetic",
                "suite_sha256": "0" * 64,
                "cases": cases,
                "passed": passed,
                "failures": [],
            }
        )
    )
    return path


def test_without_a_red_flag_report_the_suite_row_is_not_measured(tmp_path, capsys):
    code, out = _run(
        tmp_path,
        [{"language": "english", "gold": "URGENT", "pred": "URGENT"}],
        capsys=capsys,
    )
    assert "NOT MEASURED" in _line(out, "red-flag safety suite")
    assert code == 1


@pytest.mark.parametrize(
    ("cases", "passed", "verdict"),
    [(12, 12, "MET"), (12, 11, "NOT MET"), (0, 0, "NOT MEASURED")],
)
def test_the_red_flag_suite_must_pass_every_case(
    tmp_path, capsys, cases, passed, verdict
):
    report = _red_flag_report(tmp_path, cases, passed)
    _, out = _run(
        tmp_path,
        [{"language": "english", "gold": "URGENT", "pred": "URGENT"}],
        "--red-flag-report",
        str(report),
        capsys=capsys,
    )
    line = _line(out, "red-flag safety suite").rstrip()
    if verdict == "MET":
        assert re.search(r"(?<!NOT) MET  \(", line) or re.search(
            r"(?<!NOT) MET$", line
        ), line
    else:
        assert verdict in line, line


def test_a_strong_synthetic_model_with_measurements_is_permitted(tmp_path, capsys):
    rows = _large_allocation(correct=lambda lang, cls, k: k % 50 != 0, confidence=0.97)
    code, out = _run(
        tmp_path,
        rows,
        "--latency",
        str(_latency(tmp_path)),
        "--memory",
        str(_memory(tmp_path)),
        "--target-hardware",
        str(_target(tmp_path)),
        "--red-flag-report",
        str(_red_flag_report(tmp_path, 12, 12)),
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
    # 16,000 items either way: 800 scenarios of 20 (above the 780 minimum, which
    # counts scenarios), or 16,000 independent ones.
    def rows(scenario_size: int) -> list[dict]:
        out = []
        for k in range(16_000):
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
    assert (
        sum(int(b.get("data-count")) for b in bars)
        == spec.allocation_totals(spec.TEST_ALLOCATION)["items"]
    )
    report = json.loads((big / "r" / "gate_report.json").read_text())
    assert any(r["gate"] == "X-ECE" and r["point"] is not None for r in report["rows"])


def test_ece_of_a_known_miscalibration(tmp_path, capsys):
    """Everything right at confidence 0.7: ECE is exactly 0.3."""
    _, out = _run(tmp_path, _full_allocation(confidence=0.7), capsys=capsys)
    line = _line(out, "expected calibration error")
    assert "0.3000" in line and "NOT MET" in line


def test_the_repository_latency_record_has_no_samples_so_no_verdict():
    """latency_v2d.json stores percentiles only. A percentile without its interval,
    from an unnamed machine, is not a gate result (it used to score MET)."""
    record = Path(__file__).resolve().parents[1] / "training" / "latency_v2d.json"
    latency = gate.measurement_rows(record, None)[0]
    assert latency.gate == "14"
    assert latency.verdict.startswith("NOT MEASURED")
    assert "samples" in latency.verdict
    assert latency.point is None and latency.note is None


def _latency(
    tmp: Path, cpu: str = "Test CPU", center: float = 60.0, n: int = 1000
) -> Path:
    rng = np.random.default_rng(3)
    samples = (center + rng.gamma(2.0, 5.0, size=n)).round(3).tolist()
    path = tmp / "latency.json"
    path.write_text(json.dumps({"machine": {"cpu": cpu}, "samples_ms": samples}))
    return path


def _memory(tmp: Path, cpu: str = "Test CPU", peak: float = 1400.0) -> Path:
    path = tmp / "memory.json"
    path.write_text(
        json.dumps({"machine": {"cpu": cpu}, "peak_rss_mb": peak, "concurrency": 50})
    )
    return path


def _target(tmp: Path, cpu: str = "Test CPU") -> Path:
    path = tmp / "target.json"
    path.write_text(json.dumps({"cpu": cpu}))
    return path


def test_latency_is_reported_with_intervals(tmp_path):
    latency = gate.measurement_rows(_latency(tmp_path), None, _target(tmp_path))[0]
    assert latency.verdict == gate.VERDICT_MET
    assert re.search(r"p50 [\d.]+ ms \[[\d.]+, [\d.]+\]", latency.note), latency.note
    assert re.search(r"p95 [\d.]+ ms \[[\d.]+, [\d.]+\]", latency.note), latency.note


def test_latency_with_fewer_than_the_minimum_samples_is_refused(tmp_path):
    latency = gate.measurement_rows(_latency(tmp_path, n=999), None, _target(tmp_path))[
        0
    ]
    assert latency.verdict == "INSUFFICIENT DATA (n=999, need 1000)"
    assert latency.note is None


def test_without_a_named_target_machine_no_hardware_gate_is_met(tmp_path):
    rows = gate.measurement_rows(_latency(tmp_path), _memory(tmp_path), None)
    for row in rows:
        assert row.verdict.startswith("NOT DEMONSTRATED"), row
        assert "H15" in row.verdict


def test_measurements_from_another_machine_do_not_count(tmp_path):
    rows = gate.measurement_rows(
        _latency(tmp_path, cpu="Laptop"),
        _memory(tmp_path, cpu="Laptop"),
        _target(tmp_path),
    )
    for row in rows:
        assert row.verdict.startswith("NOT DEMONSTRATED"), row
        assert "Laptop" in row.verdict


def test_a_p95_whose_interval_crosses_the_threshold_is_not_met(tmp_path):
    latency = gate.measurement_rows(
        _latency(tmp_path, center=190.0), None, _target(tmp_path)
    )[0]
    assert latency.verdict != gate.VERDICT_MET


def test_legacy_names_are_still_importable():
    from training.evaluate import (  # noqa: F401
        MINIMUM_CRITICAL_RECALL,
        load_manifest,
        triage_gate,
    )

    assert MINIMUM_CRITICAL_RECALL == 0.95


# ── The gate is the only thing evaluate.py runs ───────────────────────────────
@pytest.mark.parametrize(
    "argv",
    [
        ["--model", "saved_model_holdout"],
        ["--writeup", "run.json"],
        ["--manifest", "dataset/processed/eval_manifest_phrase_v2.json"],
    ],
)
def test_evaluate_no_longer_hands_off_to_the_unrefused_holdout_report(argv, capsys):
    """These arguments used to reach holdout_eval, which prints accuracy on the
    nine-sentence set with no minimum-n refusal and applies the superseded 0.95
    three-condition gate. The deployment-gate entry point must not print that."""
    with pytest.raises(SystemExit) as refused:
        gate.main(argv)
    assert refused.value.code == 2
    err = capsys.readouterr().err
    assert "holdout_eval.py" in err
    assert "not a deployment gate" in err.lower()


def test_the_holdout_report_says_it_is_not_the_gate(capsys):
    from training import holdout_eval

    with pytest.raises(SystemExit):
        holdout_eval.main_argv(["--help"])
    assert "NOT A DEPLOYMENT GATE" in capsys.readouterr().out
