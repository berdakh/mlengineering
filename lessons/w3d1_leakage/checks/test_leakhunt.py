"""The leak hunt: grade the learner's honest evaluation on the shipped export and on a re-seeded one.

Ground truth comes from the generator: which rows are re-issues of which invoice, and a
"production" frame - later invoices exactly as a scoring service would see them at issue time.
All of it is SYNTHETIC.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score

SEEDS = [31, 2]              # 31 is the shipped file; 2 defeats hard-coded answers
LEAKS = ["reminders_sent", "customer_late_rate", "ledger_ref"]
CUTOFF = pd.Timestamp("2024-09-01")


@pytest.fixture(scope="module", params=SEEDS)
def world(request, generator, honest):
    export, production = generator.simulate(request.param)
    public = generator.public_view(export)
    result = honest.evaluate(public.copy())
    return {"export": export, "public": public, "production": generator.public_view(production),
            "result": result, "seed": request.param}


def test_result_contract(world):
    r = world["result"]
    for key in ("ap", "n_train", "n_test", "train_ids", "test_ids", "scores", "model"):
        assert key in r, f"evaluate() result lacks '{key}'"
    assert r["n_train"] == len(r["train_ids"]) and r["n_test"] == len(r["test_ids"])
    assert isinstance(r["scores"], pd.Series) and set(r["scores"].index) == set(r["test_ids"])
    assert 0.0 <= r["ap"] <= 1.0


def test_split_is_temporal(world):
    dates = world["public"].set_index("invoice_id")["issue_date"]
    r = world["result"]
    assert not set(r["train_ids"]) & set(r["test_ids"])
    assert dates.loc[r["train_ids"]].max() < CUTOFF, "training rows from the test period"
    assert dates.loc[r["test_ids"]].min() >= CUTOFF, "test rows from before the cut-off"
    assert r["n_test"] > 500 and r["n_train"] > 2000, "too many rows were discarded"


def test_reissued_invoices_are_counted_once(world):
    origin = world["export"].set_index("invoice_id")["origin_id"]
    r = world["result"]
    used = origin.loc[r["train_ids"] + r["test_ids"]]
    straddle = set(origin.loc[r["train_ids"]]) & set(origin.loc[r["test_ids"]])
    assert not straddle, f"{len(straddle)} invoices appear in training and again (re-issued) in the test period"
    assert not used.duplicated().any(), "a re-issued invoice is still counted twice on one side"
    assert used.nunique() >= 0.97 * origin.nunique(), "de-duplication removed real invoices"


@pytest.mark.parametrize("column", LEAKS)
def test_post_outcome_columns_have_no_influence(world, honest, column):
    """Scrambling a column that does not exist at issue time must not change anything."""
    scrambled = world["public"].copy()
    rng = np.random.default_rng(0)
    scrambled[column] = rng.permutation(scrambled[column].to_numpy())
    again = honest.evaluate(scrambled)
    assert again["ap"] == pytest.approx(world["result"]["ap"], abs=1e-9), f"the model reads '{column}'"


def test_preprocessing_is_fitted_on_training_rows_only(world, honest):
    """Corrupt some TEST rows. Scores of the other test rows must not move: nothing fitted may see test rows."""
    public = world["public"]
    r = world["result"]
    rng = np.random.default_rng(1)
    test_ids = np.array(sorted(r["test_ids"]))
    hit = set(rng.choice(test_ids, size=len(test_ids) // 3, replace=False))
    corrupted = public.copy()
    mask = corrupted["invoice_id"].isin(hit)
    for col in ("amount", "tenure_months", "n_prior_invoices"):
        corrupted[col] = corrupted[col].astype(float)
        corrupted.loc[mask, col] = corrupted.loc[mask, col] * 1000.0
    again = honest.evaluate(corrupted)
    untouched = [i for i in test_ids if i not in hit and i in again["scores"].index]
    assert len(untouched) > 300
    np.testing.assert_allclose(again["scores"].loc[untouched].to_numpy(), r["scores"].loc[untouched].to_numpy(),
                               atol=1e-9, err_msg="test rows influenced the fitted preprocessing or model")


def test_model_predicts_one_row_at_a_time(world):
    """A served model scores single invoices; a row's score cannot depend on its batch."""
    r = world["result"]
    batch = world["production"].head(40)
    together = np.asarray(r["model"].predict_proba(batch))[:, 1]
    alone = np.array([np.asarray(r["model"].predict_proba(batch.iloc[[i]]))[0, 1] for i in range(10)])
    np.testing.assert_allclose(alone, together[:10], atol=1e-9)


def test_reported_number_matches_production(world):
    """The point of the exercise: the estimate must predict performance on later invoices as the
    scoring service sees them (post-outcome columns empty, no knowledge of the future)."""
    r = world["result"]
    production = world["production"]
    scores = np.asarray(r["model"].predict_proba(production))[:, 1]
    production_ap = average_precision_score(production["paid_late"], scores)
    prevalence = production["paid_late"].mean()
    assert production_ap > prevalence + 0.04, (
        f"on production-like rows the model reaches AP {production_ap:.3f} at prevalence {prevalence:.3f}")
    assert abs(r["ap"] - production_ap) <= 0.08, (
        f"reported AP {r['ap']:.3f} but AP on production-like rows is {production_ap:.3f}")
