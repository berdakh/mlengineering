"""Figure for handbook H10.4: mean queueing delay against utilisation for two textbook single-server queues.

    python handbook/figures/h10_4/make_figures.py

Computed from formulas (no data): M/M/1 (Poisson arrivals, exponential service) Wq/S = rho / (1 - rho);
M/D/1 (Poisson arrivals, constant service) Wq/S = rho / (2 (1 - rho)).
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def main() -> None:
    rho = np.linspace(0.01, 0.95, 300)
    fig, ax = plt.subplots(figsize=(6.4, 3.5))
    ax.plot(rho, rho / (1 - rho), color=SERIES[1], label="M/M/1: variable service time")
    ax.plot(rho, rho / (2 * (1 - rho)), color=SERIES[0], label="M/D/1: constant service time")
    for r in (0.5, 0.7, 0.9):
        ax.axvline(r, color=INK["grid"], lw=1)
        ax.text(r + 0.005, 17.2, f"rho={r}", color=INK["secondary"], fontsize=8)
        ax.plot([r], [r / (1 - r)], "o", color=SERIES[1], ms=4)
        ax.text(r - 0.02, r / (1 - r) + 0.7, f"{r / (1 - r):.1f}", ha="right", fontsize=8, color=INK["secondary"])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 19)
    ax.set_xlabel("utilisation rho = arrival rate x service time / workers")
    ax.set_ylabel("mean wait in queue / service time")
    ax.legend(loc="upper left")
    ax.set_title("Waiting time explodes as utilisation approaches 1")
    print("wrote", save(fig, HERE / "queueing_delay.svg").relative_to(ROOT))


if __name__ == "__main__":
    main()
