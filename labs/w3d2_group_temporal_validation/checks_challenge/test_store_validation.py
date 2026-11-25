"""Does the splitter estimate what the deployment question asks? SYNTHETIC panels, re-seeded here."""
from __future__ import annotations

import numpy as np
import pytest
from sklearn.neighbors import KNeighborsRegressor

from panel import LABEL_WEEKS, make_panel

CUTOFFS = [40, 60, 80]
HORIZON = 8


@pytest.fixture(scope="module", params=[11, 12])
def case(request, folds_fn):
    panel = make_panel(seed=request.param)
    try:
        folds = folds_fn(panel.copy(), CUTOFFS, horizon_weeks=HORIZON, label_weeks=LABEL_WEEKS)
    except NotImplementedError:
        pytest.fail("deployment_folds is not implemented yet", pytrace=False)
    return panel, folds


def test_one_fold_per_cutoff_with_row_positions(case):
    panel, folds = case
    assert [f["cutoff"] for f in folds] == CUTOFFS
    for f in folds:
        for key in ("train", "val_known", "val_new"):
            idx = np.asarray(f[key])
            assert idx.ndim == 1 and np.issubdtype(idx.dtype, np.integer), f"{key} must be integer row positions"
            assert len(set(idx.tolist())) == len(idx) and (len(idx) == 0 or (idx.min() >= 0 and idx.max() < len(panel)))
            assert np.array_equal(idx, np.sort(idx)), f"{key} must be sorted"
        assert len(f["train"]) and len(f["val_known"]) and len(f["val_new"]), "these cut-offs have all three kinds of rows"
        assert not set(f["train"]) & (set(f["val_known"]) | set(f["val_new"]))
        assert not set(f["val_known"]) & set(f["val_new"])


def test_training_uses_only_labels_fully_observed_at_the_cutoff(case):
    """A label at week t sums demand over t+1 .. t+4. It is known at the cut-off only if t + 4 <= c."""
    panel, folds = case
    for f in folds:
        train = panel.iloc[f["train"]]
        assert train["demand_next4"].notna().all()
        latest = int((train["week"] + LABEL_WEEKS).max())
        assert latest <= f["cutoff"], (
            f"cut-off {f['cutoff']}: a training label reaches week {latest}, which had not happened yet")


def test_training_keeps_everything_that_was_available(case):
    panel, folds = case
    for f in folds:
        available = panel[panel["demand_next4"].notna() & (panel["week"] + LABEL_WEEKS <= f["cutoff"])]
        assert len(f["train"]) == len(available), "the model is retrained on ALL history known at the cut-off"


def test_validation_is_the_use_period_that_follows_the_cutoff(case):
    panel, folds = case
    for f in folds:
        val = panel.iloc[np.r_[f["val_known"], f["val_new"]]]
        assert val["demand_next4"].notna().all()
        assert val["week"].min() > f["cutoff"] and val["week"].max() <= f["cutoff"] + HORIZON
        expected = panel[panel["demand_next4"].notna() & (panel["week"] > f["cutoff"])
                         & (panel["week"] <= f["cutoff"] + HORIZON)]
        assert len(val) == len(expected), "every store-week of the use period with a label is validated once"


def test_known_and_new_stores_are_separated_by_what_the_model_has_seen(case):
    panel, folds = case
    for f in folds:
        trained_stores = set(panel.iloc[f["train"]]["store_id"])
        assert set(panel.iloc[f["val_known"]]["store_id"]) <= trained_stores, "val_known contains an unseen store"
        leaked = set(panel.iloc[f["val_new"]]["store_id"]) & trained_stores
        assert not leaked, f"val_new contains stores the model was trained on: {sorted(leaked)[:5]}"


def _shock_copy_correlation(panel, folds) -> float:
    """Correlation, over the first three weeks after each cut-off, between the chain-wide level of the
    validation labels and the level of the training labels at the nearest training week."""
    log_label = np.log(panel["demand_next4"])
    resid = log_label - log_label.groupby(panel["store_id"]).transform("mean")      # removes the store level
    week = panel["week"]
    predicted, actual = [], []
    for f in folds:
        train_level = resid.iloc[f["train"]].groupby(week.iloc[f["train"]]).mean()
        val_level = resid.iloc[f["val_known"]].groupby(week.iloc[f["val_known"]]).mean()
        for w in range(f["cutoff"] + 1, f["cutoff"] + 4):
            if w in val_level.index:
                nearest = train_level.index[np.argmin(np.abs(train_level.index.to_numpy() - w))]
                predicted.append(train_level[nearest])
                actual.append(val_level[w])
    return float(np.corrcoef(predicted, actual)[0, 1])


@pytest.mark.parametrize("seed", [21, 22])
def test_planted_shock_leak_is_not_available_to_the_model(folds_fn, seed):
    """Chain-wide weekly shocks are independent from week to week (no season in this panel), so the
    level of the labels just after the cut-off cannot be predicted from training labels - unless a
    training label's 4-week window overlaps the validation labels. Correct split: correlation near 0.
    Training up to the cut-off itself: about 0.5."""
    panel = make_panel(seed=seed, n_weeks=156, season_amplitude=0.0)
    folds = folds_fn(panel.copy(), list(range(30, 140, 4)), horizon_weeks=HORIZON, label_weeks=LABEL_WEEKS)
    corr = _shock_copy_correlation(panel, folds)
    assert corr < 0.3, (
        f"the chain-wide level of the validation labels is predictable from the latest training labels "
        f"(correlation {corr:.2f}); training labels overlap the validation period")


def test_new_store_error_is_not_flattered_by_known_stores(case):
    """A model that memorises stores from their fingerprint is good on known stores and poor on new
    ones. If val_new contains known stores, its error is pulled towards the known-store error."""
    panel, folds = case
    X = panel[["fp_1", "fp_2", "fp_3"]].to_numpy()
    y = np.log(panel["demand_next4"]).to_numpy()
    mae_new, mae_known = [], []
    for f in folds:
        model = KNeighborsRegressor(n_neighbors=1).fit(X[f["train"]], y[f["train"]])
        mae_new.append(np.abs(model.predict(X[f["val_new"]]) - y[f["val_new"]]))
        mae_known.append(np.abs(model.predict(X[f["val_known"]]) - y[f["val_known"]]))
    mae_new, mae_known = float(np.concatenate(mae_new).mean()), float(np.concatenate(mae_known).mean())
    assert mae_new > 1.6 * mae_known, (
        f"error on 'new' stores ({mae_new:.3f}) is suspiciously close to the error on known stores "
        f"({mae_known:.3f}); with a store-memorising model it should be about twice as large or more")


def test_impossible_cutoff_is_rejected(folds_fn):
    panel = make_panel(seed=3)
    with pytest.raises(ValueError):
        folds_fn(panel, [2], horizon_weeks=HORIZON, label_weeks=LABEL_WEEKS)
    with pytest.raises(ValueError):
        folds_fn(panel, [500], horizon_weeks=HORIZON, label_weeks=LABEL_WEEKS)
