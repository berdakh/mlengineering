"""Figures for project/README.md, from the REAL SKAB files.

    python project/get_skab.py                  # once
    python project/figures/make_figures.py      # rewrites project/figures/*.svg and prints the numbers
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

RAW = ROOT / "data" / "raw" / "skab"
OUT = Path(__file__).resolve().parent
FAMILY_COLOUR = {"valve1": SERIES[0], "valve2": SERIES[1], "other": SERIES[2]}
NORMAL, ANOMALY = "#c3c2b7", SERIES[7]


def load() -> dict[str, pd.DataFrame]:
    if not RAW.is_dir():
        sys.exit("data/raw/skab is missing: run `python project/get_skab.py` first")
    frames = {}
    for family in ("valve1", "valve2", "other"):
        for path in sorted((RAW / family).glob("*.csv"), key=lambda p: int(p.stem)):
            frames[f"{family}/{path.stem}"] = pd.read_csv(path, sep=";", parse_dates=["datetime"])
    return frames


def fig_one_experiment(frames, plt) -> None:
    exp = "valve1/0"
    df = frames[exp].reset_index(drop=True)
    sensors = [c for c in df.columns if c not in ("datetime", "anomaly", "changepoint")]
    on = np.flatnonzero(df["anomaly"].to_numpy() == 1)
    fig, axes = plt.subplots(4, 2, figsize=(9, 6.4), sharex=True)
    for ax, name in zip(axes.ravel(), sensors):
        ax.axvspan(on[0], on[-1], color=ANOMALY, alpha=0.13, lw=0)
        ax.plot(df.index, df[name], color=SERIES[0], lw=1.0)
        ax.set_title(name, fontsize=9, fontweight="normal", color=INK["secondary"])
    for ax in axes[-1]:
        ax.set_xlabel("row (about 1 s per row)")
    fig.suptitle(f"One experiment ({exp}): eight sensors, one labelled anomalous segment (shaded)",
                 x=0.01, ha="left", fontsize=11, fontweight="bold")
    fig.tight_layout()
    save(fig, OUT / "one_experiment.svg")
    print(f"{exp}: {len(df)} rows, anomalous rows {on[0]}-{on[-1]}")


def fig_onsets(frames, plt) -> None:
    rows = []
    for exp, df in frames.items():
        a = df["anomaly"].to_numpy()
        on = np.flatnonzero(a == 1)
        rows.append((exp, exp.split("/")[0], len(df), int(on[0]), int(on[-1])))
    t = pd.DataFrame(rows, columns=["experiment", "family", "n", "start", "end"])
    fig, ax = plt.subplots(figsize=(9, 7.2))
    y = np.arange(len(t))[::-1]
    ax.barh(y, t["n"], color=NORMAL, height=0.62, label="labelled normal")
    ax.barh(y, t["end"] - t["start"] + 1, left=t["start"], color=ANOMALY, height=0.62, label="labelled anomalous")
    ax.axvspan(550, 600, color=INK["muted"], alpha=0.18, lw=0)
    ax.text(575, len(t) + 0.1, "rows 550-600", ha="center", va="bottom", fontsize=8, color=INK["secondary"])
    ax.set_yticks(y, t["experiment"], fontsize=7)
    ax.set_ylim(-0.7, len(t) + 1.3)
    ax.set_xlabel("row within experiment")
    in_band = int(t["start"].between(550, 600).sum())
    ax.set_title(f"The anomaly starts at row 550-600 in {in_band} of {len(t)} experiments: position leaks the label")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="lower right")
    save(fig, OUT / "anomaly_onsets.svg")
    t.to_csv(OUT / "anomaly_onsets.csv", index=False)
    print(f"onset in rows 550-600: {in_band} of {len(t)}; onset min {t.start.min()} max {t.start.max()}")
    return t


def fig_rows(t, plt) -> None:
    fig, ax = plt.subplots(figsize=(9, 3.4))
    x = np.arange(len(t))
    for family, colour in FAMILY_COLOUR.items():
        m = (t["family"] == family).to_numpy()
        ax.bar(x[m], t["n"][m], color=colour, width=0.72, label=f"{family} ({m.sum()} experiments)")
    ax.set_xticks(x, [e.split("/")[1] for e in t["experiment"]], fontsize=7)
    ax.set_xlabel("experiment number within family")
    ax.set_ylabel("rows")
    ax.set_title(f"34 labelled experiments, {int(t['n'].sum()):,} rows: similar lengths, three families")
    ax.grid(axis="x", visible=False)
    ax.legend(ncols=3, loc="lower center")
    save(fig, OUT / "rows_per_experiment.svg")
    print(t.groupby("family")["n"].agg(["count", "min", "max", "sum"]).to_string())


def main() -> None:
    apply()
    import matplotlib.pyplot as plt
    frames = load()
    fig_one_experiment(frames, plt)
    t = fig_onsets(frames, plt)
    fig_rows(t, plt)


if __name__ == "__main__":
    main()
