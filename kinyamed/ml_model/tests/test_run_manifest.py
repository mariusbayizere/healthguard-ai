"""training/run_manifest.py: everything needed to re-run a training run (docs/ENGINEERING_SPEC.md L6, L8,
§10.8: seed, config, data hash, code commit, environment).

A run with a dirty tree, an unset seed, or an unhashed input still gets a manifest,
but the manifest says it is NOT REPRODUCIBLE and why.
"""

from __future__ import annotations

import getpass
import hashlib
import json
import socket
import subprocess
from datetime import datetime

import pytest
from training import run_manifest as rm


def _git(repo, *args):
    subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@example.invalid",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@example.invalid",
            "PATH": "/usr/bin:/bin",
            "HOME": str(repo),
        },
    )


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q")
    (root / "data").mkdir()
    (root / "data" / "train.csv").write_text("text,label\na,CRITICAL\n")
    (root / "config.json").write_text("{}")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "init")
    return root


def _started(repo, **overrides):
    kwargs = {
        "repo": repo,
        "seed": 42,
        "config": {"learning_rate": 1e-5, "max_length": 96},
        "inputs": {"train": repo / "data" / "train.csv"},
    }
    kwargs.update(overrides)
    return rm.RunManifest.start(**kwargs)


def test_every_input_and_output_is_recorded_with_its_sha256(repo):
    run = _started(repo)
    out = repo / "model" / "weights.bin"
    out.parent.mkdir()
    out.write_bytes(b"\x00\x01")
    record = run.finish(outputs={"weights": out}, results={}).record
    train = (repo / "data" / "train.csv").read_bytes()
    assert record["inputs"]["train"]["sha256"] == hashlib.sha256(train).hexdigest()
    assert (
        record["outputs"]["weights"]["sha256"]
        == hashlib.sha256(b"\x00\x01").hexdigest()
    )
    assert record["inputs"]["train"]["bytes"] == len(train)


def test_paths_are_recorded_relative_to_the_repository(repo):
    record = _started(repo).finish(outputs={}, results={}).record
    assert record["inputs"]["train"]["path"] == "data/train.csv"


def test_a_clean_tree_at_a_commit_with_a_seed_is_reproducible(repo):
    record = _started(repo).finish(outputs={}, results={}).record
    head = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True
    ).stdout.strip()
    assert record["code"] == {"commit": head, "dirty": False, "dirty_paths": []}
    assert record["reproducible"] is True
    assert record["not_reproducible_because"] == []


def test_a_dirty_tree_is_recorded_and_makes_the_run_not_reproducible(repo):
    (repo / "config.json").write_text('{"changed": true}')
    record = _started(repo).finish(outputs={}, results={}).record
    assert record["code"]["dirty"] is True
    assert "config.json" in record["code"]["dirty_paths"]
    assert record["reproducible"] is False
    assert any("uncommitted" in r for r in record["not_reproducible_because"])


def test_an_unset_seed_makes_the_run_not_reproducible(repo):
    record = _started(repo, seed=None).finish(outputs={}, results={}).record
    assert record["reproducible"] is False
    assert any("seed" in r for r in record["not_reproducible_because"])


def test_outside_a_git_checkout_the_code_is_unidentified_not_guessed(tmp_path):
    data = tmp_path / "train.csv"
    data.write_text("x")
    record = (
        rm.RunManifest.start(repo=tmp_path, seed=1, config={}, inputs={"train": data})
        .finish(outputs={}, results={})
        .record
    )
    assert record["code"]["commit"] is None
    assert record["reproducible"] is False


def test_a_missing_input_is_refused_before_the_run_starts(repo):
    with pytest.raises(FileNotFoundError):
        _started(repo, inputs={"train": repo / "data" / "absent.csv"})


def test_the_environment_and_machine_are_recorded(repo):
    record = _started(repo).finish(outputs={}, results={}).record
    env = record["environment"]
    assert env["python"].count(".") == 2
    # Every tracked package is listed, installed or not: CI's dependency-free job has
    # no numpy, and the record must say None there rather than omit it.
    assert set(env["packages"]) == set(rm.PACKAGES)
    assert all(v is None or isinstance(v, str) for v in env["packages"].values())
    assert rm.package_versions(["pytest"])["pytest"]  # installed wherever tests run
    assert "not-a-real-package-kinyamed" in rm.package_versions(
        ["not-a-real-package-kinyamed"]
    )
    assert (
        rm.package_versions(["not-a-real-package-kinyamed"])[
            "not-a-real-package-kinyamed"
        ]
        is None
    )
    assert record["machine"]["cpu_count"] >= 1
    assert "architecture" in record["machine"]


def test_no_username_or_hostname_is_written(repo):
    """L11: the manifest is committed and published alongside results."""
    text = json.dumps(_started(repo).finish(outputs={}, results={}).record)
    assert f'"{socket.gethostname()}"' not in text
    assert f"/{getpass.getuser()}/" not in text


def test_start_and_finish_are_utc_and_ordered(repo):
    record = _started(repo).finish(outputs={}, results={}).record
    started = datetime.fromisoformat(record["started_at"])
    finished = datetime.fromisoformat(record["finished_at"])
    assert started.utcoffset().total_seconds() == 0
    assert finished >= started


def test_a_refused_run_is_recorded_as_refused_with_its_reasons(repo):
    record = (
        _started(repo)
        .refuse(["english CRITICAL: 1 distinct scenarios, need 627"])
        .record
    )
    assert record["status"] == "refused"
    assert record["refusal"] == ["english CRITICAL: 1 distinct scenarios, need 627"]
    assert record["outputs"] == {}
    assert record["reproducible"] is True  # the refusal itself re-runs identically


def test_a_failed_run_is_recorded_as_failed(repo):
    record = _started(repo).fail("RuntimeError: out of memory").record
    assert record["status"] == "failed"
    assert record["error"] == "RuntimeError: out of memory"


def test_the_manifest_round_trips_and_verifies(repo, tmp_path):
    path = tmp_path / "run.json"
    _started(repo).finish(outputs={}, results={"temperature": 1.3}).write(path)
    assert json.loads(path.read_text())["results"] == {"temperature": 1.3}
    assert rm.verify(path, repo) == []


def test_verification_names_an_input_that_changed_since_the_run(repo, tmp_path):
    path = tmp_path / "run.json"
    _started(repo).finish(outputs={}, results={}).write(path)
    (repo / "data" / "train.csv").write_text("text,label\nb,ROUTINE\n")
    problems = rm.verify(path, repo)
    assert len(problems) == 1 and "data/train.csv" in problems[0]


def test_a_manifest_cannot_be_finished_twice(repo):
    run = _started(repo).finish(outputs={}, results={})
    with pytest.raises(RuntimeError):
        run.finish(outputs={}, results={})


def test_untracked_code_is_dirty_but_untracked_documents_are_not(repo):
    """An untracked module could be imported by the run; an untracked PDF cannot."""
    (repo / "notes.pdf").write_bytes(b"%PDF")
    assert (
        _started(repo).finish(outputs={}, results={}).record["code"]["dirty"] is False
    )
    (repo / "helper.py").write_text("X = 1\n")
    record = _started(repo).finish(outputs={}, results={}).record
    assert record["code"]["dirty"] is True
    assert "helper.py" in record["code"]["dirty_paths"]


def test_an_input_read_later_in_the_run_is_added_with_its_hash(repo):
    """The pipeline reads the training corpus only after the eval sets pass."""
    run = _started(repo, inputs={})
    run.add_input("train", repo / "data" / "train.csv")
    record = run.finish(outputs={}, results={}).record
    assert record["inputs"]["train"]["path"] == "data/train.csv"
    with pytest.raises(RuntimeError):
        run.add_input("late", repo / "config.json")
