"""Behavioural checks for flowguard.neural. SYNTHETIC data; tiny models; under ~30 s on a laptop CPU."""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import torch
from torch import nn

from conftest import small, synthetic_experiment  # noqa: F401


# ------------------------------------------------------------------ make_windows
def test_windows_shape_and_dtype(neural):
    x = np.arange(30, dtype=float).reshape(10, 3)
    w = neural.make_windows(x, 4)
    assert w.shape == (10, 4, 3), "expected (rows, window, features)"
    assert w.dtype == np.float32


def test_window_for_row_t_ends_at_row_t(neural):
    x = np.arange(20, dtype=float).reshape(10, 2)
    w = neural.make_windows(x, 4)
    np.testing.assert_array_equal(w[6], x[3:7], err_msg="window i must hold rows i-window+1 .. i")
    np.testing.assert_array_equal(w[9][-1], x[9], err_msg="the last position of window i is row i itself")


def test_first_rows_are_edge_padded(neural):
    x = np.arange(20, dtype=float).reshape(10, 2)
    w = neural.make_windows(x, 4)
    np.testing.assert_array_equal(w[0], np.repeat(x[:1], 4, axis=0))
    np.testing.assert_array_equal(w[1], np.vstack([x[0], x[0], x[0], x[1]]))


def test_windows_never_contain_future_rows(neural):
    rng = np.random.default_rng(0)
    x = rng.normal(size=(50, 3))
    changed = x.copy()
    changed[31:] += 100.0
    np.testing.assert_array_equal(neural.make_windows(x, 8)[:31], neural.make_windows(changed, 8)[:31],
                                  err_msg="windows up to row 30 changed when rows after 30 changed: look-ahead")


# ------------------------------------------------------------------ model
def test_autoencoder_reconstructs_input_shape(neural):
    model = neural.ConvAutoencoder(n_features=8, window=16, bottleneck=2, hidden=8)
    x = torch.zeros(5, 16, 8)
    assert model(x).shape == x.shape


# ------------------------------------------------------------------ training loop
class Constant(nn.Module):
    """Outputs one learnable constant b everywhere. With training data = 1.0 and validation data = 0.2,
    the validation loss (b - 0.2)^2 falls while b < 0.2 and rises after: its minimum is mid-training."""

    def __init__(self):
        super().__init__()
        self.b = nn.Parameter(torch.zeros(1))

    def forward(self, x):
        return torch.zeros_like(x) + self.b


def test_training_returns_history_with_documented_keys(neural):
    history = neural.train_autoencoder(Constant(), np.ones((32, 4, 2), np.float32),
                                       np.full((8, 4, 2), 0.2, np.float32), seed=0, max_epochs=5, patience=10,
                                       batch_size=32, lr=0.05)
    assert {"train_loss", "val_loss", "best_epoch", "stopped_epoch"} <= set(history)
    assert len(history["train_loss"]) == len(history["val_loss"]) == history["stopped_epoch"] + 1


def test_training_reduces_the_training_loss(neural, frames):
    train, val, _ = frames
    scorer = small(neural, max_epochs=8, patience=8).fit(train, val)
    losses = scorer.history_["train_loss"]
    assert losses[-1] < 0.7 * losses[0], f"training loss barely moved: {losses[0]:.4f} -> {losses[-1]:.4f}"


@pytest.mark.parametrize("patience", [3, 100])
def test_early_stopping_restores_the_best_validation_epoch(neural, patience):
    model = Constant()
    history = neural.train_autoencoder(model, np.ones((32, 4, 2), np.float32),
                                       np.full((8, 4, 2), 0.2, np.float32), seed=0, max_epochs=40,
                                       patience=patience, batch_size=32, lr=0.05)
    best = int(np.argmin(history["val_loss"]))
    assert history["best_epoch"] == best, "best_epoch must be the epoch with the lowest validation loss"
    assert history["stopped_epoch"] > best, "this setup is built so validation loss rises after its minimum"
    returned_val_loss = float(((model.b.detach() - 0.2) ** 2).item())
    assert returned_val_loss == pytest.approx(min(history["val_loss"]), rel=1e-4, abs=1e-7), (
        "the returned model must hold the weights of the best validation epoch, not the last epoch")


# ------------------------------------------------------------------ what fit may learn from
def test_normaliser_is_fitted_on_training_rows_only(neural, frames):
    train, val, _ = frames
    shifted_val = val.copy()
    shifted_val.loc[shifted_val["t"] >= 50, synthetic_cols(val)] += 50.0   # after burn-in only
    a = small(neural, max_epochs=1).fit(train, val)
    b = small(neural, max_epochs=1).fit(train, shifted_val)
    np.testing.assert_allclose(a.normaliser_.mean_, b.normaliser_.mean_, err_msg=(
        "normalisation statistics changed when only the VALIDATION frame changed: fit them on training rows"))
    np.testing.assert_allclose(a.normaliser_.std_, b.normaliser_.std_)


def test_anomalous_training_rows_are_never_learned_from(neural):
    clean = pd.concat([synthetic_experiment(f"valve1/{i}", seed=i) for i in range(3)], ignore_index=True)
    poisoned = pd.concat([synthetic_experiment(f"valve1/{i}", seed=i, shift_from=200 if i == 0 else None,
                                               anomaly_value=1e6) for i in range(3)], ignore_index=True)
    poisoned.loc[poisoned["anomaly"] == 0, synthetic_cols(poisoned)] = clean.loc[poisoned["anomaly"] == 0,
                                                                                synthetic_cols(clean)].to_numpy()
    val = synthetic_experiment("valve1/9", seed=9)
    a = small(neural, max_epochs=1).fit(clean[poisoned["anomaly"] == 0], val)
    b = small(neural, max_epochs=1).fit(poisoned, val)
    np.testing.assert_allclose(a.normaliser_.mean_, b.normaliser_.mean_, rtol=1e-9, err_msg=(
        "rows labelled anomalous (value 1e6 here) influenced the fitted model: train on normal rows only"))
    assert b.n_train_windows_ == a.n_train_windows_


def synthetic_cols(frame):
    return [c for c in frame.columns if c not in ("experiment_id", "family", "t", "datetime", "anomaly", "changepoint")]


# ------------------------------------------------------------------ scoring contract
def test_scores_are_finite_one_per_row_and_detect_a_shift(neural, frames):
    train, val, test = frames
    scorer = small(neural, max_epochs=8, patience=8).fit(train, val)
    s = scorer.score(test)
    assert s.shape == (len(test),) and np.isfinite(s).all()
    before = s[(test["t"] >= 60) & (test["t"] < 180)]
    after = s[test["t"] >= 190]
    assert np.median(after) > 3 * np.median(before), "a large level shift should raise the reconstruction error"


def test_score_is_causal(neural, frames):
    train, val, test = frames
    scorer = small(neural).fit(train, val)
    changed = test.copy()
    changed.loc[changed["t"] > 120, synthetic_cols(test)] *= 3.0
    np.testing.assert_allclose(scorer.score(test)[:121], scorer.score(changed)[:121], rtol=0, atol=1e-6,
                               err_msg="scores up to row 120 changed when only later rows changed: look-ahead")


def test_experiments_are_scored_independently(neural, frames):
    train, val, test = frames
    scorer = small(neural).fit(train, val)
    other = synthetic_experiment("other/3", seed=33, shift_from=100)
    together = scorer.score(pd.concat([other, test], ignore_index=True))[len(other):]
    np.testing.assert_allclose(together, scorer.score(test), rtol=0, atol=1e-6,
                               err_msg="a window crossed an experiment boundary, or scoring depends on other rows")


def test_same_seed_same_model_different_seed_different_model(neural, frames):
    train, val, test = frames
    a = small(neural, seed=0).fit(train, val).score(test)
    b = small(neural, seed=0).fit(train, val).score(test)
    c = small(neural, seed=1).fit(train, val).score(test)
    np.testing.assert_array_equal(a, b, err_msg="same seed, same data, same CPU: scores must be identical")
    assert not np.allclose(a, c), "a different seed should give a different model"
