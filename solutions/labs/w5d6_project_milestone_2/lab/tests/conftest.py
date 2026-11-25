import numpy as np
import pandas as pd
import pytest

from flowguard.bundle import save_bundle
from flowguard.scoring import ZScoreModel


@pytest.fixture
def model() -> ZScoreModel:
    return ZScoreModel("flow_rate", 20, 3.0, 5, 2, "test-model")


@pytest.fixture
def bundle_dir(tmp_path, model):
    return save_bundle(model, tmp_path / "bundle", {"splits_sha256": "x" * 64})


@pytest.fixture
def tidy() -> pd.DataFrame:
    """SYNTHETIC: three experiments of 60 rows; flow drops by 3 units from row 40 in two of them."""
    rng = np.random.default_rng(0)
    frames = []
    for k, eid in enumerate(["valve1/0", "valve1/1", "other/1"]):
        flow = 32 + rng.normal(0, 0.4, 60)
        anomaly = np.zeros(60, dtype=int)
        if k < 2:
            flow[40:] -= 3.0
            anomaly[40:] = 1
        frames.append(pd.DataFrame({"experiment_id": eid, "family": eid.split("/")[0], "t": range(60),
                                    "flow_rate": flow, "anomaly": anomaly}))
    return pd.concat(frames, ignore_index=True).sample(frac=1.0, random_state=1)   # shuffled rows on purpose
