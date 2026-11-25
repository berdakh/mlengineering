"""Challenge checks: contract, honest estimate, no identifiers, determinism, quality bar."""
from __future__ import annotations

import numpy as np
import pytest
from sklearn.metrics import average_precision_score


def test_contract(result):
    assert result["choice"] in ("iforest", "gbt")
    assert set(result["estimates"]) >= {"iforest", "gbt"}
    assert all(0.0 <= float(v) <= 1.0 for v in result["estimates"].values())
    assert hasattr(result["model"], "score")


def test_choice_follows_the_estimates(result):
    assert result["choice"] == max(("iforest", "gbt"), key=lambda k: result["estimates"][k])


def _test_ap(result, test):
    s = np.asarray(result["model"].score(test.drop(columns=["label"])), dtype=float)
    assert s.shape == (len(test),) and np.isfinite(s).all()
    return average_precision_score(test["label"].astype(int), s)


def test_reported_estimate_is_honest_on_new_customers(result, data):
    _, test = data
    truth = _test_ap(result, test)
    estimate = float(result["estimates"][result["choice"]])
    assert abs(estimate - truth) <= 0.12, (
        f"estimate {estimate:.3f} for '{result['choice']}' vs {truth:.3f} on new customers")


def test_scores_ignore_identifiers(result, data):
    train, test = data
    probe = test.drop(columns=["label"]).iloc[:3000]
    base = np.asarray(result["model"].score(probe), dtype=float)
    shuffled = probe.copy()
    rng = np.random.default_rng(0)
    # identifiers drawn from the TRAINING range, so a model that split on them would react
    shuffled["customer_id"] = rng.choice(train["customer_id"].to_numpy(), size=len(shuffled))
    shuffled["tx_id"] = rng.choice(train["tx_id"].to_numpy(), size=len(shuffled))
    np.testing.assert_allclose(np.asarray(result["model"].score(shuffled), dtype=float), base)


def test_run_is_deterministic(fraud, data, result):
    train, _ = data
    again = fraud.run(train.copy(), seed=0)
    assert again["choice"] == result["choice"]
    for k in ("iforest", "gbt"):
        assert float(again["estimates"][k]) == pytest.approx(float(result["estimates"][k]))


def test_quality_bar(result, data):
    _, test = data
    assert _test_ap(result, test) >= 0.2      # prevalence is about 0.03
