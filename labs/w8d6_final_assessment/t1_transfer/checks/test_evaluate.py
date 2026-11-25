"""t1: is the evaluation honest? (Checks grade the evaluation, not the model.)"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

from conftest import LEAKY, learner_view

CUTOFF = pd.Timestamp("2024-10-01")


def expected_split(df):
    served = pd.to_datetime(df["service_date"])
    return df[served < CUTOFF], df[served >= CUTOFF]


def called_rows(test, scores, fraction=0.10):
    frame = test.assign(_s=np.asarray(scores, float))
    parts = [g.sort_values("_s", ascending=False, kind="stable").head(math.ceil(fraction * len(g)))
             for _, g in frame.groupby(pd.to_datetime(frame["service_date"]))]
    return pd.concat(parts)


def reference_topk(test, scores):
    return called_rows(test, scores)["no_show"].mean()


# ------------------------------------------------------------------ declared features
def test_declared_features_exclude_columns_unknown_the_evening_before(mod):
    features = set(mod.FEATURES)
    assert features, "FEATURES is empty"
    for column in LEAKY:
        assert column not in features, f"{column!r} is not known on the evening before service"
    assert "no_show" not in features and "reservation_id" not in features


# ------------------------------------------------------------------ split
@pytest.mark.parametrize("which", ["shipped", "reseeded"])
def test_split_is_by_service_date(mod, which, request):
    df = learner_view(request.getfixturevalue(which))
    train, test = mod.split_train_test(df)
    served = pd.to_datetime(df["service_date"])
    assert set(test["reservation_id"]) == set(df.loc[served >= CUTOFF, "reservation_id"]), (
        "test = every reservation served from 2024-10-01, including those booked before it")
    assert set(train["reservation_id"]) == set(df.loc[served < CUTOFF, "reservation_id"]), (
        "train = every reservation served before 2024-10-01 (its outcome is known that evening)")


def test_split_respects_the_cutoff_argument(mod, shipped):
    train, test = mod.split_train_test(learner_view(shipped), "2024-07-01")
    assert pd.to_datetime(test["service_date"]).min() >= pd.Timestamp("2024-07-01")
    assert pd.to_datetime(train["service_date"]).max() < pd.Timestamp("2024-07-01")


# ------------------------------------------------------------------ metric
def tiny(dates, y):
    return pd.DataFrame({"service_date": pd.to_datetime(dates), "no_show": y})


def test_metric_ranks_within_each_day(mod):
    # day 1: 3 reservations, day 2: 3 reservations; fraction 0.1 -> one call per day
    test = tiny(["2024-10-01"] * 3 + ["2024-10-02"] * 3, [1, 0, 0, 0, 1, 0])
    assert mod.daily_topk_precision(test, [0.9, 0.5, 0.1, 0.2, 0.3, 0.25], fraction=0.1) == pytest.approx(1.0)
    assert mod.daily_topk_precision(test, [0.9, 0.95, 0.1, 0.2, 0.3, 0.25], fraction=0.1) == pytest.approx(0.5)


def test_metric_is_not_a_global_top_k(mod):
    # the highest scores are all on day 1; one call per day
    test = tiny(["2024-10-01", "2024-10-01", "2024-10-02", "2024-10-02"], [1, 1, 0, 0])
    assert mod.daily_topk_precision(test, [0.9, 0.8, 0.2, 0.1], fraction=0.25) == pytest.approx(0.5)


def test_metric_rounds_up_per_day(mod):
    # 11 reservations on one day at 10 % -> ceil(1.1) = 2 calls
    test = tiny(["2024-10-01"] * 11, [1, 0] + [0] * 9)
    scores = [0.9, 0.8] + [0.1] * 9
    assert mod.daily_topk_precision(test, scores, fraction=0.1) == pytest.approx(0.5)


def test_metric_agrees_with_reference_on_real_shape(mod, shipped):
    _, test = expected_split(shipped)
    scores = np.random.default_rng(0).random(len(test))
    assert mod.daily_topk_precision(test, scores) == pytest.approx(reference_topk(test, scores))


# ------------------------------------------------------------------ model scores
@pytest.fixture(scope="module")
def scored(mod, shipped):
    train, test = expected_split(shipped)
    scores = np.asarray(mod.fit_and_score(learner_view(train), learner_view(test)), dtype=float)
    return train, test, scores


def test_scores_have_one_finite_value_per_test_row(scored):
    _, test, scores = scored
    assert scores.shape == (len(test),) and np.isfinite(scores).all()


def test_scores_carry_real_signal(scored):
    _, test, scores = scored
    auc = roc_auc_score(test["no_show"], scores)
    assert auc > 0.62, f"test AUC {auc:.3f}: deposit, lead time and the guest's earlier visits are available"


@pytest.mark.parametrize("which", ["shipped", "reseeded"])
def test_scores_do_not_beat_the_generator(mod, which, request):
    """The generator's own no-show probability is the best possible ranking in expectation. A model
    that ranks clearly better has used information from after the evening before service."""
    table = request.getfixturevalue(which)
    train, test = expected_split(table)
    scores = mod.fit_and_score(learner_view(train), learner_view(test))
    auc, oracle = roc_auc_score(test["no_show"], scores), roc_auc_score(test["no_show"], test["p_true"])
    assert auc <= oracle + 0.01, (
        f"test AUC {auc:.3f} exceeds the generator's own probabilities ({oracle:.3f}). "
        "Some input encodes the outcome.")


def test_scores_ignore_columns_unknown_the_evening_before(mod, shipped):
    """Scramble every post-decision column in train and test. An honest pipeline does not notice."""
    train, test = expected_split(shipped)
    train, test = learner_view(train), learner_view(test)
    before = np.asarray(mod.fit_and_score(train.copy(), test.copy()), dtype=float)
    rng = np.random.default_rng(1)
    for frame in (train, test):
        for column in LEAKY:
            frame[column] = rng.permutation(frame[column].to_numpy())
    after = np.asarray(mod.fit_and_score(train, test), dtype=float)
    assert np.allclose(before, after, atol=1e-9), (
        "scores changed when " + " / ".join(LEAKY) + " were scrambled, so the pipeline reads at least one of them")


def test_scores_do_not_read_test_labels(mod, shipped):
    train, test = expected_split(shipped)
    train, test = learner_view(train), learner_view(test)
    before = np.asarray(mod.fit_and_score(train.copy(), test.copy()), dtype=float)
    test["no_show"] = 1 - test["no_show"]
    after = np.asarray(mod.fit_and_score(train.copy(), test), dtype=float)
    assert np.allclose(before, after, atol=1e-9)


# ------------------------------------------------------------------ the report dictionary
@pytest.fixture(scope="module")
def result(mod, shipped):
    return mod.run(learner_view(shipped))


def test_run_reports_sizes_and_prevalence(result, shipped):
    train, test = expected_split(shipped)
    assert result["n_test"] == len(test) and result["n_train"] == len(train)
    assert result["test_prevalence"] == pytest.approx(test["no_show"].mean(), abs=1e-9)


def test_run_reports_a_baseline_and_a_model_with_interval(result, shipped):
    _, test = expected_split(shipped)
    baseline, model = result["baseline"], result["model"]
    assert isinstance(baseline["name"], str) and baseline["name"]
    assert 0.0 <= baseline["topk_precision"] <= 1.0
    oracle = reference_topk(test, test["p_true"])
    assert model["topk_precision"] <= oracle + 0.08, "top-k precision far above what the generator allows"
    assert model["topk_precision"] > test["no_show"].mean() + 0.08, "barely better than calling at random"
    assert model["ci_low"] < model["topk_precision"] < model["ci_high"]
    assert 0.03 < model["ci_high"] - model["ci_low"] < 0.3, "about 260 calls cannot give a narrower or wider interval"


def test_run_reports_slices_of_the_called_reservations(result, shipped):
    _, test = expected_split(shipped)
    n_called = sum(math.ceil(0.1 * len(g)) for _, g in test.groupby(pd.to_datetime(test["service_date"])))
    slices = result["slices"]
    assert len(slices) >= 2
    total = 0
    for row in slices:
        assert {"slice", "n_picked", "precision"} <= set(row)
        total += row["n_picked"]
        if row["n_picked"] == 0:
            assert math.isnan(row["precision"]), "a slice with no calls has no precision"
        else:
            assert 0.0 <= row["precision"] <= 1.0
    assert total == n_called, f"slices should partition the {n_called} called reservations, got {total}"


def test_run_works_on_a_freshly_generated_table(mod, reseeded):
    result = mod.run(learner_view(reseeded))
    _, test = expected_split(reseeded)
    assert result["n_test"] == len(test)
    assert result["model"]["topk_precision"] <= reference_topk(test, test["p_true"]) + 0.08
