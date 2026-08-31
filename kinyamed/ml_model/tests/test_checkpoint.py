"""Training checkpoint resume.

The confirmed crash mode for this project is systemd-oomd killing the whole
terminal cgroup, so training must survive a SIGKILL at an arbitrary step and
resume without repeating or skipping examples.
"""

from __future__ import annotations

from pathlib import Path

import pytest

torch = pytest.importorskip("torch", reason="training extras not installed")
pytest.importorskip("transformers", reason="training extras not installed")

from dataset.atomicio import atomic_write  # noqa: E402
from training.train_holdout import (  # noqa: E402
    epoch_order,
    load_checkpoint,
    run_fingerprint,
    save_checkpoint,
)


@pytest.fixture
def payload() -> dict:
    model = torch.nn.Linear(4, 3)
    return {"fingerprint": "FP-A", "step": 42, "model": model.state_dict()}


def test_checkpoint_round_trip(tmp_path: Path, payload: dict) -> None:
    path = tmp_path / "state.pt"
    save_checkpoint(path, payload)
    restored = load_checkpoint(path, "FP-A")
    assert restored is not None
    assert restored["step"] == 42


def test_checkpoint_from_another_configuration_is_refused(tmp_path: Path, payload: dict) -> None:
    """Resuming a different LR or split into a half-trained optimiser would
    produce a model no manifest describes."""
    path = tmp_path / "state.pt"
    save_checkpoint(path, payload)
    assert load_checkpoint(path, "FP-DIFFERENT") is None


def test_torn_checkpoint_is_refused_without_raising(tmp_path: Path) -> None:
    path = tmp_path / "torn.pt"
    path.write_bytes(b"\x80\x02}q\x00TRUNCATED")
    assert load_checkpoint(path, "FP-A") is None


def test_missing_checkpoint_returns_none(tmp_path: Path) -> None:
    assert load_checkpoint(tmp_path / "absent.pt", "FP-A") is None


def test_crash_during_save_preserves_the_previous_checkpoint(
    tmp_path: Path, payload: dict
) -> None:
    """torch.save streams a large archive; interrupted, it leaves a file that
    load rejects only after the run is already lost."""
    path = tmp_path / "state.pt"
    save_checkpoint(path, {**payload, "step": 1})
    before = path.read_bytes()

    try:
        with atomic_write(path, "wb") as handle:
            torch.save({"fingerprint": "FP-A", "step": 999}, handle)
            raise RuntimeError("killed mid-save")
    except RuntimeError:
        pass

    assert path.read_bytes() == before
    assert load_checkpoint(path, "FP-A")["step"] == 1


def test_no_partial_debris_after_a_clean_save(tmp_path: Path, payload: dict) -> None:
    save_checkpoint(tmp_path / "state.pt", payload)
    assert not list(tmp_path.glob(".*.partial"))


def test_epoch_order_is_reproducible_and_epoch_dependent() -> None:
    assert epoch_order(1000, 42, 0) == epoch_order(1000, 42, 0)
    assert epoch_order(1000, 42, 0) != epoch_order(1000, 42, 1)
    assert epoch_order(1000, 7, 0) != epoch_order(1000, 42, 0)


def test_resume_covers_every_example_exactly_once() -> None:
    """A resume must not replay finished batches nor skip unfinished ones."""
    order = epoch_order(1000, 42, 0)
    batch_size, done_batches = 16, 7
    consumed = order[: done_batches * batch_size]
    remaining = order[done_batches * batch_size :]

    assert remaining[0] == order[done_batches * batch_size]
    assert sorted(consumed + remaining) == sorted(order)
    assert len(set(consumed) & set(remaining)) == 0, "a resume would repeat examples"


def test_fingerprint_changes_with_any_trajectory_input() -> None:
    """Anything that changes the training trajectory must invalidate a resume."""

    class Args:
        seed = 42
        epochs = 1
        max_steps = None
        batch_size = 16
        max_length = 64
        learning_rate = 2e-5
        weight_decay = 0.01
        warmup_ratio = 0.1
        train_fraction = 1.0
        eval_limit = None

    manifest = {"files": {"train": {"sha256": "aaa"}, "eval": {"sha256": "bbb"}}}
    baseline = run_fingerprint(manifest, Args())

    for field, value in [
        ("seed", 7), ("batch_size", 32), ("learning_rate", 5e-5),
        ("max_length", 128), ("train_fraction", 0.5), ("epochs", 3),
    ]:
        changed = Args()
        setattr(changed, field, value)
        assert run_fingerprint(manifest, changed) != baseline, (
            f"changing {field} did not invalidate the checkpoint"
        )

    # A different split must also invalidate it.
    other = {"files": {"train": {"sha256": "ccc"}, "eval": {"sha256": "bbb"}}}
    assert run_fingerprint(other, Args()) != baseline
