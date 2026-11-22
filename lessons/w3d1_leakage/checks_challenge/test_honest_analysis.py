"""An honest estimate says 'chance' on noise and agrees with fresh data when there is signal."""
from __future__ import annotations

import numpy as np
from sklearn.metrics import roc_auc_score


def test_contract(leads, analysis):
    X, y = leads.simulate(5, n_signal=6)
    result = analysis.honest_estimate(X, y, seed=0)
    assert set(result) >= {"auc", "model"}
    assert 0.0 <= float(result["auc"]) <= 1.0
    proba = np.asarray(result["model"].predict_proba(X.head(7)))
    assert proba.shape == (7, 2)
    again = analysis.honest_estimate(X, y, seed=0)
    assert float(again["auc"]) == float(result["auc"]), "same inputs and seed must give the same estimate"


def test_noise_is_reported_as_chance(noise_results):
    aucs = [float(r["auc"]) for r in noise_results]
    assert max(aucs) < 0.64, f"an AUC of {max(aucs):.3f} was reported for features that are pure noise"
    assert 0.42 <= float(np.mean(aucs)) <= 0.57, (
        f"mean reported AUC on pure noise is {np.mean(aucs):.3f}; the procedure manufactures skill")


def test_estimate_agrees_with_fresh_data(signal_results):
    gaps, fresh_aucs = [], []
    for result, X_new, y_new in signal_results:
        fresh = roc_auc_score(y_new, np.asarray(result["model"].predict_proba(X_new))[:, 1])
        fresh_aucs.append(fresh)
        gaps.append(float(result["auc"]) - fresh)
    assert float(np.mean(fresh_aucs)) > 0.57, f"the returned models barely beat chance on new leads: {fresh_aucs}"
    assert float(np.mean(gaps)) < 0.06, (
        f"estimates exceed performance on 20,000 new leads by {np.mean(gaps):.3f} on average")
    assert max(abs(g) for g in gaps) < 0.13, f"estimate far from fresh-data performance: {gaps}"
