"""Shared fixtures: a bundle factory and a started client. Every test builds its own bundle in tmp_path."""
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "service"))   # local runs; harmless if absent

from flowguard.api import create_app  # noqa: E402
from flowguard.bundle import save_bundle  # noqa: E402
from flowguard.scoring import ZScoreModel  # noqa: E402

THRESHOLD = 3.0
MODEL_VERSION = "test-2026.11"


@pytest.fixture
def model() -> ZScoreModel:
    return ZScoreModel(sensor="flow_rate", n_burn_in=100, threshold=THRESHOLD, min_duration=30,
                       merge_gap=10, model_version=MODEL_VERSION)


@pytest.fixture
def bundle_dir(tmp_path, model) -> Path:
    return save_bundle(model, tmp_path / "bundle")


@pytest.fixture
def client(bundle_dir):
    """A client whose app has run its startup (lifespan), so the bundle is loaded."""
    with TestClient(create_app(bundle_dir)) as c:
        yield c


@pytest.fixture
def degraded_client(tmp_path):
    """A started app whose model directory holds no bundle."""
    (tmp_path / "empty").mkdir()
    with TestClient(create_app(tmp_path / "empty")) as c:
        yield c


def body(burn_in=(-1.0, 1.0), values=(0.0,)):
    """burn_in (-1, 1) has mean 0 and population std 1, so score = |value|."""
    return {"burn_in": list(burn_in), "values": list(values)}
