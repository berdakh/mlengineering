"""Transfer exercise part 2: is the evaluation honest? (Checks grade the evaluation, not the model.)"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import roc_auc_score

from conftest import LEAKY, learner_view

CUTOFF = pd.Timestamp("2024-10-01")


def expected_split(df):
    test = df[df["issue_date"] >= CUTOFF]
    train = df[(df["due_date"] + pd.Timedelta(days=30) < CUTOFF) & (df["issue_date"] < CUTOFF)]
    return train, test


def reference_topk(test, scores, k=15):
    frame = test.assign(s=np.asarray(scores, float), w=(test["issue_date"] - CUTOFF).dt.days // 7)
    return frame.sort_values("s", ascending=False, kind="stable").groupby("w").head(k)["late"].mean()


# ------------------------------------------------------------------ declared features
def test_declared_features_exclude_columns_unknown_at_issue_time(mod):
    features = set(mod.FEATURES)
    assert features, "FEATURES is empty"
    for column in LEAKY:
        assert column not in features, f"{column!r} is not known when the invoice is issued"
    assert "late" not in features and "invoice_id" not in features


# ------------------------------------------------------------------ split
@pytest.mark.parametrize("which", ["shipped", "reseeded"])
def test_split_is_temporal(mod, which, request):
    df = learner_view(request.getfixturevalue(which))
    train, test = mod.split_train_test(df)
    assert len(train) and len(test)
    assert test["issue_date"].min() >= CUTOFF
    assert set(test["invoice_id"]) == set(df.loc[df["issue_date"] >= CUTOFF, "invoice_id"])
    assert train["issue_date"].max() < CUTOFF, "training invoices must be issued before the test period"
    assert not set(train["invoice_id"]) & set(test["invoice_id"])


def test_training_labels_were_known_before_the_test_period(mod, shipped):
    train, _ = mod.split_train_test(learner_view(shipped))
    known_on = train["due_date"] + pd.Timedelta(days=30)
    late_known = int((known_on >= CUTOFF).sum())
    assert late_known == 0, (
        f"{late_known} training invoices have a `late` label that was not yet decided on 2024-10-01 "
        "(late = unpaid 30 days after the due date). At deployment those labels do not exist.")
    expected, _ = expected_split(shipped)
    assert len(train) >= 0.95 * len(expected), "too many usable training invoices were discarded"


def test_split_respects_the_cutoff_argument(mod, shipped):
    train, test = mod.split_train_test(learner_view(shipped), "2024-07-01")
    assert test["issue_date"].min() >= pd.Timestamp("2024-07-01")
    assert (train["due_date"] + pd.Timedelta(days=30)).max() < pd.Timestamp("2024-07-01")


# ------------------------------------------------------------------ metric
def tiny(dates, late):
    return pd.DataFrame({"issue_date": pd.to_datetime(dates), "late": late})


def test_metric_ranks_within_each_week(mod):
    # week 0: three invoices, week 1: three invoices; k = 1 -> one call per week
    test = tiny(["2024-10-01", "2024-10-03", "2024-10-07", "2024-10-08", "2024-10-09", "2024-10-14"],
                [1, 0, 0, 0, 1, 0])
    scores = [0.9, 0.8, 0.1, 0.2, 0.3, 0.25]      # week 0 best is late; week 1 best (0.3) is late
    assert mod.weekly_topk_precision(test, scores, k=1) == pytest.approx(1.0)
    globally_top = [0.9, 0.95, 0.1, 0.2, 0.3, 0.25]   # week 0 best is now on time
    assert mod.weekly_topk_precision(test, globally_top, k=1) == pytest.approx(0.5)


def test_metric_is_not_a_global_top_k(mod):
    # All the highest scores are in week 0. A global top-2 would take two week-0 invoices (both late);
    # the team calls one per week, and week 1's best invoice is on time.
    test = tiny(["2024-10-01", "2024-10-02", "2024-10-08", "2024-10-09"], [1, 1, 0, 0])
    assert mod.weekly_topk_precision(test, [0.9, 0.8, 0.2, 0.1], k=1) == pytest.approx(0.5)


def test_metric_takes_all_invoices_of_a_short_week(mod):
    test = tiny(["2024-10-01", "2024-10-02", "2024-10-08"], [1, 0, 1])
    assert mod.weekly_topk_precision(test, [0.5, 0.4, 0.1], k=2) == pytest.approx(2 / 3)


def test_metric_agrees_with_reference_on_real_shape(mod, shipped):
    _, test = expected_split(shipped)
    rng = np.random.default_rng(0)
    scores = rng.random(len(test))
    assert mod.weekly_topk_precision(test, scores, k=15) == pytest.approx(reference_topk(test, scores))


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
    auc = roc_auc_score(test["late"], scores)
    assert auc > 0.70, f"test AUC {auc:.3f}: the customer's resolved payment history is available at issue time"


@pytest.mark.parametrize("which", ["shipped", "reseeded"])
def test_scores_do_not_beat_the_generator(mod, which, request):
    """The generator's own late-probability is the best possible ranking in expectation. A model that
    ranks clearly better than it has used information from after the invoice was issued."""
    table = request.getfixturevalue(which)
    train, test = expected_split(table)
    scores = mod.fit_and_score(learner_view(train), learner_view(test))
    auc, oracle = roc_auc_score(test["late"], scores), roc_auc_score(test["late"], test["p_true"])
    assert auc <= oracle + 0.01, (
        f"test AUC {auc:.3f} exceeds the generator's own probabilities ({oracle:.3f}). "
        "Some input encodes the outcome.")


def test_scores_ignore_columns_unknown_at_issue_time(mod, shipped):
    """Scramble every post-issue column in train and test. An honest pipeline does not notice."""
    train, test = expected_split(shipped)
    train, test = learner_view(train), learner_view(test)
    before = np.asarray(mod.fit_and_score(train.copy(), test.copy()), dtype=float)
    rng = np.random.default_rng(1)
    for frame in (train, test):
        frame["days_to_payment"] = rng.permutation(frame["days_to_payment"].to_numpy())
        frame["reminders_sent"] = rng.permutation(frame["reminders_sent"].to_numpy())
        frame["customer_late_rate"] = rng.permutation(frame["customer_late_rate"].to_numpy())
        frame["account_status"] = rng.permutation(frame["account_status"].to_numpy())
    after = np.asarray(mod.fit_and_score(train, test), dtype=float)
    assert np.allclose(before, after, atol=1e-9), (
        "scores changed when days_to_payment / reminders_sent / customer_late_rate / account_status "
        "were scrambled, so the pipeline reads at least one of them")


def test_scores_do_not_read_test_labels(mod, shipped):
    train, test = expected_split(shipped)
    train, test = learner_view(train), learner_view(test)
    before = np.asarray(mod.fit_and_score(train.copy(), test.copy()), dtype=float)
    test["late"] = 1 - test["late"]
    after = np.asarray(mod.fit_and_score(train.copy(), test), dtype=float)
    assert np.allclose(before, after, atol=1e-9)


# ------------------------------------------------------------------ the report dictionary
@pytest.fixture(scope="module")
def result(mod, shipped):
    return mod.run(learner_view(shipped))


def test_run_reports_sizes_and_prevalence(result, shipped):
    train, test = expected_split(shipped)
    assert result["n_test"] == len(test)
    assert 0.95 * len(train) <= result["n_train"] <= len(train)
    assert result["test_prevalence"] == pytest.approx(test["late"].mean(), abs=1e-9)


def test_run_reports_a_baseline_and_a_model_with_interval(result, shipped):
    _, test = expected_split(shipped)
    baseline, model = result["baseline"], result["model"]
    assert isinstance(baseline["name"], str) and baseline["name"]
    assert 0.0 <= baseline["topk_precision"] <= 1.0
    oracle = reference_topk(test, test["p_true"])
    assert model["topk_precision"] <= oracle + 0.08, "top-k precision far above what the generator allows"
    assert model["topk_precision"] > test["late"].mean() + 0.2, "barely better than calling at random"
    assert model["ci_low"] < model["topk_precision"] < model["ci_high"]
    assert 0.03 < model["ci_high"] - model["ci_low"] < 0.4, "about 200 calls cannot give a narrower or wider interval"


def test_run_reports_slices_with_sizes(result):
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
    assert 150 <= total <= 15 * 14, "slices should partition the invoices that were called"


def test_run_works_on_a_freshly_generated_table(mod, reseeded):
    result = mod.run(learner_view(reseeded))
    train, test = expected_split(reseeded)
    assert result["n_test"] == len(test)
    assert result["model"]["topk_precision"] <= reference_topk(test, test["p_true"]) + 0.08
