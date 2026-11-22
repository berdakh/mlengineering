"""A bundle written to disk by save_bundle, read back by load_bundle and served end to end."""
import json

import pytest
from fastapi.testclient import TestClient

from flowguard.api import create_app
from flowguard.bundle import BundleError, load_bundle, save_bundle
from flowguard.scoring import ZScoreModel


def test_round_trip_and_serving(tmp_path):
    model = ZScoreModel("flow_rate", 100, 7.25, 30, 10, "it-1")
    directory = save_bundle(model, tmp_path / "b")
    assert load_bundle(directory) == model
    manifest = json.loads((directory / "MANIFEST.json").read_text())
    assert set(manifest["files"]) == {"model.json"}
    with TestClient(create_app(directory)) as client:
        data = client.post("/predict", json={"burn_in": [9.0, 11.0], "values": [17.25, 10.0]}).json()
    assert data["scores"] == pytest.approx([7.25, 0.0])
    assert data["above_threshold"] == [True, False]


def test_missing_file_is_a_bundle_error(tmp_path):
    directory = save_bundle(ZScoreModel("flow_rate", 100, 3.0, 30, 10, "it-2"), tmp_path / "b")
    (directory / "model.json").unlink()
    with pytest.raises(BundleError):
        load_bundle(directory)
