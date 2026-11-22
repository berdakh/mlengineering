"""Figures for w2d2 and handbook H3.2, computed from the lesson's SYNTHETIC cold-chain database
with the reference queries (gaps-and-islands, as-of join).

    python lessons/w2d2_sql_windows_timeseries/figures/make_figures.py
"""
from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.figstyle import INK, SERIES, STATUS, apply, save  # noqa: E402

apply()
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

DB = HERE.parent / "data" / "coldchain.db"
QUERIES = ROOT / "solutions" / "lessons" / "w2d2_sql_windows_timeseries" / "lab" / "queries"
DEVICE = "D01"


def main() -> None:
    con = sqlite3.connect(DB)
    readings = pd.read_sql("SELECT * FROM readings_dedup WHERE device_id = ? ORDER BY ts_epoch", con,
                           params=(DEVICE,), parse_dates=["ts"])
    episodes = pd.read_sql((QUERIES / "q5_alert_episodes.sql").read_text(), con, parse_dates=["start_ts", "end_ts"])
    episodes = episodes[episodes.device_id == DEVICE]

    # Figure 1: per-sample alert flags become episodes (islands). Show the second day.
    t0 = readings.ts.min().normalize() + pd.Timedelta(hours=24)
    t1 = t0 + pd.Timedelta(hours=24)
    r = readings[(readings.ts >= t0) & (readings.ts < t1)]
    e = episodes[(episodes.end_ts >= t0) & (episodes.start_ts < t1)]
    fig, ax = plt.subplots(figsize=(8, 3.3))
    for i, row in enumerate(e.itertuples()):
        ax.axvspan(row.start_ts, row.end_ts + pd.Timedelta(minutes=4), color=SERIES[1], alpha=0.18,
                   label="episode (island)" if i == 0 else None)
    ax.plot(r.ts, r.temperature, color=SERIES[0], linewidth=1.4, label="reported temperature")
    flagged = r[r.alert == 1]
    ax.scatter(flagged.ts, flagged.temperature, s=22, color=SERIES[1], edgecolor=INK["surface"],
               linewidth=0.8, zorder=3, label="sample with alert = 1")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.set_xlabel(f"time of measurement on {t0:%d %b %Y}, device {DEVICE} (UTC)")
    ax.set_ylabel("temperature (deg C)")
    ax.set_title("Gaps and islands: flagged samples collapse into episodes (SYNTHETIC)")
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.24), ncol=3)
    save(fig, HERE / "islands.svg")
    print(f"{DEVICE} {t0:%d %b %H:%M} to {t1:%d %b %H:%M}: {len(r)} readings, {int(r.alert.sum())} flagged, {len(e)} episodes")
    print(f"{DEVICE} whole day: {len(readings)} readings, {int(readings.alert.sum())} flagged, {len(episodes)} episodes")

    # Figure 2: as-of join. Each reading takes the calibration row in force at its timestamp.
    asof = pd.read_sql((QUERIES / "q6_asof_calibration.sql").read_text(), con, parse_dates=["ts"])
    a = asof[asof.device_id == DEVICE].sort_values("ts")
    cal = pd.read_sql("SELECT * FROM calibration WHERE device_id = ? ORDER BY valid_from_epoch", con,
                      params=(DEVICE,), parse_dates=["valid_from"])
    fig, (top, bottom) = plt.subplots(2, 1, figsize=(8, 4.6), sharex=True, height_ratios=[1, 1.6])
    top.step(a.ts, a.corrected_temperature - readings.set_index("reading_id").loc[a.reading_id, "temperature"].to_numpy(),
             where="post", color=SERIES[2])
    top.set_ylabel("offset applied\n(deg C)")
    top.set_title(f"As-of join: each reading uses the calibration in force at its own time (SYNTHETIC, {DEVICE})")
    bottom.plot(a.ts, a.corrected_temperature, color=SERIES[0], linewidth=1.2, label="corrected temperature")
    bottom.step(a.ts, a.alert_threshold_c, where="post", color=INK["secondary"], linewidth=1.4,
                linestyle="--", label="alert threshold in force")
    first = True
    for v in cal.valid_from:
        if a.ts.min() <= v <= a.ts.max():
            top.axvline(v, color=INK["axis"], linewidth=1)
            bottom.axvline(v, color=INK["axis"], linewidth=1,
                           label="a calibration row takes effect" if first else None)
            first = False
    bottom.xaxis.set_major_formatter(mdates.DateFormatter("%d %b %H:%M"))
    bottom.set_xlabel("time of measurement (UTC)")
    bottom.set_ylabel("temperature (deg C)")
    bottom.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=3)
    save(fig, HERE / "asof_calibration.svg")
    print(f"{DEVICE} calibration rows: {len(cal)}; valid_from: {[f'{v:%m-%d %H:%M}' for v in cal.valid_from]}")
    print(f"{DEVICE} readings over the threshold in force: {int(a.over_threshold.sum())} of {len(a)}")
    _ = STATUS


if __name__ == "__main__":
    main()
