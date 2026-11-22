"""Worked example for w4d3: one training run is a lottery ticket. SYNTHETIC data, PyTorch on CPU.

    python lessons/w4d3_neural_comparison/example/seed_lottery.py        # about 1 minute on 4 cores

A tiny MLP autoencoder is trained on windows of a SYNTHETIC 4-sensor signal with 10 different seeds
and evaluated on a test signal with injected faults. Nothing about the data or model changes between
runs; only the seed. The script then shows (1) the spread over seeds, (2) how optimistic "the best of
k seeds" is, (3) that the same seed reproduces exactly on CPU, and (4) how a causal and a centred
window react to a step - the reason the lab insists on causal windows.
Results are also written to example/seed_lottery.json for the figure script.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

try:
    import torch
    from torch import nn
except ImportError:                                                     # pragma: no cover
    raise SystemExit("PyTorch is not installed; see the lesson's set-up note.")

HERE = Path(__file__).resolve().parent
WINDOW = 16
torch.set_num_threads(1)


def signal(n: int, rng: np.random.Generator, faults: list[tuple[int, int]] = ()) -> tuple[np.ndarray, np.ndarray]:
    t = np.arange(n)
    x = np.stack([np.sin(2 * np.pi * t / 40), np.cos(2 * np.pi * t / 40),
                  np.sin(2 * np.pi * t / 13), 0.5 * np.sin(2 * np.pi * t / 40 + 1.0)], axis=1)
    x = x + 0.15 * rng.standard_normal(x.shape)
    y = np.zeros(n, dtype=int)
    for start, stop in faults:                                          # fault: sensor 3 decouples
        x[start:stop, 3] = 0.8 * rng.standard_normal(stop - start)
        y[start:stop] = 1
    return x.astype(np.float32), y


def windows(x: np.ndarray, centred: bool = False) -> np.ndarray:
    if centred:
        half = WINDOW // 2
        padded = np.concatenate([np.repeat(x[:1], half, 0), x, np.repeat(x[-1:], WINDOW - 1 - half, 0)])
    else:
        padded = np.concatenate([np.repeat(x[:1], WINDOW - 1, 0), x])
    return padded[np.arange(len(x))[:, None] + np.arange(WINDOW)[None, :]].reshape(len(x), -1)


def average_precision(y: np.ndarray, s: np.ndarray) -> float:
    order = np.argsort(-s, kind="stable")
    hits = y[order]
    precision = np.cumsum(hits) / np.arange(1, len(hits) + 1)
    return float((precision * hits).sum() / hits.sum())


def train(seed: int, x_train: np.ndarray, epochs: int = 15) -> nn.Module:
    torch.manual_seed(seed)
    model = nn.Sequential(nn.Linear(x_train.shape[1], 32), nn.ReLU(), nn.Linear(32, 3), nn.ReLU(),
                          nn.Linear(3, 32), nn.ReLU(), nn.Linear(32, x_train.shape[1]))
    optimiser = torch.optim.Adam(model.parameters(), lr=3e-3)
    data = torch.from_numpy(x_train)
    generator = torch.Generator().manual_seed(seed)
    for _ in range(epochs):
        for batch in torch.randperm(len(data), generator=generator).split(128):
            loss = ((model(data[batch]) - data[batch]) ** 2).mean()
            optimiser.zero_grad()
            loss.backward()
            optimiser.step()
    return model


def score(model: nn.Module, w: np.ndarray) -> np.ndarray:
    with torch.no_grad():
        x = torch.from_numpy(w)
        return ((model(x) - x) ** 2).mean(dim=1).numpy()


def main() -> None:
    rng = np.random.default_rng(0)
    x_train, _ = signal(3000, rng)
    x_test, y_test = signal(3000, rng, faults=[(500, 560), (1400, 1420), (2200, 2320)])
    w_train, w_test = windows(x_train), windows(x_test)

    print("1. Ten seeds, identical data and model; test average precision (SYNTHETIC)")
    aps = []
    for seed in range(10):
        aps.append(average_precision(y_test, score(train(seed, w_train), w_test)))
        print(f"   seed {seed}: {aps[-1]:.3f}")
    aps = np.array(aps)
    print(f"   mean {aps.mean():.3f}, sd {aps.std(ddof=1):.3f}, range [{aps.min():.3f}, {aps.max():.3f}]")

    print("\n2. 'Best of k seeds' as a reported number (expected value over 5000 random subsets)")
    best_of = {}
    for k in (1, 2, 3, 5, 10):
        draws = [aps[rng.choice(10, size=k, replace=False)].max() for _ in range(5000)]
        best_of[k] = float(np.mean(draws))
        optimism = round(best_of[k] - float(aps.mean()), 3) + 0.0
        print(f"   k = {k:>2}: {best_of[k]:.3f}  (optimism over the seed mean: {optimism:+.3f})")

    print("\n3. Same seed twice on CPU")
    a = score(train(3, w_train), w_test)
    b = score(train(3, w_train), w_test)
    print(f"   bitwise identical scores: {np.array_equal(a, b)}")

    print("\n4. Causal versus centred window: when does the score of a step change start to rise?")
    step = np.zeros((200, 4), dtype=np.float32)
    step[100:, :] = 1.0
    model = train(0, w_train)
    reaction = {}
    for name, centred in (("causal", False), ("centred", True)):
        s = score(model, windows(step, centred=centred))
        first = int(np.argmax(s > s[:40].mean() + 5 * s[:40].std() + 1e-6))
        reaction[name] = {"first_row_above_baseline": first, "scores": s[80:130].round(5).tolist()}
        print(f"   {name:>7} window: score first rises at row {first} (the step is at row 100)")

    (HERE / "seed_lottery.json").write_text(json.dumps(
        {"aps": aps.tolist(), "best_of_k": best_of, "same_seed_identical": bool(np.array_equal(a, b)),
         "step_reaction": reaction}, indent=2) + "\n")


if __name__ == "__main__":
    main()
