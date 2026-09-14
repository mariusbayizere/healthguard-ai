"""Model selection returns the trained model or nothing, in every environment.

There is no fallback classifier. A configuration that cannot produce a loaded
model yields `None` and a reason, and the triage endpoint turns `None` into a
503 (tests/integration/test_fail_closed.py).
"""

from __future__ import annotations

import pytest
from app.services import model_classifier as mc

ENVIRONMENTS = ("production", "staging", "development")


@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_unset_model_path_yields_no_classifier(monkeypatch, environment: str) -> None:
    monkeypatch.setattr(mc.settings, "ENVIRONMENT", environment, raising=False)
    monkeypatch.setattr(mc.settings, "TRIAGE_MODEL_PATH", "", raising=False)

    classifier, reason = mc.build_classifier()

    assert classifier is None
    assert "TRIAGE_MODEL_PATH" in reason


@pytest.mark.parametrize("environment", ENVIRONMENTS)
def test_missing_model_directory_yields_no_classifier(
    monkeypatch, environment: str
) -> None:
    monkeypatch.setattr(mc.settings, "ENVIRONMENT", environment, raising=False)
    monkeypatch.setattr(
        mc.settings, "TRIAGE_MODEL_PATH", "/nonexistent/model", raising=False
    )

    classifier, reason = mc.build_classifier()

    assert classifier is None
    assert "/nonexistent/model" in reason


def test_an_unloadable_artefact_yields_no_classifier(monkeypatch, tmp_path) -> None:
    """A directory that exists but holds no model must not become any classifier."""
    monkeypatch.setattr(mc.settings, "TRIAGE_MODEL_PATH", str(tmp_path), raising=False)

    classifier, reason = mc.build_classifier()

    assert classifier is None
    assert reason


def test_missing_ml_dependencies_yield_no_classifier(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(mc.settings, "TRIAGE_MODEL_PATH", str(tmp_path), raising=False)

    def _no_torch(*_args, **_kwargs):
        raise ImportError("No module named 'torch'")

    monkeypatch.setattr(mc, "ModelClassifier", _no_torch)

    classifier, reason = mc.build_classifier()

    assert classifier is None
    assert "torch" in reason
