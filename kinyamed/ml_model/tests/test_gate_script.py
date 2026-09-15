"""scripts/gate_on_current_holdout.py must stop at the gate, not after inference."""

from __future__ import annotations

import csv
import importlib.util
from pathlib import Path

import pytest

pytest.importorskip("numpy", reason="the gate's counts need numpy")

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "gate_on_current_holdout.py"


def _load():
    spec = importlib.util.spec_from_file_location("gate_on_current_holdout", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_an_unmeasurable_gold_set_stops_before_the_model_is_loaded(
    tmp_path, monkeypatch, capsys
):
    script = _load()
    gold = tmp_path / "gold.csv"
    with gold.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["item_id", "text", "language", "gold_label", "scenario_id", "split"]
        )
        for k in range(900):
            writer.writerow(
                [f"r{k}", "synthetic", "kinyarwanda", "CRITICAL", f"s{k % 4}", "test"]
            )

    def fake_build_gold():
        return 900, 4

    def model_must_not_load(*args, **kwargs):
        raise AssertionError("inference ran on a gold set the gate cannot measure")

    from training import evaluate as gate

    monkeypatch.setattr(script, "GOLD", gold)
    monkeypatch.setattr(script, "build_gold", fake_build_gold)
    monkeypatch.setattr(gate, "predict_with_model", model_must_not_load)
    assert script.main(["--model", str(tmp_path / "model")]) == 2
    assert "No gate cell can be measured" in capsys.readouterr().out
