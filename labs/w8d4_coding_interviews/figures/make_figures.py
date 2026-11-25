"""Regenerate the data figures of lesson w8d4 and handbook H16.4.

    python labs/w8d4_coding_interviews/figures/make_figures.py [png_dir]

Figure 1 times the worked example's two solutions on this machine (timings vary by machine; the ratio of
slopes is what matters). Figure 2 reads the SYNTHETIC rides database. Plotted numbers go to
figure_data.csv. An optional argument writes PNG copies for render checks.
"""
from __future__ import annotations

import csv
import importlib.util
import sqlite3
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
UNIT = HERE.parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

ROWS: list[dict] = []
PNG_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else None


def _save(fig, name: str) -> None:
    if PNG_DIR:
        PNG_DIR.mkdir(parents=True, exist_ok=True)
        fig.savefig(PNG_DIR / f"{name}.png", dpi=110)
    save(fig, HERE / f"{name}.svg")


def scaling() -> None:
    spec = importlib.util.spec_from_file_location("w8d4_example", UNIT / "example" / "repeat_within_k.py")
    ex = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ex)
    rows = ex.main()
    ns = [r[0] for r in rows]
    fig, ax = plt.subplots(figsize=(7, 3.6))
    for colour, idx, name in ((SERIES[1], 1, "brute force, O(n k) with k = n/10"), (SERIES[0], 2, "hash map, O(n)")):
        ys = [r[idx] for r in rows]
        ax.plot(ns, ys, marker="o", color=colour, label=name)
        for n, y in zip(ns, ys):
            ROWS.append({"figure": "scaling", "series": name, "x": n, "y": round(y, 6)})
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("input size n (log scale)")
    ax.set_ylabel("seconds (log scale)")
    ax.set_title("Doubling n: about 4x the time for the quadratic version, about 2x for the linear one")
    ax.legend(loc="upper left")
    _save(fig, "scaling")


def streak(driver: int = 4) -> None:
    con = sqlite3.connect(UNIT / "data" / "rides.db")
    t = pd.read_sql_query(
        "SELECT DATE(requested_at) AS day FROM trips WHERE status = 'completed' AND driver_id = ?", con,
        params=(driver,))
    con.close()
    days = pd.to_datetime(sorted(set(t["day"])))
    s = pd.Series(1, index=days)
    full = s.reindex(pd.date_range("2026-02-01", "2026-04-30"), fill_value=0)
    # islands: consecutive active days share (day - position)
    active = full[full == 1].index
    grp = (active - pd.to_timedelta(range(len(active)), unit="D"))
    lengths = pd.Series(1, index=active).groupby(grp).sum()
    best_key = lengths[lengths == lengths.max()].index.min()
    best_days = active[grp == best_key]
    fig, ax = plt.subplots(figsize=(7, 2.4))
    colours = [SERIES[1] if d in best_days else (SERIES[0] if v else INK["grid"]) for d, v in full.items()]
    ax.bar(full.index, [1] * len(full), color=colours, width=0.8)
    import matplotlib.dates as mdates
    ax.xaxis.set_major_locator(mdates.MonthLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    ax.set_yticks([])
    ax.grid(visible=False)
    ax.set_title(f"Driver {driver}: longest streak {len(best_days)} days from {best_days[0].date()} (orange)")
    ax.set_xlabel("SYNTHETIC rides database, Feb-Apr 2026; blue = completed trip that day, grey = none")
    for d, v in full.items():
        ROWS.append({"figure": "streak", "series": f"driver_{driver}", "x": d.date().isoformat(), "y": int(v)})
    _save(fig, "streak")


def main() -> None:
    scaling()
    streak()
    with open(HERE / "figure_data.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["figure", "series", "x", "y"])
        w.writeheader()
        w.writerows(ROWS)
    print(f"wrote 2 figures and {len(ROWS)} rows")


if __name__ == "__main__":
    main()
