"""Regenerate the w7d1 figures (deterministic).

    python labs/w7d1_service_logging_metrics/figures/make_figures.py

Figures 1-2 use REAL replay data: the reference solution's replay of two SKAB test experiments
(``solutions/.../lab/replay_demo.py``, run here if its results are missing; needs the SKAB download).
Figures 3-4 are SYNTHETIC illustrations. Numbers are printed and written to figure_data.csv.
"""
from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE.parent / "example"))

from tools.figstyle import INK, SERIES, STATUS, apply, save  # noqa: E402

import matplotlib.pyplot as plt  # noqa: E402

SOL_LAB = ROOT / "solutions" / "labs" / "w7d1_service_logging_metrics" / "lab"
ROWS: list[dict] = []


def replay_results() -> tuple[list[dict], str]:
    log, metrics = SOL_LAB / "results" / "service.log", SOL_LAB / "results" / "metrics.txt"
    if not (log.is_file() and metrics.is_file()):
        subprocess.run([sys.executable, str(SOL_LAB / "replay_demo.py")], check=True, cwd=ROOT,
                       stdout=subprocess.DEVNULL)
    events = [json.loads(l) for l in log.read_text().splitlines() if l.startswith("{")]
    return events, metrics.read_text()


def fig_duration_vs_samples(events: list[dict]) -> None:
    pred = {e["request_id"]: e for e in events if e.get("event") == "prediction"}
    acc = [e for e in events if e.get("event") == "access" and e.get("route") == "/predict"]
    ok = [(pred[e["request_id"]]["n_samples"], e["duration_ms"], pred[e["request_id"]]["machine_id"])
          for e in acc if e["status"] == 200 and e["request_id"] in pred]
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    for i, exp in enumerate(sorted({m for _, _, m in ok})):
        xs = [n for n, _, m in ok if m == exp]
        ys = [d for _, d, m in ok if m == exp]
        ax.plot(xs, ys, "o", color=SERIES[i], label=exp, markersize=6)
        last = int(np.argmax(xs))
        ax.annotate(exp, (xs[last], ys[last]), textcoords="offset points", xytext=(8, -12 if i else 10),
                    color=INK["secondary"], fontsize=9, va="center")
        for n, d in zip(xs, ys):
            ROWS.append({"figure": "duration_vs_samples", "series": exp, "x": n, "y": d})
    ax.set_xlabel("samples in the request")
    ax.set_ylabel("server-side duration (ms)")
    ax.set_title("Request duration grows with request size (real replay, 2 SKAB test runs)")
    ax.legend(loc="upper left")
    ax.set_xlim(0, 1300)
    save(fig, HERE / "duration_vs_samples.svg")


def fig_buckets(metrics_text: str) -> None:
    rows = []
    for line in metrics_text.splitlines():
        if line.startswith('flowguard_http_request_duration_seconds_bucket{route="/predict"'):
            le = line.split('le="')[1].split('"')[0]
            rows.append((le, float(line.rsplit(" ", 1)[1])))
    labels = [le for le, _ in rows]
    cum = np.array([v for _, v in rows])
    per = np.diff(np.concatenate([[0.0], cum]))
    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.4), sharey=True)
    for ax, vals, title, colour in ((axes[0], per, "per bucket (what you might expect)", SERIES[0]),
                                    (axes[1], cum, "cumulative le= (what /metrics shows)", SERIES[1])):
        ax.bar(range(len(labels)), vals, color=colour, width=0.8)
        ax.set_xticks(range(len(labels)), [f"{float(l)*1000:g}" if l != "+Inf" else "+Inf" for l in labels],
                      rotation=60, fontsize=8)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("upper bound le (ms)")
    axes[0].set_ylabel("requests")
    fig.suptitle("The /predict latency histogram from the real replay: per-bucket vs cumulative counts",
                 x=0.01, ha="left", fontweight="bold", fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    for le, c, p in zip(labels, cum, per):
        ROWS.append({"figure": "buckets", "series": "cumulative", "x": le, "y": c})
        ROWS.append({"figure": "buckets", "series": "per_bucket", "x": le, "y": p})
    save(fig, HERE / "histogram_buckets.svg")


def fig_percentile_averaging() -> None:
    import two_instances as ti
    rng = np.random.default_rng(7)
    a = rng.lognormal(mean=np.log(0.02), sigma=0.4, size=9000)
    b = rng.lognormal(mean=np.log(0.30), sigma=0.5, size=1000)
    both = np.concatenate([a, b])
    merged = ti.cumulative_buckets(a) + ti.cumulative_buckets(b)
    vals = {"p99 instance A": np.quantile(a, .99), "p99 instance B": np.quantile(b, .99),
            "mean of the two p99s": (np.quantile(a, .99) + np.quantile(b, .99)) / 2,
            "true p99 (all requests)": np.quantile(both, .99),
            "p99 from summed buckets": ti.quantile_from_buckets(merged, .99)}
    colours = [SERIES[0], SERIES[0], STATUS["critical"], SERIES[2], SERIES[2]]
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    names = list(vals)[::-1]
    ax.barh(names, [vals[n] * 1000 for n in names], color=colours[::-1], height=0.6)
    for i, n in enumerate(names):
        ax.text(vals[n] * 1000 + 15, i, f"{vals[n]*1000:.0f} ms", va="center", color=INK["secondary"], fontsize=9)
        ROWS.append({"figure": "percentile_averaging", "series": n, "x": "", "y": round(vals[n] * 1000, 1)})
    ax.set_xlabel("latency (ms)")
    ax.set_xlim(0, 1200)
    ax.set_title("Averaging percentiles across instances is wrong (SYNTHETIC)")
    save(fig, HERE / "percentile_averaging.svg")


def fig_burn_rate() -> None:
    """30 days at 40 req/min, target 99.5 %; a 3-hour partial outage on day 12 and a 4-minute blip on day 20."""
    minutes = np.arange(30 * 24 * 60)
    total = np.full(minutes.size, 40.0)
    rng = np.random.default_rng(3)
    bad = rng.binomial(40, 0.001, minutes.size).astype(float)
    inc = (minutes >= 12 * 1440 + 600) & (minutes < 12 * 1440 + 780)
    bad[inc] = rng.binomial(40, 0.25, inc.sum())
    blip = (minutes >= 20 * 1440 + 300) & (minutes < 20 * 1440 + 304)
    bad[blip] = 40
    budget = 0.005

    def burn(window: int) -> np.ndarray:
        cb, ct = np.convolve(bad, np.ones(window))[: bad.size], np.convolve(total, np.ones(window))[: bad.size]
        return (cb / ct) / budget

    long_b, short_b = burn(60), burn(5)
    page = (long_b >= 14.4) & (short_b >= 14.4)
    days = minutes / 1440
    fig, axes = plt.subplots(2, 1, figsize=(8.0, 4.8), sharex=True)
    axes[0].plot(days, np.maximum(short_b, 0.05), color=SERIES[1], lw=0.6, label="5-minute window")
    axes[0].plot(days, np.maximum(long_b, 0.05), color=SERIES[0], lw=1.6, label="1-hour window")
    axes[0].axhline(14.4, color=INK["muted"], lw=1, ls="--")
    axes[0].text(29.8, 18, "page if both >= 14.4", color=INK["secondary"], fontsize=9, ha="right")
    axes[0].set_yscale("log")
    axes[0].set_ylim(0.05, 500)
    axes[0].set_ylabel("burn rate (log)")
    axes[0].legend(loc="upper left", ncol=2)
    axes[0].set_title("Multi-window burn-rate paging (SYNTHETIC 30 days, SLO 99.5 %)")
    spent = np.cumsum(bad) / (budget * total.sum())
    axes[1].plot(days, spent * 100, color=SERIES[2])
    axes[1].fill_between(days, 0, 100, where=page, color=STATUS["critical"], alpha=0.25, step="mid",
                         label="paging")
    axes[1].set_ylabel("budget spent (%)")
    axes[1].set_xlabel("day")
    axes[1].legend(loc="upper left")
    axes[1].annotate("4-minute blip: no page", (20.2, spent[blip.argmax()] * 100), xytext=(21.5, 12),
                     arrowprops={"arrowstyle": "->", "color": INK["muted"]}, color=INK["secondary"], fontsize=9)
    axes[1].annotate(f"3-hour partial outage: paged {int(page.sum())} min", (12.45, 30), xytext=(1.0, 60),
                     arrowprops={"arrowstyle": "->", "color": INK["muted"]}, color=INK["secondary"], fontsize=9)
    axes[1].set_ylim(0, 100)
    paged_minutes = int(page.sum())
    ROWS.append({"figure": "burn_rate", "series": "paged_minutes", "x": "", "y": paged_minutes})
    ROWS.append({"figure": "burn_rate", "series": "budget_spent_pct_day30", "x": "", "y": round(spent[-1] * 100, 1)})
    ROWS.append({"figure": "burn_rate", "series": "page_during_blip", "x": "", "y": bool(page[blip].any())})
    save(fig, HERE / "burn_rate.svg")


def main() -> None:
    apply()
    events, metrics_text = replay_results()
    fig_duration_vs_samples(events)
    fig_buckets(metrics_text)
    fig_percentile_averaging()
    fig_burn_rate()
    with (HERE / "figure_data.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["figure", "series", "x", "y"])
        w.writeheader()
        w.writerows(ROWS)
    for r in ROWS:
        if r["figure"] in ("percentile_averaging", "burn_rate"):
            print(r)


if __name__ == "__main__":
    main()
