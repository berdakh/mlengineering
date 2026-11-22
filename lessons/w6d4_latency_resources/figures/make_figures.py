"""Plot lesson w6d4's figures from figures/data/*.json (written by measure.py) and write the challenge's
measured curve.

    python lessons/w6d4_latency_resources/figures/make_figures.py

Also runs the SYNTHETIC coordinated-omission simulation from example/coordinated_omission.py.
"""
from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
UNIT = HERE.parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

CONFIGS = [("uvicorn", 1, "1 worker", SERIES[1]), ("uvicorn", 2, "2 workers", SERIES[0]),
           ("uvicorn", 4, "4 workers", SERIES[6]), ("serve", 2, "2 workers + TCP_NODELAY", SERIES[2])]


def load_runs() -> dict:
    out = defaultdict(list)
    for path in sorted((HERE / "data").glob("workers*_rep*.json")):
        d = json.loads(path.read_text())
        key = (d["meta"].get("launcher", "uvicorn"), d["meta"]["workers"])
        for r in d["runs"]:
            out[key].append({"rate": r["target_rps"], **r["summary"], "rss_after": d["meta"]["server_rss_mb_after"]})
    return out


def fig_latency_vs_rate(runs) -> Path:
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 3.6), sharey=True)
    for ax, key in zip(axes, ("p50_ms", "p95_ms"), strict=True):
        for launcher, workers, label, colour in CONFIGS:
            rows = runs[(launcher, workers)]
            rates = sorted({r["rate"] for r in rows})
            means = [np.mean([r[key] for r in rows if r["rate"] == x]) for x in rates]
            ax.plot(rates, means, "-", color=colour, label=label)
            ax.plot([r["rate"] for r in rows], [r[key] for r in rows], "o", color=colour, ms=4)
        ax.axhline(100, color=INK["muted"], lw=1, ls="--")
        ax.set_yscale("log")
        ax.set_xlabel("offered load (requests per second, open loop)")
        ax.set_title(key.replace("_ms", "") + " latency")
        ax.set_xticks([20, 60, 90, 120])
    axes[1].text(21, 115, "p95 budget 100 ms", color=INK["secondary"], fontsize=8)
    axes[0].set_ylabel("ms (log scale)")
    axes[1].legend(loc="upper left", bbox_to_anchor=(1.0, 1.0))
    fig.suptitle("One worker collapses past ~85 req/s; more workers add a 40 ms floor until TCP_NODELAY is set",
                 x=0.02, y=1.04, ha="left", fontsize=10.5, fontweight="bold")
    return save(fig, HERE / "latency_vs_rate.svg")


def fig_throughput(runs) -> Path:
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.plot([0, 125], [0, 125], color=INK["muted"], lw=1, ls="--")
    ax.text(100, 106, "served = offered", color=INK["secondary"], fontsize=8, rotation=0)
    for launcher, workers, label, colour in (CONFIGS[0], CONFIGS[3]):
        rows = runs[(launcher, workers)]
        ax.plot([r["rate"] for r in rows], [r["throughput_rps"] for r in rows], "o", color=colour, label=label)
        rates = sorted({r["rate"] for r in rows})
        ax.plot(rates, [np.mean([r["throughput_rps"] for r in rows if r["rate"] == x]) for x in rates], "-", color=colour)
    ax.set_xlabel("offered load (requests per second)")
    ax.set_ylabel("successful responses per second")
    ax.set_xlim(0, 125)
    ax.set_ylim(0, 130)
    ax.legend(loc="upper left")
    ax.set_title("Past saturation, one worker serves less, not more: timeouts")
    return save(fig, HERE / "throughput.svg")


def fig_distribution() -> Path:
    d = json.loads((HERE / "data" / "detail_workers1.json").read_text())
    fig, ax = plt.subplots(figsize=(6.6, 3.5))
    for run, colour in zip(d["runs"], (SERIES[0], SERIES[1]), strict=True):
        lat = np.sort(np.array(run["latencies_ms"]))
        if lat.size == 0:
            continue
        frac = np.arange(1, lat.size + 1) / lat.size
        ax.plot(lat, frac, color=colour, label=f"{run['target_rps']:.0f} req/s offered (n={lat.size} ok)")
        p99 = np.percentile(lat, 99)
        ax.plot([p99], [0.99], "o", color=colour)
    ax.set_xscale("log")
    ax.set_xlabel("latency of successful requests, ms (log scale)")
    ax.set_ylabel("fraction of requests")
    ax.axhline(0.99, color=INK["muted"], lw=1, ls=":")
    ax.text(ax.get_xlim()[0] * 1.1, 0.955, "p99", color=INK["secondary"], fontsize=8)
    ax.legend(loc="lower right")
    ax.set_title("One worker: the whole distribution moves past saturation")
    return save(fig, HERE / "latency_cdf.svg")


def fig_coordinated_omission() -> Path:
    spec = importlib.util.spec_from_file_location("co", UNIT / "example" / "coordinated_omission.py")
    co = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(co)
    rows = [co.report("closed loop", co.closed_loop()), co.report("open loop", co.open_loop())]
    keys = ["p50", "p95", "p99", "p99.9"]
    x = np.arange(len(keys))
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for i, (row, colour) in enumerate(zip(rows, (SERIES[1], SERIES[0]), strict=True)):
        vals = [row[k] for k in keys]
        ax.bar(x + (i - 0.5) * 0.36, vals, width=0.34, color=colour, label=row["method"])
        for xi, v in zip(x, vals, strict=True):
            ax.text(xi + (i - 0.5) * 0.36, v * 1.15, f"{v:.0f}", ha="center", fontsize=8, color=INK["secondary"])
    ax.set_yscale("log")
    ax.set_ylim(5, 3000)
    ax.set_xticks(x, keys)
    ax.set_ylabel("reported latency, ms (log)")
    ax.legend(loc="upper left")
    ax.set_title("Same server, same 1 s stall: the closed loop reports p99 = 10 ms (SYNTHETIC)")
    return save(fig, HERE / "coordinated_omission.svg")


def write_challenge_curve(runs) -> Path:
    rows = runs[("uvicorn", 1)]
    out = UNIT / "challenge" / "measured_curve.csv"
    with out.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rate_rps", "p50_ms", "p95_ms", "p99_ms", "mean_ms", "error_rate", "throughput_rps"])
        for rate in sorted({r["rate"] for r in rows}):
            sel = [r for r in rows if r["rate"] == rate]
            w.writerow([rate] + [round(float(np.mean([r[k] for r in sel])), 2)
                                 for k in ("p50_ms", "p95_ms", "p99_ms", "mean_ms", "error_rate", "throughput_rps")])
    return out


def main() -> None:
    runs = load_runs()
    outs = [fig_latency_vs_rate(runs), fig_throughput(runs), fig_distribution(), fig_coordinated_omission(),
            write_challenge_curve(runs)]
    for p in outs:
        print("wrote", p.relative_to(ROOT))
    print("\nmeans over the two repetitions:")
    for launcher, workers, label, _ in CONFIGS:
        rows = runs[(launcher, workers)]
        for rate in sorted({r["rate"] for r in rows}):
            sel = [r for r in rows if r["rate"] == rate]
            f = lambda k: np.mean([r[k] for r in sel])  # noqa: E731
            print(f"  {label:<24} {rate:>4.0f}/s  p50 {f('p50_ms'):8.1f}  p95 {f('p95_ms'):8.1f}  p99 {f('p99_ms'):8.1f} ms"
                  f"  err {f('error_rate'):.3f}  thr {f('throughput_rps'):6.1f}/s  RSS after {f('rss_after'):6.0f} MB")


if __name__ == "__main__":
    main()
