"""Worked example: what "point-adjust" does to a detector that knows nothing. REAL SKAB data.

    python project/get_skab.py                                                    # once
    python lessons/w3d4_point_vs_event_evaluation/example/point_adjust_random.py

The "detector" flags each row independently with probability q. It never looks at a sensor, so
there is nothing to fit and no split is needed: all 34 labelled experiments are scored.
Point-adjust (PA): if any row of a true event is flagged, count the whole event as flagged.

Expected value under PA for an event of L rows:  P(event counted) = 1 - (1 - q)^L.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = next(p for p in Path(__file__).resolve().parents if (p / "project" / "get_skab.py").is_file())
RAW = REPO_ROOT / "data" / "raw" / "skab"


def load_labels() -> list[np.ndarray]:
    files = sorted(p for fam in ("valve1", "valve2", "other") for p in (RAW / fam).glob("*.csv"))
    if not files:
        sys.exit("no SKAB files found. Run `python project/get_skab.py` from the repository root first.")
    out = []
    for path in files:
        df = pd.read_csv(path, sep=";", parse_dates=["datetime"]).sort_values("datetime", kind="stable")
        out.append(df["anomaly"].to_numpy().astype(int))
    return out


def point_adjust(y: np.ndarray, pred: np.ndarray) -> np.ndarray:
    pred = pred.copy()
    change = np.flatnonzero(np.diff(np.r_[0, y, 0]))        # starts and (exclusive) ends alternate
    for start, end in zip(change[::2], change[1::2]):
        if pred[start:end].any():
            pred[start:end] = 1
    return pred


def f1(y: np.ndarray, pred: np.ndarray) -> tuple[float, float, float]:
    tp = int(np.sum((pred == 1) & (y == 1)))
    precision = tp / pred.sum() if pred.sum() else 0.0
    recall = tp / y.sum()
    return precision, recall, (0.0 if tp == 0 else 2 * precision * recall / (precision + recall))


def main() -> None:
    labels = load_labels()
    y_all = np.concatenate(labels)
    lengths = [int(y.sum()) for y in labels]                # one event per experiment
    print(f"{len(labels)} experiments, {len(y_all)} rows, prevalence {y_all.mean():.3f}, "
          f"event length {min(lengths)}-{max(lengths)} rows (median {int(np.median(lengths))})\n")
    print("| flag rate q | raw P | raw R | raw F1 | PA P | PA R | PA F1 | events counted | expected events |")
    print("|---|---|---|---|---|---|---|---|---|")
    rng = np.random.default_rng(0)
    for q in (0.0005, 0.002, 0.01, 0.05, 0.2):
        raw, adjusted, counted = [], [], 0
        for y in labels:
            pred = (rng.random(len(y)) < q).astype(int)
            pa = point_adjust(y, pred)
            counted += int(pa[y == 1].all())
            raw.append(pred)
            adjusted.append(pa)
        p0, r0, f0 = f1(y_all, np.concatenate(raw))
        p1, r1, f1_pa = f1(y_all, np.concatenate(adjusted))
        expected = sum(1 - (1 - q) ** L for L in lengths)
        print(f"| {q:.4f} | {p0:.3f} | {r0:.3f} | {f0:.3f} | {p1:.3f} | {r1:.3f} | {f1_pa:.3f} "
              f"| {counted}/{len(labels)} | {expected:.1f} |")
    print("\nReference points on the same rows: flag everything gives F1 "
          f"{2 * y_all.mean() / (1 + y_all.mean()):.3f}; the best F1 on the SKAB README leaderboard (not point-adjusted) is 0.78.")


if __name__ == "__main__":
    main()
