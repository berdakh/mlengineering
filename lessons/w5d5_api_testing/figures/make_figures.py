"""Regenerate every figure of lesson w5d5 from real runs. From the repository root:

    python lessons/w5d5_api_testing/figures/make_figures.py

Writes figures/*.svg and figures/figure_data.csv. Takes about a minute (the kill matrix runs the
mutation harness for five test suites). matplotlib is needed only here.
"""
from __future__ import annotations

import csv
import json
import shutil
import statistics
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
UNIT = HERE.parent
ROOT = UNIT.parents[1]
sys.path[:0] = [str(ROOT), str(UNIT / "checks"), str(UNIT / "example"), str(UNIT / "lab" / "service")]

from tools.figstyle import INK, SEQUENTIAL, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import ListedColormap  # noqa: E402

ROWS: list[dict] = []


def race_figure() -> None:
    import race_demo
    threads = (1, 2, 4, 8, 16)
    repeats = [race_demo.table(threads) for _ in range(3)]
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    for k, (label, col) in enumerate((("correct service", 1), ("buggy shared cache", 2))):
        vals = np.array([[row[col] for row in rep] for rep in repeats])
        ax.plot(threads, vals.mean(axis=0), marker="o", color=SERIES[k], label=label)
        ax.fill_between(threads, vals.min(axis=0), vals.max(axis=0), color=SERIES[k], alpha=0.15, linewidth=0)
        for t, v in zip(threads, vals.mean(axis=0)):
            ROWS.append({"figure": "race_fraction", "series": label, "x": t, "value": round(float(v), 3)})
        ax.annotate(label, (threads[-1], vals.mean(axis=0)[-1]), xytext=(6, 0), textcoords="offset points",
                    va="center", color=INK["secondary"], fontsize=9)
    ax.set_xscale("log", base=2)
    ax.set_xticks(threads, [str(t) for t in threads])
    ax.set_ylim(-0.03, 1.0)
    ax.set_xlabel("concurrent client threads")
    ax.set_ylabel("fraction of wrong responses")
    ax.set_title("A sequential test (1 thread) cannot see the shared-state bug")
    ax.legend(loc="upper left")
    save(fig, HERE / "race_fraction.svg")


def kill_matrix() -> None:
    import harness
    from bugs import BUGS
    sol = ROOT / "solutions" / "lessons" / "w5d5_api_testing"
    suites = {"starter (1 smoke test)": [UNIT / "lab" / "tests"],
              "happy path only": [sol / "mutants" / "happy_path_only" / "tests"],
              "status codes only": [sol / "mutants" / "status_codes_only" / "tests"],
              "sequential only": [sol / "lab" / "tests", "drop:test_concurrency.py"],
              "reference suite": [sol / "lab" / "tests"]}
    matrix = []
    for name, spec in suites.items():
        with tempfile.TemporaryDirectory() as tmp:
            tests = Path(tmp) / "tests"
            shutil.copytree(spec[0], tests, ignore=shutil.ignore_patterns("__pycache__"))
            for extra in spec[1:]:
                (tests / extra.split(":", 1)[1]).unlink()
            reference, runs = harness.grade(tests, UNIT / "checks" / "reference_pkg", BUGS)
        assert reference.passed, f"{name} does not pass on the correct service"
        killed = [1 if runs[b.name].failed_tests else 0 for b in BUGS]
        matrix.append(killed)
        for b, k in zip(BUGS, killed):
            ROWS.append({"figure": "kill_matrix", "series": name, "x": b.name, "value": k})
    m = np.array(matrix)
    fig, ax = plt.subplots(figsize=(8.6, 3.2))
    ax.imshow(m, cmap=ListedColormap([INK["grid"], SEQUENTIAL[4]]), aspect="auto", vmin=0, vmax=1)
    ax.set_yticks(range(len(suites)), [f"{n}  ({int(r.sum())}/{len(BUGS)})" for n, r in zip(suites, m)])
    ax.set_xticks(range(len(BUGS)), [b.name.replace("_", " ") for b in BUGS], rotation=40, ha="right",
                  fontsize=8)
    ax.set_xticks(np.arange(-0.5, len(BUGS)), minor=True)
    ax.set_yticks(np.arange(-0.5, len(suites)), minor=True)
    ax.grid(which="minor", color=INK["surface"], linewidth=2)
    ax.grid(which="major", visible=False)
    ax.tick_params(which="minor", length=0)
    ax.set_title("Defects each suite kills (dark = test fails on the defective service)")
    save(fig, HERE / "kill_matrix.svg")


def latency_figure() -> None:
    from fastapi.testclient import TestClient

    from flowguard.api import create_app
    from flowguard.bundle import save_bundle
    from flowguard.scoring import ZScoreModel
    sizes = (1, 10, 100, 1000, 3600)
    rng = np.random.default_rng(0)
    p50, p95 = [], []
    with tempfile.TemporaryDirectory() as tmp:
        save_bundle(ZScoreModel("flow_rate", 100, 7.24, 30, 10, "lat-1"), Path(tmp) / "b")
        with TestClient(create_app(Path(tmp) / "b")) as client:
            for n in sizes:
                payload = {"burn_in": rng.normal(size=100).tolist(), "values": rng.normal(size=n).tolist()}
                for _ in range(20):
                    client.post("/predict", json=payload)            # warm-up
                times = []
                for _ in range(200):
                    t0 = time.perf_counter()
                    client.post("/predict", json=payload)
                    times.append((time.perf_counter() - t0) * 1000)
                p50.append(statistics.median(times))
                p95.append(float(np.percentile(times, 95)))
                ROWS.append({"figure": "predict_latency", "series": "p50_ms", "x": n, "value": round(p50[-1], 3)})
                ROWS.append({"figure": "predict_latency", "series": "p95_ms", "x": n, "value": round(p95[-1], 3)})
    fig, ax = plt.subplots(figsize=(6.4, 3.4))
    ax.plot(sizes, p50, marker="o", color=SERIES[0], label="median")
    ax.plot(sizes, p95, marker="o", color=SERIES[1], label="95th percentile")
    for label, ys in (("median", p50), ("95th percentile", p95)):
        ax.annotate(label, (sizes[-1], ys[-1]), xytext=(6, 0), textcoords="offset points", va="center",
                    color=INK["secondary"], fontsize=9)
    ax.set_xscale("log")
    ax.set_xticks(sizes, [f"{n:,}" for n in sizes])
    ax.set_ylim(0, max(p95) * 1.15)
    ax.set_xlabel("values per request")
    ax.set_ylabel("time per request, ms (in-process)")
    ax.set_title("Fixed per-request overhead dominates small batches")
    ax.legend(loc="upper left")
    save(fig, HERE / "predict_latency.svg")


if __name__ == "__main__":
    race_figure()
    latency_figure()
    kill_matrix()
    with (HERE / "figure_data.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["figure", "series", "x", "value"])
        writer.writeheader()
        writer.writerows(ROWS)
    for r in ROWS:
        if r["figure"] != "kill_matrix":
            print(r)
    print(json.dumps({s: sum(r["value"] for r in ROWS if r["figure"] == "kill_matrix" and r["series"] == s)
                      for s in dict.fromkeys(r["series"] for r in ROWS if r["figure"] == "kill_matrix")}))
