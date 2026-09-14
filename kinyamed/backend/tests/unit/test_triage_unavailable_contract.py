"""The frontend's 503 fixture is the 503 the API actually sends.

The Playwright test that proves a nurse sees the manual-triage instruction
cannot reach a real API, so it serves a recorded response. A recording drifts
silently when the message changes; this test fails instead.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from app.core.config import settings
from app.core.exceptions import TriageModelUnavailableError

FRONTEND = Path(__file__).resolve().parents[3] / "frontend"
FIXTURE = FRONTEND / "e2e" / "fixtures" / "triage-model-unavailable.json"


@pytest.mark.skipif(not FRONTEND.exists(), reason="frontend package absent")
def test_the_frontend_fixture_is_the_real_503() -> None:
    error = TriageModelUnavailableError(settings.TRIAGE_UNAVAILABLE_RETRY_AFTER_SECONDS)
    expected = {
        "status": error.status_code,
        "headers": error.headers,
        "body": {
            "error": {
                "code": error.code,
                "message": error.message,
                "details": error.details,
            }
        },
    }
    assert FIXTURE.exists(), f"{FIXTURE} is missing"
    assert json.loads(FIXTURE.read_text(encoding="utf-8")) == expected
