"""Guards on the numbers the paper is allowed to report.

A published figure must trace to a verified run. These tests make the failure
mode — a hand-typed number reaching a draft — impossible to introduce quietly.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

GENERATED = Path("paper/generated")
MACROS = GENERATED / "results_macros.tex"
TABLE = GENERATED / "results_table.tex"

# A provenance block is what distinguishes a generated result from a typed one.
PROVENANCE_KEYS = ("generated_at", "git_commit", "eval_sha256", "source_sha256")


def test_generated_files_exist(ml_root: Path) -> None:
    """The paper \\inputs these; a missing file means a broken build, not a blank."""
    assert (ml_root / MACROS).exists(), f"{MACROS} is missing"
    assert (ml_root / TABLE).exists(), f"{TABLE} is missing"


def macro_values(text: str) -> dict[str, str]:
    return dict(re.findall(r"\\newcommand\{\\(\w+)\}\{(.*)\}", text))


def test_every_reported_number_is_either_tbd_or_provenanced(ml_root: Path) -> None:
    """The core guard.

    Either the macros are unfilled TBD tokens, or the file carries the full
    provenance of the run that produced them. A file with concrete numbers and
    no provenance is a hand-edited figure, which is exactly what must not ship.
    """
    text = (ml_root / MACROS).read_text()
    values = macro_values(text)
    assert values, "no macros defined; the paper would fail to compile"

    has_provenance = all(f"% {key}:" in text for key in PROVENANCE_KEYS)
    numeric = {
        name: value
        for name, value in values.items()
        if re.search(r"\d", value) and "TBD" not in value
    }
    if numeric and not has_provenance:
        pytest.fail(
            "results_macros.tex contains concrete numbers but no provenance block.\n"
            f"  offending macros: {sorted(numeric)}\n"
            "  A reported figure must come from training/evaluate.py, not by hand."
        )


def test_placeholder_reports_no_performance_figure(ml_root: Path) -> None:
    """While untrained, no macro may expand to something that reads as a score."""
    text = (ml_root / MACROS).read_text()
    if all(f"% {key}:" in text for key in PROVENANCE_KEYS):
        pytest.skip("a real run has filled these in; the provenance test covers it")

    for name, value in macro_values(text).items():
        assert "TBD" in value, (
            f"\\{name} expands to {value!r} but no run has produced it. "
            "Placeholders must stay visibly unfilled."
        )


def test_table_placeholder_is_marked_as_such(ml_root: Path) -> None:
    text = (ml_root / TABLE).read_text()
    if all(f"% {key}:" in text for key in PROVENANCE_KEYS):
        pytest.skip("a real run has filled the table in")
    assert "TBD" in text
    assert "No results yet" in text, (
        "an unfilled table must say so in its caption, where a reader will see it"
    )


def test_generated_files_warn_against_hand_editing(ml_root: Path) -> None:
    for path in (MACROS, TABLE):
        text = (ml_root / path).read_text()
        assert "DO NOT EDIT" in text.upper(), f"{path} lacks a do-not-edit banner"


def test_evaluate_refuses_a_drifted_split(ml_root: Path, tmp_path: Path) -> None:
    """A score computed against rows the manifest does not describe is untraceable."""
    from training.evaluate import load_manifest

    real = ml_root / "dataset/processed/eval_manifest_phrase_v1.json"
    if not real.exists():
        pytest.skip("phrase manifest is built by `make dataset`")

    manifest = json.loads(real.read_text())
    manifest["files"]["eval"]["sha256"] = "0" * 64
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(manifest))

    with pytest.raises(SystemExit) as excinfo:
        load_manifest(tampered)
    assert "drifted" in str(excinfo.value).lower()
