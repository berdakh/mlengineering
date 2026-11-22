"""A small convolutional autoencoder as an anomaly scorer (PyTorch, CPU).

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
    x = np.asarray(x, dtype=np.float32)
    if x.ndim != 2:
        raise ValueError(f"expected a 2-D array (rows, features), got shape {x.shape}")
    if window < 1:
        raise ValueError("window must be at least 1")
    padded = np.concatenate([np.repeat(x[:1], window - 1, axis=0), x], axis=0)
    index = np.arange(len(x))[:, None] + np.arange(window)[None, :]
    return padded[index]


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
    if len(train_x) == 0 or len(val_x) == 0:
        raise ValueError("need non-empty training and validation windows")
    train_x = np.ascontiguousarray(train_x, dtype=np.float32)
    val_x = np.ascontiguousarray(val_x, dtype=np.float32)
    generator = torch.Generator().manual_seed(seed)
    optimiser = torch.optim.Adam(model.parameters(), lr=lr)
    history: dict = {"train_loss": [], "val_loss": []}
    best_loss, best_state, best_epoch, since_best = float("inf"), None, -1, 0
    epoch = -1
    for epoch in range(max_epochs):
        model.train()
        order = torch.randperm(len(train_x), generator=generator).numpy()
        total = 0.0
        for start in range(0, len(order), batch_size):
            xb = torch.from_numpy(train_x[order[start:start + batch_size]])
            loss = ((model(xb) - xb) ** 2).mean()
            optimiser.zero_grad()
            loss.backward()
            optimiser.step()
            total += loss.item() * len(xb)
        history["train_loss"].append(total / len(train_x))
        val_loss = _mean_loss(model, val_x, batch_size)
        history["val_loss"].append(val_loss)
        if val_loss < best_loss:
            best_loss, best_epoch, since_best = val_loss, epoch, 0
            best_state = copy.deepcopy(model.state_dict())
        else:
            since_best += 1
            if since_best >= patience:
                break
    model.load_state_dict(best_state)
    history["best_epoch"] = best_epoch
    history["stopped_epoch"] = epoch
    return history


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
        usable = (tidy["t"].to_numpy() >= self.n_burn) & (tidy["anomaly"].to_numpy() == 0)
        parts = []
        for _, group in tidy.groupby("experiment_id", sort=False):
            idx = group.sort_values("t", kind="stable").index.to_numpy()
            windows = make_windows(feats[idx], self.window)
            parts.append(windows[usable[idx]])
        return np.concatenate(parts, axis=0)

    def _usable_rows(self, tidy: pd.DataFrame) -> np.ndarray:
        return (tidy["t"].to_numpy() >= self.n_burn) & (tidy["anomaly"].to_numpy() == 0)

    # -- contract
    def fit(self, train_tidy: pd.DataFrame, val_tidy: pd.DataFrame) -> "NeuralScorer":
        train_tidy = train_tidy.reset_index(drop=True)
        val_tidy = val_tidy.reset_index(drop=True)
        train_feats = self._features(train_tidy)
        self.normaliser_ = Normaliser().fit(train_feats[self._usable_rows(train_tidy)])
        train_x = self._training_windows(train_tidy, self.normaliser_)
        val_x = self._training_windows(val_tidy, self.normaliser_)
        self.model_ = ConvAutoencoder(len(_SENSORS), self.window, self.bottleneck, self.hidden)
        started = time.perf_counter()
        self.history_ = train_autoencoder(self.model_, train_x, val_x, seed=self.seed,
                                          max_epochs=self.max_epochs, patience=self.patience,
                                          batch_size=self.batch_size, lr=self.lr)
        self.train_seconds_ = time.perf_counter() - started
        self.n_train_windows_ = int(len(train_x))
        self.n_parameters_ = n_parameters(self.model_)
        return self

    def score(self, tidy: pd.DataFrame) -> np.ndarray:
        tidy = tidy.reset_index(drop=True)
        feats = self.normaliser_.transform(self._features(tidy))
        scores = np.empty(len(tidy), dtype=np.float64)
        self.model_.eval()
        with torch.no_grad():
            for _, group in tidy.groupby("experiment_id", sort=False):
                idx = group.sort_values("t", kind="stable").index.to_numpy()
                windows = torch.from_numpy(make_windows(feats[idx], self.window))
                errors = []
                for start in range(0, len(windows), 4096):
                    xb = windows[start:start + 4096]
                    errors.append(((self.model_(xb) - xb) ** 2).mean(dim=(1, 2)).numpy())
                scores[idx] = np.concatenate(errors)
        return scores
