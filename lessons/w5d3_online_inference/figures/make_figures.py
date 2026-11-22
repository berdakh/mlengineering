"""Regenerate every figure of lesson w5d3.

    python project/get_skab.py                                      # once
    python lessons/w5d3_online_inference/figures/make_figures.py    # about 15 s

Figures 1 and 4 are SYNTHETIC. Figures 2 and 3 use REAL SKAB test experiments and the REFERENCE
streaming implementation (solutions tree), replayed sample by sample; latency depends on the host and
its load. The plotted numbers are written to figure_data.csv. matplotlib is needed only here.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REFERENCE_LAB = ROOT / "solutions" / "lessons" / "w5d3_online_inference" / "lab"
REFERENCE_CHALLENGE = ROOT / "solutions" / "lessons" / "w5d3_online_inference" / "challenge"
sys.path[:0] = [str(ROOT), str(REFERENCE_LAB / "src"), str(HERE.parent / "example")]

from tools.figstyle import INK, SERIES, STATUS, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402

from flowguard.bundle import load_bundle  # noqa: E402
from flowguard.data import load_raw  # noqa: E402
from flowguard.splits import load_splits  # noqa: E402
from flowguard.streaming import StreamScorer  # noqa: E402
from welford_demo import naive, shifted, welford  # noqa: E402

COLOR = {"naive": SERIES[1], "shifted": SERIES[2], "welford": SERIES[0]}
records: list[dict] = []


def fig_cancellation() -> None:
    rng = np.random.default_rng(20261122)
    noise = rng.normal(0.0, 0.5, 10_000)
    offsets = 10.0 ** np.arange(1, 10)
    errs = {k: [] for k in COLOR}
    for off in offsets:
        xs = (off + noise).tolist()
        ref = float(np.var(np.array(xs)))
        for name, fn in (("naive", naive), ("shifted", shifted), ("welford", welford)):
            e = max(abs(fn(xs) - ref) / ref, 1e-17)
            errs[name].append(e)
            records.append({"figure": "cancellation", "offset": off, "method": name, "rel_error": e})
    fig, ax = plt.subplots(figsize=(7.2, 3.8))
    for name, values in errs.items():
        ax.loglog(offsets, values, marker="o", color=COLOR[name], label=name)
        ax.annotate(name, (offsets[-1], values[-1]), xytext=(6, 0), textcoords="offset points",
                    va="center", color=INK["secondary"])
    ax.axhline(1e-9, color=INK["muted"], linewidth=1, linestyle="--")
    ax.text(12, 2.5e-10, "parity tolerance used in the checks (1e-9)", color=INK["secondary"], fontsize=8)
    ax.set_xlabel("offset added to a signal with SD 0.5")
    ax.set_ylabel("relative error of the variance")
    ax.set_title("Naive sums of squares collapse at large offsets; Welford degrades slowly (SYNTHETIC)")
    ax.set_xlim(5, 1e11)
    ax.legend(loc="upper left")
    save(fig, HERE / "cancellation.svg")


def replay_test_set():
    tidy = load_raw(ROOT / "data" / "raw" / "skab")
    detector, _ = load_bundle(REFERENCE_LAB / "models" / "flowguard-z" / "1.0.0")
    manifest = load_splits(REFERENCE_LAB / "splits" / "v2.json")
    runs, latencies = {}, []
    for eid in sorted(manifest["test"]):
        run = tidy[tidy["experiment_id"] == eid].sort_values("t").reset_index(drop=True)
        scorer = StreamScorer(detector, machine_id=eid)
        scores = []
        for row in run.to_dict("records"):
            t0 = time.perf_counter_ns()
            r = scorer.update(row)
            latencies.append((time.perf_counter_ns() - t0) / 1e3)
            scores.append(np.nan if r.score is None else r.score)
        runs[eid] = (run, np.array(scores))
    return detector, runs, np.array(latencies)


def fig_stream(detector, runs, eid: str = "valve1/13") -> None:
    run, scores = runs[eid]
    t = np.arange(len(run))
    anomalous = run["anomaly"].to_numpy() == 1
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(7.6, 5.0), sharex=True)
    for ax in (ax1, ax2):
        ax.axvspan(0, detector.n_burn, color=INK["grid"], alpha=0.8, linewidth=0)
        on = np.flatnonzero(np.diff(np.r_[0, anomalous.astype(int), 0]) == 1)
        off = np.flatnonzero(np.diff(np.r_[0, anomalous.astype(int), 0]) == -1)
        for a, b in zip(on, off):
            ax.axvspan(a, b, color=STATUS["warning"], alpha=0.18, linewidth=0)
    ax1.plot(t, run["flow_rate"], color=SERIES[0], linewidth=1.2)
    ax1.set_ylabel("flow rate (L/min)")
    ax1.set_title(f"{eid}: warm-up, then one score per sample (REAL SKAB, test experiment)")
    ax2.plot(t, scores, color=SERIES[0], linewidth=1.2)
    ax2.axhline(detector.threshold, color=STATUS["critical"], linewidth=1.2, linestyle="--")
    ax2.text(len(t) * 0.01 + detector.n_burn, detector.threshold * 1.15,
             f"threshold {detector.threshold:.2f}", fontsize=8, color=INK["secondary"])
    ax2.set_yscale("symlog", linthresh=10)
    ax2.text(detector.n_burn / 2, 3, "warm-up:\nno score", ha="center", va="center", fontsize=8,
             color=INK["secondary"])
    ax2.set_ylabel("|z| (symlog)")
    ax2.set_xlabel("sample (1 per second); shaded orange = labelled anomaly")
    save(fig, HERE / "stream_valve1_13.svg")
    records.append({"figure": "stream", "experiment": eid, "rows": len(run),
                    "exceedances": int(np.nansum(scores >= detector.threshold))})


def fig_latency(lat_us: np.ndarray) -> None:
    p50, p95, p99 = np.percentile(lat_us, [50, 95, 99])
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    bins = np.logspace(np.log10(max(lat_us.min(), 0.5)), np.log10(lat_us.max()), 60)
    ax.hist(lat_us, bins=bins, color=SERIES[0], edgecolor=INK["surface"], linewidth=0.5)
    ax.set_xscale("log")
    for value, name in ((p50, "p50"), (p95, "p95"), (p99, "p99")):
        ax.axvline(value, color=INK["primary"], linewidth=1, linestyle=":")
        ax.text(value * 1.08, ax.get_ylim()[1] * 0.9, f"{name} {value:.1f} µs", fontsize=8,
                color=INK["secondary"], rotation=90, va="top")
    ax.set_xlabel("time per StreamScorer.update call (µs, log scale)")
    ax.set_ylabel("samples")
    ax.set_title(f"{lat_us.size:,} updates over the 7 test experiments (REAL SKAB; host-dependent)")
    save(fig, HERE / "update_latency.svg")
    records.append({"figure": "latency", "n": int(lat_us.size), "p50_us": p50, "p95_us": p95, "p99_us": p99,
                    "max_us": float(lat_us.max())})


def fig_hysteresis() -> None:
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "reference_hysteresis", REFERENCE_CHALLENGE / "src" / "flowguard" / "hysteresis.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    hysteresis_batch = module.hysteresis_batch
    seq = np.array([0, 0, 1, 0, 1, 1, 1, 1, 1, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 0], dtype=bool)
    stream = hysteresis_batch(seq, 3, 2)
    backdated = stream.copy()
    for i in range(1, len(stream)):
        if stream[i] and not stream[i - 1]:
            j = i
            while j > 0 and seq[j - 1]:
                j -= 1
            backdated[j:i] = True
    fig, axes = plt.subplots(3, 1, figsize=(8.0, 3.8), sharex=True)
    panels = [(seq, "exceeds threshold", SERIES[3]),
              (stream, "streaming alarm (k=3, m=2)", SERIES[0]),
              (backdated, "offline rule, back-dated to run start", SERIES[1])]
    x = np.arange(len(seq))
    for ax, (values, label, color) in zip(axes, panels):
        ax.bar(x, values.astype(int), width=0.92, color=color)
        ax.set_yticks([])
        ax.set_ylim(0, 1.05)
        ax.grid(False)
        ax.text(-0.6, 0.5, label, ha="right", va="center", fontsize=9, color=INK["secondary"])
    fig.suptitle("A stream raises at the k-th exceedance; an offline rule can look back (SYNTHETIC)",
                 x=0.02, ha="left", fontweight="bold", fontsize=11)
    axes[-1].set_xlabel("sample")
    axes[-1].set_xticks(x)
    fig.subplots_adjust(left=0.30, top=0.88)
    save(fig, HERE / "hysteresis.svg")


def main() -> None:
    fig_cancellation()
    fig_hysteresis()
    detector, runs, lat = replay_test_set()
    fig_stream(detector, runs)
    fig_latency(lat)
    pd.DataFrame(records).to_csv(HERE / "figure_data.csv", index=False)
    for r in records:
        if r["figure"] != "cancellation":
            print(r)


if __name__ == "__main__":
    main()
