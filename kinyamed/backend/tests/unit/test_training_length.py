"""The serving max_length must be the model's training max_length.

v2d was fine-tuned at 96 and served at MODEL_MAX_LENGTH=512 (MODEL_AUDIT §2).
Nothing current exceeds 94 tokens, so no number measured to date is affected,
but a longer real report would be classified at lengths the model never saw in
fine-tuning. The model directory now records its training length, and the
service refuses to start when the configured length differs or is unknowable.

No weights are loaded here: the check runs before the model is.
"""

from __future__ import annotations

import json

import pytest
from app.services import model_classifier as mc


def _model_dir(tmp_path, metadata: dict | None):
    directory = tmp_path / "model"
    directory.mkdir()
    if metadata is not None:
        (directory / mc.TRAINING_METADATA).write_text(json.dumps(metadata))
    return directory


def test_the_recorded_training_length_is_used_when_none_is_configured(tmp_path):
    directory = _model_dir(tmp_path, {"max_length": 96})
    assert mc.resolve_max_length(directory, configured=None) == 96


def test_a_configured_length_equal_to_the_training_length_is_accepted(tmp_path):
    directory = _model_dir(tmp_path, {"max_length": 96})
    assert mc.resolve_max_length(directory, configured=96) == 96


def test_a_configured_length_that_differs_is_refused(tmp_path):
    directory = _model_dir(tmp_path, {"max_length": 96})
    with pytest.raises(mc.ModelConfigurationError) as refused:
        mc.resolve_max_length(directory, configured=512)
    assert "512" in str(refused.value) and "96" in str(refused.value)


@pytest.mark.parametrize(
    "metadata",
    [None, {}, {"max_length": "96"}, {"max_length": 0}, {"max_length": True}],
)
def test_a_model_that_does_not_record_a_valid_training_length_is_refused(
    tmp_path, metadata
):
    directory = _model_dir(tmp_path, metadata)
    with pytest.raises(mc.ModelConfigurationError, match="training max_length"):
        mc.resolve_max_length(directory, configured=None)


def test_build_classifier_raises_on_a_mismatch_instead_of_quietly_returning_none(
    tmp_path, monkeypatch
):
    """A missing model fails closed (503) and the service stays up. A model whose
    length is wrong is a configuration error: it must stop start-up, not hide."""
    directory = _model_dir(tmp_path, {"max_length": 96})
    monkeypatch.setattr(mc.settings, "TRIAGE_MODEL_PATH", str(directory), raising=False)
    monkeypatch.setattr(mc.settings, "MODEL_MAX_LENGTH", 512, raising=False)
    with pytest.raises(mc.ModelConfigurationError):
        mc.build_classifier()


def test_the_service_refuses_to_start_on_a_mismatch(tmp_path, monkeypatch):
    import main
    from app.services import triage_service
    from fastapi.testclient import TestClient

    directory = _model_dir(tmp_path, {"max_length": 96})
    monkeypatch.setattr(mc.settings, "TRIAGE_MODEL_PATH", str(directory), raising=False)
    monkeypatch.setattr(mc.settings, "MODEL_MAX_LENGTH", 512, raising=False)
    triage_service.get_classifier.cache_clear()
    try:
        with pytest.raises(mc.ModelConfigurationError), TestClient(main.app):
            pass
    finally:
        triage_service.get_classifier.cache_clear()


def test_the_default_setting_no_longer_forces_a_length():
    from app.core.config import Settings

    assert Settings.model_fields["MODEL_MAX_LENGTH"].default is None


# ── Recording the length for an existing model, from its own run record ───────
def test_the_length_is_recorded_from_the_training_run_record(tmp_path):
    from scripts import record_training_length as record

    directory = _model_dir(tmp_path, None)
    run = tmp_path / "last_run.json"
    run.write_text(json.dumps({"args": {"max_length": "96", "seed": "42"}}))
    assert record.main(["--model", str(directory), "--run-record", str(run)]) == 0
    written = json.loads((directory / mc.TRAINING_METADATA).read_text())
    assert written["max_length"] == 96
    assert written["source"].endswith("last_run.json")


def test_recording_refuses_a_run_record_without_the_length(tmp_path):
    from scripts import record_training_length as record

    directory = _model_dir(tmp_path, None)
    run = tmp_path / "last_run.json"
    run.write_text(json.dumps({"args": {"seed": "42"}}))
    assert record.main(["--model", str(directory), "--run-record", str(run)]) == 2
    assert not (directory / mc.TRAINING_METADATA).exists()


def test_recording_never_overwrites_a_different_length(tmp_path):
    from scripts import record_training_length as record

    directory = _model_dir(tmp_path, {"max_length": 128})
    run = tmp_path / "last_run.json"
    run.write_text(json.dumps({"args": {"max_length": "96"}}))
    assert record.main(["--model", str(directory), "--run-record", str(run)]) == 2
    assert (
        json.loads((directory / mc.TRAINING_METADATA).read_text())["max_length"] == 128
    )


def test_the_script_and_the_service_name_the_same_metadata_file():
    from scripts import record_training_length as record

    assert record.TRAINING_METADATA == mc.TRAINING_METADATA
