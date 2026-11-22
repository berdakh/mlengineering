"""Plot lesson w6d3's figures from figure_data.csv (written by measure.py on the authoring machine).

    python lessons/w6d3_ci/figures/make_figures.py
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402


def main() -> None:
    rows = list(csv.DictReader((HERE / "figure_data.csv").open()))
    inst = {c: [float(r["value"]) for r in rows if r["measure"] == "install_s" and r["condition"] == c]
            for c in ("cold", "warm")}
    flaky = [(int(r["condition"]), int(r["value"])) for r in rows if r["measure"].startswith("flaky_failures")]
    runs = int(next(r["measure"] for r in rows if r["measure"].startswith("flaky")).rsplit("_", 1)[1])

    fig, ax = plt.subplots(figsize=(6.2, 3.0))
    labels = ["empty pip cache", "warm pip cache"]
    means = [sum(v) / len(v) for v in inst.values()]
    ax.barh(labels, means, color=[SERIES[1], SERIES[0]], height=0.5)
    for i, vals in enumerate(inst.values()):
        ax.plot(vals, [i] * len(vals), "o", color=INK["primary"], ms=5, label="single run" if i == 0 else None)
        ax.text(max(vals) + 0.35, i, f"{means[i]:.1f} s", va="center", color=INK["secondary"])
    ax.set_xlabel("seconds to install the lab project with [dev] extras in a fresh venv")
    ax.set_xlim(0, max(max(v) for v in inst.values()) * 1.25)
    ax.set_title("A warm pip cache cut install time by about a third here")
    ax.legend(loc="lower right")
    ax.invert_yaxis()
    outs = [save(fig, HERE / "install_cache.svg")]

    fig, ax = plt.subplots(figsize=(6.2, 3.2))
    xs = [b for b, _ in flaky]
    ys = [f for _, f in flaky]
    ax.bar([str(x) for x in xs], ys, color=SERIES[1], width=0.55)
    for x, y in zip(xs, ys, strict=True):
        ax.text(str(x), y + 0.08, f"{y}/{runs}", ha="center", color=INK["secondary"])
    ax.set_xlabel("other CPU-bound processes running on the 4-core machine")
    ax.set_ylabel(f"failures in {runs} runs")
    ax.set_ylim(0, max(ys + [1]) + 1)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.set_title("The same 50 ms assertion fails more often on a busier machine")
    outs.append(save(fig, HERE / "flaky_vs_load.svg"))
    for p in outs:
        print("wrote", p.relative_to(ROOT))


if __name__ == "__main__":
    main()
