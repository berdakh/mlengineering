import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score, brier_score_loss

LABEL = "churned_30d"


# ---------------------------------------------------------------- probability tools
def test_brier_score_matches_definition(mod):
    rng = np.random.default_rng(0)
    for _ in range(20):
        y = rng.integers(0, 2, 200)
        p = rng.random(200)
        assert mod.brier_score(y, p) == pytest.approx(brier_score_loss(y, p))
    assert mod.brier_score([1, 0], [1.0, 0.0]) == pytest.approx(0.0)
    assert mod.brier_score([1, 0, 0, 0], [0.25] * 4) == pytest.approx(0.1875)


def test_reliability_table_partitions_the_rows(mod):
    rng = np.random.default_rng(1)
    p = rng.beta(1, 12, 5000)
    y = (rng.random(5000) < p).astype(int)                 # perfectly calibrated by construction
    table = mod.reliability_table(y, p, n_bins=10)
    assert {"n", "mean_predicted", "observed_rate"} <= set(table.columns)
    assert len(table) == 10 and int(table["n"].sum()) == 5000
    assert table["n"].min() >= 400, "bins must hold (about) equal numbers of rows"
    assert table["mean_predicted"].is_monotonic_increasing
    assert np.average(table["mean_predicted"], weights=table["n"]) == pytest.approx(p.mean())
    assert np.average(table["observed_rate"], weights=table["n"]) == pytest.approx(y.mean())
    assert np.abs(table["mean_predicted"] - table["observed_rate"]).max() < 0.05


# ---------------------------------------------------------------- decision rule
def test_offer_threshold_is_the_break_even_probability(mod):
    assert mod.offer_threshold([10.0], offer_cost=4.0, success_rate=0.25, months_retained=6)[0] == pytest.approx(4 / 15)
    t = mod.offer_threshold(np.array([9.99, 14.99, 19.99]), offer_cost=4.0, success_rate=0.25, months_retained=6)
    assert t[0] > t[1] > t[2], "a more valuable customer justifies the offer at a lower churn probability"
    half = mod.offer_threshold([10.0], offer_cost=4.0, success_rate=0.125, months_retained=6)[0]
    assert half == pytest.approx(8 / 15), "halving the success rate must double the break-even probability"
    cheap = mod.offer_threshold([10.0], offer_cost=2.0, success_rate=0.25, months_retained=6)[0]
    assert cheap == pytest.approx(2 / 15)


def test_policy_value_on_a_hand_example(mod):
    y = np.array([1, 0, 1, 0])
    price = np.array([10.0, 10.0, 20.0, 20.0])
    offered = np.array([True, True, False, False])
    value = mod.policy_value(y, offered, price, offer_cost=4.0, success_rate=0.25, months_retained=6)
    # row 0: 0.25 * 6 * 10 - 4 = 11 ; row 1: -4  -> 7 over 4 customers -> 1750 per 1,000
    assert value["net_value_per_1000"] == pytest.approx(1750.0)
    assert value["n_offered"] == 2 and value["offered_fraction"] == pytest.approx(0.5)
    assert value["churners_reached"] == pytest.approx(0.5)
    nobody = mod.policy_value(y, np.zeros(4, bool), price)
    assert nobody["net_value_per_1000"] == pytest.approx(0.0) and nobody["n_offered"] == 0


# ---------------------------------------------------------------- validation design
def test_validation_months_come_after_all_fit_months(mod, train):
    fit, validation = mod.temporal_fit_validation_split(train, n_validation_months=2)
    assert len(fit) + len(validation) == len(train) and len(fit) and len(validation)
    assert validation["snapshot_date"].nunique() == 2
    assert fit["snapshot_date"].max() < validation["snapshot_date"].min(), \
        "validation must be strictly later than every fitting row (the test months are later still)"


# ---------------------------------------------------------------- the probability model
def test_probabilities_are_valid_and_need_no_labels(mod, train, test):
    p = np.asarray(mod.churn_probabilities(train, test.drop(columns=[LABEL])))
    assert p.shape == (len(test),) and np.isfinite(p).all()
    assert p.min() >= 0.0 and p.max() <= 1.0
    np.testing.assert_allclose(p, mod.churn_probabilities(train, test.drop(columns=[LABEL])))


def test_probabilities_do_not_depend_on_the_rows_scored_together(mod, train, test):
    unlabeled = test.drop(columns=[LABEL])
    full = np.asarray(mod.churn_probabilities(train, unlabeled))
    part = np.asarray(mod.churn_probabilities(train, unlabeled.iloc[:50]))
    np.testing.assert_allclose(part, full[:50], rtol=1e-6, atol=1e-9)


def test_probabilities_are_calibrated_in_the_large_on_the_fitting_data(mod, train):
    """A cost threshold compares p with money. p must be a probability, not just a ranking score."""
    p = np.asarray(mod.churn_probabilities(train, train.drop(columns=[LABEL])))
    assert abs(p.mean() - train[LABEL].mean()) < 0.015, (
        f"mean predicted probability {p.mean():.3f} vs churn rate {train[LABEL].mean():.3f} on the rows "
        "the model was fitted on")


def test_model_beats_the_prevalence_forecast(mod, train, test):
    p = np.asarray(mod.churn_probabilities(train, test.drop(columns=[LABEL])))
    y = test[LABEL].to_numpy()
    assert average_precision_score(y, p) > 1.5 * y.mean()
    assert brier_score_loss(y, p) < brier_score_loss(y, np.full(len(y), train[LABEL].mean()))


# ---------------------------------------------------------------- the report
def test_report_is_consistent_with_the_functions(mod, report, train, test):
    assert {"validation", "test", "policies"} <= set(report)
    assert {"nobody", "everybody", "prevalence", "model"} <= set(report["policies"])
    y, price = test[LABEL].to_numpy(), test["monthly_price"].to_numpy()
    p = np.asarray(mod.churn_probabilities(train, test.drop(columns=[LABEL])))
    assert report["test"]["brier_model"] == pytest.approx(brier_score_loss(y, p), abs=1e-9)
    assert report["test"]["observed_rate"] == pytest.approx(y.mean())
    assert report["test"]["mean_predicted"] == pytest.approx(p.mean(), abs=1e-9)
    expected = mod.policy_value(y, p >= mod.offer_threshold(price), price)
    assert report["policies"]["model"]["net_value_per_1000"] == pytest.approx(expected["net_value_per_1000"])
    assert report["policies"]["nobody"]["net_value_per_1000"] == pytest.approx(0.0)
    everybody = (0.25 * 6 * price * y - 4.0).sum() / len(y) * 1000
    assert report["policies"]["everybody"]["net_value_per_1000"] == pytest.approx(everybody)


def test_validation_block_was_computed_without_the_validation_labels_in_the_fit(mod, report, train):
    fit, validation = mod.temporal_fit_validation_split(train)
    p = np.asarray(mod.churn_probabilities(fit, validation.drop(columns=[LABEL])))
    assert report["validation"]["brier_model"] == pytest.approx(brier_score_loss(validation[LABEL], p), abs=1e-9)
    assert report["validation"]["observed_rate"] == pytest.approx(validation[LABEL].mean())
