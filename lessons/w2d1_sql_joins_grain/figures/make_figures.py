"""Figures for w2d1 and handbook H3.1, computed from the lesson's SYNTHETIC maintenance database.

    python lessons/w2d1_sql_joins_grain/figures/make_figures.py

Writes SVGs next to this file and prints the plotted numbers.
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

DB = HERE.parent / "data" / "maintenance.db"

NAIVE = """
SELECT m.machine_id,
       SUM(w.labor_hours) AS labor, SUM(d.hours) AS downtime,
       COUNT(DISTINCT w.wo_id) AS n_wo, COUNT(DISTINCT d.event_id) AS n_dt
FROM machines m
LEFT JOIN work_orders w     ON w.machine_id = m.machine_id
LEFT JOIN downtime_events d ON d.machine_id = m.machine_id
GROUP BY m.machine_id
"""
TRUE_LABOR = "SELECT machine_id, SUM(labor_hours) FROM work_orders GROUP BY machine_id"
TRUE_DOWN = "SELECT machine_id, SUM(hours) FROM downtime_events GROUP BY machine_id"


def main() -> None:
    con = sqlite3.connect(DB)
    naive = {r[0]: r[1:] for r in con.execute(NAIVE)}
    true_labor = dict(con.execute(TRUE_LABOR))
    true_down = dict(con.execute(TRUE_DOWN))
    total_true = (con.execute("SELECT SUM(labor_hours) FROM work_orders").fetchone()[0],
                  con.execute("SELECT SUM(hours) FROM downtime_events").fetchone()[0])
    total_naive = (sum(v[0] or 0 for v in naive.values()), sum(v[1] or 0 for v in naive.values()))
    print(f"labour hours   true {total_true[0]:.1f}  naive join {total_naive[0]:.1f}")
    print(f"downtime hours true {total_true[1]:.1f}  naive join {total_naive[1]:.1f}")

    # Figure 1: totals, true vs naive two-children join
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    labels = ["Labour hours", "Downtime hours"]
    y = [1, 0]
    h = 0.34
    ax.barh([v + h / 2 for v in y], total_true, height=h, color=SERIES[0], label="true (single-table total)")
    ax.barh([v - h / 2 for v in y], total_naive, height=h, color=SERIES[1], label="naive join of both children")
    for yy, t, n in zip(y, total_true, total_naive):
        ax.text(t + 25, yy + h / 2, f"{t:,.1f}", va="center", color=INK["primary"])
        ax.text(n + 25, yy - h / 2, f"{n:,.1f}  ({n / t:.1f}x)", va="center", color=INK["primary"])
    ax.set_yticks(y, labels)
    ax.set_xlim(0, max(total_naive) * 1.28)
    ax.set_xlabel("hours summed over all machines")
    ax.set_title("Joining two children of one parent inflates both sums (SYNTHETIC)")
    ax.grid(axis="y", visible=False)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2)
    save(fig, HERE / "fanout_totals.svg")

    # Figure 2: per machine, inflation factor of labour equals the number of downtime events
    xs, ys = [], []
    for mid, (labor, _down, _n_wo, n_dt) in naive.items():
        if labor and true_labor.get(mid):
            xs.append(max(n_dt, 1))  # LEFT JOIN: a machine with no downtime keeps one row per order
            ys.append(labor / true_labor[mid])
    fig, ax = plt.subplots(figsize=(5.2, 3.6))
    lim = max(xs) + 1
    ax.plot([0, lim], [0, lim], color=INK["axis"], linewidth=1, zorder=1)
    ax.scatter(xs, ys, s=42, color=SERIES[1], edgecolor=INK["surface"], linewidth=1.5, zorder=2)
    ax.text(lim - 0.2, lim - 0.9, "factor = number of\ndowntime events", ha="right", color=INK["secondary"])
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.set_xlabel("downtime events on the machine (minimum 1 under LEFT JOIN)")
    ax.set_ylabel("reported labour / true labour")
    ax.set_title("Each machine's labour is multiplied by its\nrow count in the other child (SYNTHETIC)")
    save(fig, HERE / "fanout_factor_per_machine.svg")
    print(f"machines plotted: {len(xs)}; max factor {max(ys):.1f}; all on the identity line: "
          f"{all(abs(a - b) < 1e-9 for a, b in zip(xs, ys))}")


if __name__ == "__main__":
    main()
