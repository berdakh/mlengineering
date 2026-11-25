"""Regenerate the data figures of lesson w7d3 and handbook H15.4.

    python project/get_skab.py                                          # once
    python labs/w7d3_drift_vs_degradation/figures/make_figures.py    # about 10 s

Real data: figures 1 and 2 come from the reference replay (solutions/.../lab/replay_report.py), i.e.
real SKAB valve recordings on a CONSTRUCTED 60-day timeline with SIMULATED label arrival.
Figure 3 is SYNTHETIC (a stated generator below). Figure 4 is arithmetic (Wilson intervals).
Every plotted number is also written to figure_data.csv.
"""
from __future__ import annotations

import csv
import importlib.util
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
SOL_LAB = ROOT / "solutions" / "labs" / "w7d3_drift_vs_degradation" / "lab"
sys.path.insert(0, str(SOL_LAB / "src"))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

from flowguard.uncertainty import wilson_interval  # noqa: E402

ROWS: list[dict] = []
PERIOD_COLOUR = {"A": SERIES[0], "B": SERIES[1], "C": SERIES[2]}
PERIOD_NAME = {"A": "A: as recorded", "B": "B: sensor recalibrated", "C": "C: threshold regression"}


def replay() -> dict:
    spec = importlib.util.spec_from_file_location("replay_report", SOL_LAB / "replay_report.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.run(ROOT / "data" / "raw" / "skab")


def fig_drift(out: dict) -> None:
    w = out["drift_windows"]
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    for i, d in enumerate(w):
        ax.bar(i, d["psi"], color=PERIOD_COLOUR[d["period"]], width=0.8,
               label=PERIOD_NAME[d["period"]] if i % 4 == 0 else None)
        ROWS.append({"figure": "drift_psi_windows", "x": d["days"], "series": d["period"], "value": round(d["psi"], 4)})
    thr = out["psi_threshold"]
    ax.axhline(thr, color=INK["primary"], linewidth=1, linestyle="--")
    ax.text(11.6, thr * 1.15, f"calibrated threshold {thr:.2f}", ha="right", va="bottom", color=INK["secondary"], fontsize=8)
    ax.set_yscale("log")
    ax.set_xticks(range(len(w)), [d["days"] for d in w], rotation=45, ha="right")
    ax.set_xlabel("replay days (5-day windows)")
    ax.set_ylabel("PSI of flow rate vs reference (log)")
    ax.set_title("A recalibrated sensor pushes PSI 9-13x past its threshold; the faults caught do not change")
    ax.legend(loc="upper right", fontsize=8)
    save(fig, HERE / "drift_psi_windows.svg")


def fig_recall(out: dict) -> None:
    series = out["recall_over_time"]
    days = [r["day"] for r in series]
    true = {p: int(v["day 150"]["true_recall"].split("/")[0]) / 20 for p, v in out["periods"].items()}
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    for p in "ABC":
        y = [r[f"recall_{p}"] for r in series]
        ax.plot(days, y, color=PERIOD_COLOUR[p], label=f"{PERIOD_NAME[p]}: estimate")
        ax.axhline(true[p], color=PERIOD_COLOUR[p], linestyle=":", linewidth=1.5)
        for d, v in zip(days, y):
            ROWS.append({"figure": "recall_over_time", "x": d, "series": p, "value": v})
    same = true["A"] == true["B"]
    ax.text(days[-1] + 2, true["A"], f"true A{' and B' if same else ''} {true['A']:.2f}", color=INK["secondary"],
            va="center", fontsize=8)
    if not same:
        ax.text(days[-1] + 2, true["B"], f"true B {true['B']:.2f}", color=INK["secondary"], va="center", fontsize=8)
    ax.text(days[-1] + 2, true["C"], f"true C {true['C']:.2f}", color=INK["secondary"], va="center", fontsize=8)
    ax.axvline(60, color=INK["muted"], linewidth=1)
    ax.text(61, 1.0, "timeline ends", color=INK["secondary"], fontsize=8, va="top")
    ax.set_xlim(15, days[-1] + 40)
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("day on which the estimate is computed (labels known so far)")
    ax.set_ylabel("estimated event recall")
    ax.set_title("Recall estimates start optimistic and settle only after missed-fault reports arrive")
    ax.legend(loc="upper right", fontsize=8)
    save(fig, HERE / "recall_over_time.svg")


def fig_verification_bias() -> None:
    """SYNTHETIC: 400 alarms; P(alarm is true) = 1 / (1 + exp(-(peak - 6))), peak ~ Uniform(3, 12).
    Operators investigate the top fraction by peak score; precision is measured on those only."""
    rng = np.random.default_rng(7)
    peak = rng.uniform(3, 12, 400)
    true = rng.random(400) < 1 / (1 + np.exp(-(peak - 6)))
    order = np.argsort(-peak)
    fracs = np.linspace(0.1, 1.0, 19)
    est = [true[order[: int(round(f * len(peak)))]].mean() for f in fracs]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.plot(fracs * 100, est, color=SERIES[0], marker="o", markersize=4, label="precision among investigated alarms")
    ax.axhline(true.mean(), color=SERIES[1], linestyle="--", label=f"true precision of all alarms ({true.mean():.2f})")
    for f, e in zip(fracs, est):
        ROWS.append({"figure": "verification_bias", "x": round(float(f), 3), "series": "estimate", "value": round(float(e), 4)})
    ROWS.append({"figure": "verification_bias", "x": "all", "series": "truth", "value": round(float(true.mean()), 4)})
    ax.set_xlabel("alarms investigated (top % by peak score)")
    ax.set_ylabel("precision")
    ax.set_ylim(0.5, 1.02)
    ax.set_title("SYNTHETIC: labelling only the worst-looking alarms overstates precision")
    ax.legend(loc="lower left", fontsize=8)
    save(fig, HERE / "verification_bias.svg")


def fig_power() -> None:
    ns = np.arange(5, 201)
    half = [(wilson_interval(int(round(0.6 * n)), int(n))[1] - wilson_interval(int(round(0.6 * n)), int(n))[0]) / 2
            for n in ns]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.plot(ns, half, color=SERIES[0], label="half-width of a 95 % Wilson interval at recall 0.6")
    need = int(ns[np.argmax(np.array(half) <= 0.10)])
    ax.axhline(0.10, color=INK["muted"], linewidth=1, linestyle="--")
    for n, label in [(20, "one replay period: 20 faults"), (need, f"±0.10 needs about {need} faults")]:
        h = half[n - 5]
        ax.plot([n], [h], marker="o", color=SERIES[1], markersize=6)
        ax.annotate(label, (n, h), xytext=(10, 10), textcoords="offset points", fontsize=8, color=INK["secondary"])
    for n, h in zip(ns[::5], half[::5]):
        ROWS.append({"figure": "power_wilson", "x": int(n), "series": "half_width", "value": round(float(h), 4)})
    ax.set_xlabel("faults with a known outcome in the window")
    ax.set_ylabel("interval half-width")
    ax.set_title("A window needs about 90 faults to pin recall to ±0.10")
    ax.legend(loc="upper right", fontsize=8)
    save(fig, HERE / "power_wilson.svg")


def main() -> None:
    out = replay()
    fig_drift(out)
    fig_recall(out)
    fig_verification_bias()
    fig_power()
    with open(HERE / "figure_data.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["figure", "x", "series", "value"])
        w.writeheader()
        w.writerows(ROWS)
    print("wrote 4 figures and figure_data.csv to", HERE)


if __name__ == "__main__":
    main()
