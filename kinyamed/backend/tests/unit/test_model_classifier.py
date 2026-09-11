"""AUDIT 1.5 — production must not serve triage from the keyword baseline."""

from __future__ import annotations

import pytest
from app.services import model_classifier as mc


@pytest.mark.parametrize(
    "environment,expect_raise",
    [("production", True), ("development", False), ("test", False)],
)
def test_production_refuses_to_start_on_the_baseline(
    monkeypatch, environment: str, expect_raise: bool
) -> None:
    """A missing TRIAGE_MODEL_PATH is a boot failure in production only.

    The baseline has never been evaluated against the holdout. A deployment
    that forgets one environment variable must fail loudly rather than quietly
    serve triage from a keyword matcher.
    """
    monkeypatch.setattr(mc.settings, "ENVIRONMENT", environment, raising=False)
    monkeypatch.setattr(mc.settings, "TRIAGE_MODEL_PATH", "", raising=False)

    if expect_raise:
        with pytest.raises(mc.BaselineInProductionError) as excinfo:
            mc.build_classifier()
        # The message must say what to do, not merely what went wrong.
        assert "TRIAGE_MODEL_PATH" in str(excinfo.value)
    else:
        classifier, description = mc.build_classifier()
        assert classifier is not None
        assert "keyword baseline" in description


def test_production_refuses_when_the_model_path_does_not_exist(monkeypatch) -> None:
    """A configured-but-absent model is the more dangerous case: configuration
    claims a model is in use and the service would silently disagree."""
    monkeypatch.setattr(mc.settings, "ENVIRONMENT", "production", raising=False)
    monkeypatch.setattr(
        mc.settings, "TRIAGE_MODEL_PATH", "/nonexistent/model", raising=False
    )
    with pytest.raises(mc.BaselineInProductionError):
        mc.build_classifier()
