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


@pytest.fixture(autouse=True)
def _reset_corpus_version():
    """Leave every test on v2, whatever it selected.

    use_corpus_version rebinds module globals, so a v1 selection persists for the
    rest of the process. That is fine in a one-shot script and wrong in a test
    suite: the first time these tests pinned v1 they broke four later tests that
    had selected nothing at all.
    """
    yield
    import dataset.generate_large_dataset as G
    import dataset.split_dataset as SD
    G.use_corpus_version(2)
    SD.use_corpus_version(2)
