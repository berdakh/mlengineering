"""Fixtures for the failure-injection suite: a tiny SYNTHETIC bundle and an app factory with faults."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from flowguard.bundle import save_bundle
from flowguard.scoring import ZScoreModel
from flowguard.settings import Settings

SETTINGS = Settings(deadline_s=0.2, max_inflight=2, retry_after_s=1,
                    support_low=0.0, support_high=200.0, envelope_low=20.0, envelope_high=130.0)


@pytest.fixture()
def bundle_dir(tmp_path):
    model = ZScoreModel(sensor="flow_rate", n_burn_in=10, threshold=3.0, min_duration=1, merge_gap=0,
                        model_version="synthetic-1")
    return save_bundle(model, tmp_path / "bundle")


@pytest.fixture()
def make_client(bundle_dir):
    from flowguard.api import create_app
    clients = []

    def _make(faults=None, settings=SETTINGS, model_dir=None):
        c = TestClient(create_app(model_dir or bundle_dir, settings=settings, faults=faults or {}),
                       raise_server_exceptions=False)
        c.__enter__()
        clients.append(c)
        return c

    yield _make
    for c in clients:
        c.__exit__(None, None, None)


BODY = {"burn_in": [100.0, 101.0, 99.0, 100.5, 99.5, 100.2, 99.8, 100.1, 99.9, 100.0],
        "values": [100.0, 100.3, 150.0, 10.0]}
