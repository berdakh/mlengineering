"""A small convolutional autoencoder as an anomaly scorer (PyTorch, CPU). LAB STARTER: complete the TODOs.

Same contract as every scorer in ``flowguard.baselines``, with one difference: ``fit`` takes a
training frame AND a validation frame, because early stopping needs data the weights never saw.

* ``fit(train_tidy, val_tidy)`` learns only from rows of those two frames that are past the per-
  experiment burn-in and labelled normal (``anomaly == 0``). The labels select training rows; the
  model never sees an anomalous row. Normalisation statistics come from the TRAINING rows only.
* ``score(tidy)`` returns one finite float per row, higher = more anomalous. The score of row ``t``
  depends only on rows ``<= t`` of the same experiment and on what ``fit`` learned.

Input representation, per experiment (causal):
  1. burn-in z: each sensor standardised with the mean/sd of the experiment's first ``n_burn`` rows
     (the same per-experiment calibration the classical baselines use; see w2d5/w2d6);
  2. clipped to [-clip, clip];
  3. standardised again with mean/sd fitted on the training rows (``Normaliser``);
  4. cut into causal windows: the window for row t holds rows t-window+1 .. t.
The score of a row is the mean squared reconstruction error of its window.
"""
from __future__ import annotations

import copy
import time

import numpy as np
import pandas as pd
import torch
from torch import nn

from flowguard.data import SENSOR_COLUMNS

_SENSORS = list(SENSOR_COLUMNS)


# ----------------------------------------------------------------------------- representation
def burn_in_z(tidy: pd.DataFrame, n_burn: int) -> np.ndarray:
    """(n_rows, n_sensors) z-scores, each experiment standardised by its own first ``n_burn`` rows.

    Given (not part of the exercise). Rows are returned in the order of ``tidy``.
    """
    tidy = tidy.reset_index(drop=True)
    out = np.empty((len(tidy), len(_SENSORS)), dtype=np.float64)
    for _, group in tidy.groupby("experiment_id", sort=False):
        group = group.sort_values("t", kind="stable")
        if len(group) <= n_burn:
            raise ValueError(f"experiment {group['experiment_id'].iloc[0]!r} has only {len(group)} rows")
        x = group[_SENSORS].to_numpy(dtype=np.float64)
        mean = x[:n_burn].mean(axis=0)
        std = x[:n_burn].std(axis=0)
        out[group.index.to_numpy()] = (x - mean) / np.where(std > 0, std, 1.0)
    return out


def make_windows(x: np.ndarray, window: int) -> np.ndarray:
    """(n, f) -> (n, window, f) float32. Row i holds x[i-window+1 .. i] (past and present only).

    Before the first row there is no past; those positions repeat x[0] ("edge padding").
    """
    # TODO Task 1. Validate the input (2-D, window >= 1), then build the windows.
    # Hint: pad the front with window-1 copies of x[0]; fancy indexing avoids a Python loop.
    raise NotImplementedError("make_windows")

class Normaliser:
    """Per-feature mean/sd learned once in ``fit``; ``transform`` never updates them."""

    def fit(self, x: np.ndarray) -> "Normaliser":
        x = np.asarray(x, dtype=np.float64)
        self.mean_ = x.mean(axis=0)
        std = x.std(axis=0)
        self.std_ = np.where(std > 0, std, 1.0)
        return self

    def transform(self, x: np.ndarray) -> np.ndarray:
        return (np.asarray(x, dtype=np.float64) - self.mean_) / self.std_


# ----------------------------------------------------------------------------- model
class ConvAutoencoder(nn.Module):
    """1-D convolutional autoencoder over a window. Input and output: (batch, window, features).

    Given (not part of the exercise). ``window`` must be divisible by 4.
    """

    def __init__(self, n_features: int, window: int, bottleneck: int = 4, hidden: int = 16):
        super().__init__()
        if window % 4:
            raise ValueError("window must be divisible by 4")
        self.encoder = nn.Sequential(
            nn.Conv1d(n_features, hidden, kernel_size=5, padding=2), nn.ReLU(),
            nn.Conv1d(hidden, hidden, kernel_size=4, stride=2, padding=1), nn.ReLU(),
            nn.Conv1d(hidden, bottleneck, kernel_size=4, stride=2, padding=1), nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose1d(bottleneck, hidden, kernel_size=4, stride=2, padding=1), nn.ReLU(),
            nn.ConvTranspose1d(hidden, hidden, kernel_size=4, stride=2, padding=1), nn.ReLU(),
            nn.Conv1d(hidden, n_features, kernel_size=5, padding=2),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        z = self.encoder(x.transpose(1, 2))
        return self.decoder(z).transpose(1, 2)


def n_parameters(model: nn.Module) -> int:
    return int(sum(p.numel() for p in model.parameters()))


# ----------------------------------------------------------------------------- training
def _mean_loss(model: nn.Module, x: np.ndarray, batch_size: int) -> float:
    model.eval()
    total, n = 0.0, 0
    with torch.no_grad():
        for start in range(0, len(x), batch_size):
            xb = torch.from_numpy(x[start:start + batch_size])
            total += float(((model(xb) - xb) ** 2).mean(dim=(1, 2)).sum())
            n += len(xb)
    return total / max(n, 1)


def train_autoencoder(model: nn.Module, train_x: np.ndarray, val_x: np.ndarray, *, seed: int,
                      max_epochs: int = 30, patience: int = 4, batch_size: int = 256,
                      lr: float = 1e-3) -> dict:
    """Train ``model`` to reconstruct ``train_x``; early-stop on the reconstruction loss of ``val_x``.

    On return the model holds the weights of the epoch with the LOWEST validation loss.
    Returns ``{"train_loss": [...], "val_loss": [...], "best_epoch": int, "stopped_epoch": int}``;
    epochs are counted from 0 and ``val_loss[best_epoch] == min(val_loss)``.
    The shuffling order is drawn from a generator seeded with ``seed``; seed the weights before
    building ``model`` (``NeuralScorer`` does both).
    """
    # TODO Task 2. Shuffle with torch.randperm(..., generator=torch.Generator().manual_seed(seed)),
    # train with Adam on the mean squared reconstruction error, compute the validation loss after every
    # epoch with _mean_loss, keep a copy of the best state_dict, stop after `patience` epochs without
    # improvement, restore the best weights, and return the documented history dict.
    raise NotImplementedError("train_autoencoder")

# ----------------------------------------------------------------------------- scorer
class NeuralScorer:
    """Autoencoder anomaly scorer with the fit/score contract described in the module docstring."""

    def __init__(self, window: int = 32, bottleneck: int = 4, hidden: int = 16, n_burn: int = 100,
                 clip: float = 10.0, seed: int = 0, max_epochs: int = 30, patience: int = 4,
                 batch_size: int = 256, lr: float = 1e-3):
        self.window, self.bottleneck, self.hidden = window, bottleneck, hidden
        self.n_burn, self.clip, self.seed = n_burn, clip, seed
        self.max_epochs, self.patience, self.batch_size, self.lr = max_epochs, patience, batch_size, lr

    # -- helpers
    def _features(self, tidy: pd.DataFrame) -> np.ndarray:
        return np.clip(burn_in_z(tidy, self.n_burn), -self.clip, self.clip)

    def _training_windows(self, tidy: pd.DataFrame, normaliser: Normaliser) -> np.ndarray:
        """Windows ending at usable rows (past burn-in, labelled normal), built per experiment."""
        tidy = tidy.reset_index(drop=True)
        feats = normaliser.transform(self._features(tidy))
        usable = self._usable_rows(tidy)
        parts = []
        for _, group in tidy.groupby("experiment_id", sort=False):
            idx = group.sort_values("t", kind="stable").index.to_numpy()
            windows = make_windows(feats[idx], self.window)
            parts.append(windows[usable[idx]])
        return np.concatenate(parts, axis=0)

    def _usable_rows(self, tidy: pd.DataFrame) -> np.ndarray:
        """Boolean mask of rows the model may learn from (use it in _training_windows too)."""
        raise NotImplementedError("Task 3: rows past the burn-in AND labelled normal")

    # -- contract
    def fit(self, train_tidy: pd.DataFrame, val_tidy: pd.DataFrame) -> "NeuralScorer":
        # TODO Task 3. (a) features of the training frame -> fit self.normaliser_ on its USABLE rows only;
        # (b) training and validation windows via self._training_windows;
        # (c) torch.manual_seed(self.seed) BEFORE building ConvAutoencoder, then train_autoencoder;
        # (d) set history_, train_seconds_, n_train_windows_, n_parameters_.
        raise NotImplementedError("NeuralScorer.fit")

    def score(self, tidy: pd.DataFrame) -> np.ndarray:
        # TODO Task 4. Per experiment (sorted by t): features -> self.normaliser_.transform -> make_windows
        # -> model in eval mode under torch.no_grad() -> mean squared error per window. Return scores in
        # the row order of `tidy`.
        raise NotImplementedError("NeuralScorer.score")
