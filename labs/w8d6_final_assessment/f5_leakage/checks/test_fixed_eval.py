"""Checks for f5. The evaluation is re-run here from the submitted parts (FEATURES, make_split,
build_model), so the grade does not rely on a self-reported number. Any model family and any
temporal cut-off satisfying the README are accepted."""
import numpy as np
import pandas as pd
import pytest
from sklearn.metrics import average_precision_score

LABEL = "lapsed_30d"


@pytest.fixture(scope="module")
def rerun(sub, df, split):
    train_idx, test_idx = split
    train, test = df.iloc[train_idx], df.iloc[test_idx]
    model = sub.build_model().fit(train[list(sub.FEATURES)], train[LABEL])
    prob = np.asarray(model.predict_proba(test[list(sub.FEATURES)]))[:, 1]
    return test[LABEL].to_numpy(), prob


# ------------------------------------------------------------------ features
def test_features_exist_and_exclude_label_and_identifier(sub, df):
    feats = list(sub.FEATURES)
    assert feats, "FEATURES is empty"
    assert set(feats) <= set(df.columns)
    assert LABEL not in feats
    assert "account_id" not in feats, "an identifier is not a feature"


def test_features_are_available_at_prediction_time(sub):
    """Columns written after the snapshot date cannot be model inputs.
    (Which columns those are is for you to establish from data/README.md and the data.)"""
    not_available = {"winback_call_logged", "last_pickup_offset_days"}
    used = not_available & set(sub.FEATURES)
    assert not used, f"{len(used)} feature(s) are not known on the snapshot date"


# ------------------------------------------------------------------ split
def test_split_is_a_partition_of_row_positions(df, split):
    train_idx, test_idx = split
    assert len(np.intersect1d(train_idx, test_idx)) == 0, "a row is in both train and test"
    assert train_idx.min() >= 0 and max(train_idx.max(), test_idx.max()) < len(df)
    assert len(train_idx) >= 0.5 * len(df), "train must keep at least half of the rows"
    assert len(test_idx) >= 0.1 * len(df), "test must hold at least 10% of the rows"


def test_split_is_forward_in_time(df, split):
    train_idx, test_idx = split
    dates = pd.to_datetime(df["snapshot_date"])
    assert dates.iloc[train_idx].max() < dates.iloc[test_idx].min(), (
        "every training snapshot must precede every test snapshot: the model will be used on "
        "months that come after everything it was trained on")


# ------------------------------------------------------------------ model
def test_model_accepts_raw_features(rerun):
    """build_model() must contain its own preprocessing: it is fitted on raw training rows here."""
    y, prob = rerun
    assert prob.shape == y.shape and np.isfinite(prob).all()


def test_build_model_returns_unfitted_fresh_estimators(sub):
    assert sub.build_model() is not sub.build_model()


# ------------------------------------------------------------------ result
def test_score_is_plausible_for_an_honest_evaluation(rerun):
    y, prob = rerun
    ap = average_precision_score(y, prob)
    assert ap > 1.2 * y.mean(), f"AP {ap:.3f} is at the no-skill level ({y.mean():.3f})"
    assert ap < 0.40, (f"AP {ap:.3f} is far above what the legitimately available features support "
                       "on this data; something still leaks")


def test_reported_numbers_match_a_rerun(sub, df, rerun, split):
    y, prob = rerun
    report = sub.evaluate(df.copy())
    assert report["ap"] == pytest.approx(average_precision_score(y, prob), abs=0.02)
    assert report["n_train"] == len(split[0]) and report["n_test"] == len(split[1])
    assert report["test_prevalence"] == pytest.approx(y.mean())
