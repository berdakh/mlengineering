"""Figure for handbook H6.5: how much normal operating time a false-alarm claim needs.

    python handbook/figures/h6_5/make_figures.py

Analytical (no data): exact one-sided 95 % upper bound of a Poisson rate after observing n false
alarms in T hours, chi2.ppf(0.95, 2(n+1)) / (2T). The marked exposures are the measured hours of
normal operation in the development and test experiments of the frozen v2 manifest (lesson w3d4).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.stats import chi2

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[3]))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

BUDGET = 1 / 8


def main() -> None:
    apply()
    hours = np.logspace(-0.3, 2.3, 200)
    fig, ax = plt.subplots(figsize=(7.4, 4.0))
    for n, colour in zip((0, 1, 3), SERIES):
        bound = chi2.ppf(0.95, 2 * (n + 1)) / (2 * hours)
        ax.plot(hours, bound, color=colour, label=f"{n} false alarm{'s' if n != 1 else ''} observed")
        ax.text(hours[-1] * 1.05, bound[-1], f"n = {n}", va="center", fontsize=9, color=INK["secondary"])
        need = chi2.ppf(0.95, 2 * (n + 1)) / (2 * BUDGET)
        print(f"n={n}: hours needed for a 95 % bound of {BUDGET}/h: {need:.1f}; "
              f"bound at 1.22 h: {chi2.ppf(0.95, 2 * (n + 1)) / (2 * 1.22):.2f}/h, at 5.00 h: "
              f"{chi2.ppf(0.95, 2 * (n + 1)) / (2 * 5.00):.2f}/h")
    ax.axhline(BUDGET, color=INK["muted"], ls="--", lw=1.0)
    ax.text(hours[0], BUDGET * 1.12, "budget: 1 false alarm per 8 h", fontsize=9, color=INK["secondary"])
    for t, name in ((1.22, "test: 1.22 h"), (5.00, "dev: 5.00 h")):
        ax.axvline(t, color=INK["axis"], lw=1.0)
        ax.text(t * 1.04, 0.02, name, fontsize=9, color=INK["secondary"], rotation=90, va="bottom")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("hours of normal operation observed (log scale)")
    ax.set_ylabel("95 % upper bound on false alarms per hour (log scale)")
    ax.set_title("Zero false alarms in 1.2 h still allows 2.5 per hour; the budget needs 24 h")
    ax.legend(loc="upper right")
    save(fig, HERE / "rate_bound_vs_hours.svg")


if __name__ == "__main__":
    main()
