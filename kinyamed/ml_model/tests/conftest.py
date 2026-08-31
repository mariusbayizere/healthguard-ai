"""Shared fixtures. Tests run from the ml_model directory, which is how every
script in this project resolves its relative default paths."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ML_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ML_ROOT))


@pytest.fixture(scope="session")
def ml_root() -> Path:
    return ML_ROOT


@pytest.fixture(scope="session")
def sample_manifest() -> dict:
    return json.loads((ML_ROOT / "dataset/sample/sample_manifest.json").read_text())


@pytest.fixture(scope="session")
def sample_csv() -> Path:
    return ML_ROOT / "dataset/sample/symptoms_sample.csv"


def sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()
