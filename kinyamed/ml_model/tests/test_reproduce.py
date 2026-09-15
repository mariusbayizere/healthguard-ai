"""reproduce.py: `make reproduce` (docs/ENGINEERING_SPEC.md §14). Every committed output it covers is
re-derived and diffed; refusals must still refuse; nothing it runs may dirty the tree."""

from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

import reproduce as rp

ML_ROOT = Path(__file__).resolve().parent.parent
REPO = ML_ROOT.parent.parent


def _py(code: str) -> list[str]:
    return [sys.executable, "-c", code]


def test_a_step_passes_on_its_expected_exit_code(tmp_path):
    assert rp.run_step(rp.Step("ok", _py("pass"), tmp_path)).ok
    refused = rp.Step("refuses", _py("raise SystemExit(2)"), tmp_path, expected_exit=2)
    assert rp.run_step(refused).ok


def test_a_step_that_exits_differently_fails(tmp_path):
    """A refusal that stops refusing is a regression, not a pass."""
    result = rp.run_step(rp.Step("x", _py("pass"), tmp_path, expected_exit=2))
    assert not result.ok and "exit 0, expected 2" in result.detail


def test_output_identical_to_the_committed_file_passes(tmp_path):
    committed = tmp_path / "out.txt"
    committed.write_text("a\nb\n")
    step = rp.Step(
        "same", _py("print('a'); print('b')"), tmp_path, compare_to=committed
    )
    assert rp.run_step(step).ok


def test_output_that_differs_fails_and_names_the_first_difference(tmp_path):
    committed = tmp_path / "out.txt"
    committed.write_text("a\nb\n")
    step = rp.Step(
        "diff", _py("print('a'); print('c')"), tmp_path, compare_to=committed
    )
    result = rp.run_step(step)
    assert not result.ok and "line 2" in result.detail


def test_stderr_can_be_the_compared_stream(tmp_path):
    committed = tmp_path / "err.txt"
    committed.write_text("refused\n")
    step = rp.Step(
        "err",
        _py("import sys; print('refused', file=sys.stderr); raise SystemExit(2)"),
        tmp_path,
        expected_exit=2,
        compare_to=committed,
        stream="stderr",
    )
    assert rp.run_step(step).ok


def test_a_file_already_matching_its_digest_is_not_regenerated(tmp_path):
    target = tmp_path / "f.csv"
    target.write_bytes(b"x")
    digest = hashlib.sha256(b"x").hexdigest()
    assert rp.matches_digest(target, digest)
    assert not rp.matches_digest(tmp_path / "absent.csv", digest)


def test_every_compared_output_is_a_tracked_file():
    tracked = set(
        subprocess.run(
            ["git", "-C", str(REPO), "ls-files"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
    )
    compared = [s.compare_to for s in rp.steps() if s.compare_to is not None]
    assert len(compared) >= 4
    for path in compared:
        assert path.resolve().relative_to(REPO.resolve()).as_posix() in tracked, path


def test_the_n9_refusals_are_expected_to_exit_2():
    by_name = {s.name: s for s in rp.steps()}
    assert by_name["gate --check-gold on the n=9 set"].expected_exit == 2
    assert by_name["training pipeline on the n=9 set"].expected_exit == 2


def test_what_is_left_out_is_listed_with_a_reason():
    names = " ".join(item for item, _ in rp.NOT_REPRODUCED)
    assert "tokenizer" in names and "latency" in names
    assert all(reason for _, reason in rp.NOT_REPRODUCED)


def test_missing_dependencies_are_named_before_any_step_runs(monkeypatch, capsys):
    """A clean clone run with an interpreter lacking the pinned packages failed only at
    step 7, after 14 minutes of regeneration. It must fail first, and say what to do."""
    ran = []
    monkeypatch.setattr(rp, "REQUIRED_MODULES", ("json", "not_a_module_kinyamed"))
    monkeypatch.setattr(
        rp, "run_step", lambda step: ran.append(step) or rp.Result(True, "")
    )
    monkeypatch.setattr(
        rp, "ensure_phrase_v2_split", lambda: ran.append("split") or rp.Result(True, "")
    )
    assert rp.main() == 1
    out = capsys.readouterr().out
    assert ran == []
    assert "not_a_module_kinyamed" in out and "make install" in out


def test_the_required_modules_cover_what_the_steps_import():
    assert {"numpy", "pandas", "torch"} <= set(rp.REQUIRED_MODULES)


# ── The environment is pinned in the repository, not on one machine ──────────
# A clean clone in /tmp ran steps 1-6 and failed 7-8: outside the author's home
# directory pyenv fell back to a system Python without the packages. The fix must
# not depend on anything outside the clone.
def test_the_required_python_is_pinned_at_the_repository_root():
    pinned = (REPO / ".python-version").read_text().strip()
    major, minor = rp.REQUIRED_PYTHON
    assert pinned.startswith(f"{major}.{minor}.")


def test_a_wrong_python_is_refused_by_name_before_any_step(monkeypatch, capsys):
    ran = []
    monkeypatch.setattr(rp, "REQUIRED_PYTHON", (3, 99))
    monkeypatch.setattr(
        rp, "run_step", lambda step: ran.append(step) or rp.Result(True, "")
    )
    monkeypatch.setattr(
        rp, "ensure_phrase_v2_split", lambda: ran.append(1) or rp.Result(True, "")
    )
    assert rp.main() == 1
    assert ran == []
    assert "Python 3.99" in capsys.readouterr().out


def test_the_lock_file_pins_every_package_to_one_version():
    requirements = rp.read_lock(rp.LOCK_FILE)
    assert {"numpy", "pandas", "torch", "transformers"} <= requirements.keys()
    assert all(version for version in requirements.values())
    raw = [
        line.strip()
        for line in rp.LOCK_FILE.read_text().splitlines()
        if line.strip() and not line.startswith(("#", "--"))
    ]
    assert all("==" in line for line in raw), [line for line in raw if "==" not in line]


def test_the_lock_agrees_with_the_top_level_pins():
    lock = rp.read_lock(rp.LOCK_FILE)
    top = rp.read_lock(ML_ROOT / "requirements.txt")
    assert top and all(lock[name] == version for name, version in top.items())


def test_installed_versions_that_differ_from_the_lock_are_named():
    problems = rp.dependency_mismatches(
        {"numpy": "2.4.4", "pandas": "2.3.3", "absentpkg": "1.0"},
        installed=lambda name: {"numpy": "2.4.4", "pandas": "2.2.0"}.get(name),
    )
    assert problems == [
        "pandas 2.2.0 installed, 2.3.3 locked",
        "absentpkg not installed, 1.0 locked",
    ]


def test_an_environment_off_the_lock_is_refused_before_any_step(monkeypatch, capsys):
    ran = []
    monkeypatch.setattr(
        rp,
        "dependency_mismatches",
        lambda locked, installed=None: ["pandas 2.2.0 installed, 2.3.3 locked"],
    )
    monkeypatch.setattr(
        rp, "run_step", lambda step: ran.append(step) or rp.Result(True, "")
    )
    monkeypatch.setattr(
        rp, "ensure_phrase_v2_split", lambda: ran.append(1) or rp.Result(True, "")
    )
    assert rp.main() == 1
    out = capsys.readouterr().out
    assert ran == [] and "pandas 2.2.0" in out and "make reproduce-env" in out


def test_the_makefile_tells_a_reviewer_what_to_run_first():
    makefile = (REPO / "Makefile").read_text()
    assert "reproduce-env:" in makefile
    assert "requirements-reproduce.lock" in makefile
    assert ".venv-reproduce" in (REPO / ".gitignore").read_text()
