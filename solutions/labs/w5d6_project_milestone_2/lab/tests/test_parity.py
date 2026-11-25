"""Three paths, one answer: evaluation, batch inference and the API give identical scores."""
import numpy as np
from fastapi.testclient import TestClient

from flowguard.api import create_app
from flowguard.evaluation import experiment_scores
from flowguard.inference import api_requests_for, score_experiments


def test_three_way_parity(tidy, model, bundle_dir):
    batch = score_experiments(model, tidy).set_index(["experiment_id", "t"])["score"]
    evaluation = experiment_scores(model, tidy).set_index(["experiment_id", "t"])["score"]
    assert np.array_equal(batch.sort_index().to_numpy(), evaluation.sort_index().to_numpy())
    with TestClient(create_app(bundle_dir)) as client:
        for eid in sorted(tidy["experiment_id"].unique()):
            api = []
            for body in api_requests_for(model, tidy, eid, max_values=25):     # force chunking: 60 rows -> 3 requests
                api += client.post("/predict", json=body).json()["scores"]
            np.testing.assert_allclose(api, batch.loc[eid].sort_index().to_numpy(), rtol=0, atol=1e-12)


def test_burn_in_is_per_experiment(tidy, model):
    scored = score_experiments(model, tidy)
    first = scored.groupby("experiment_id").apply(lambda g: g.sort_values("t")["score"].iloc[:20].mean(),
                                                  include_groups=False)
    assert (first < 2.0).all()      # each experiment is normal relative to its own burn-in
