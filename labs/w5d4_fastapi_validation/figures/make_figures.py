"""Regenerate the data figures of lesson w5d4.

    python project/get_skab.py                                        # once
    python labs/w5d4_fastapi_validation/figures/make_figures.py    # about 30 s

Uses the REFERENCE API (solutions tree) in process through TestClient (no network: these timings
exclude TCP, TLS and the uvicorn event loop), the committed model bundle, and REAL SKAB rows of test
experiment valve1/13, tiled with increasing timestamps to make batches up to 5,000 samples.
Timings depend on the host and its load. Values are written to figure_data.csv.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
REFERENCE_LAB = ROOT / "solutions" / "labs" / "w5d4_fastapi_validation" / "lab"
sys.path[:0] = [str(ROOT), str(REFERENCE_LAB / "src")]

from tools.figstyle import INK, SERIES, apply, save  # noqa: E402

apply()
import matplotlib.pyplot as plt  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from flowguard.api import create_app  # noqa: E402
from flowguard.bundle import load_bundle  # noqa: E402
from flowguard.data import SENSOR_COLUMNS, load_raw  # noqa: E402
from flowguard.schemas import PredictRequest, PredictResponse, SampleResult  # noqa: E402

MODEL = REFERENCE_LAB / "models" / "flowguard-z" / "1.0.0"
SIZES = [1, 10, 100, 500, 1000, 2000, 5000]
REPEATS = 15
records: list[dict] = []


def samples_of(n: int) -> list[dict]:
    tidy = load_raw(ROOT / "data" / "raw" / "skab")
    run = tidy[tidy["experiment_id"] == "valve1/13"].sort_values("t")
    rows = [{c: float(r[c]) for c in SENSOR_COLUMNS} for r in run.to_dict("records")]
    start = pd.Timestamp(run["datetime"].iloc[0])
    return [{"timestamp": (start + pd.Timedelta(seconds=i)).isoformat(), **rows[i % len(rows)]} for i in range(n)]


def fig_latency(all_samples: list[dict]) -> None:
    with TestClient(create_app(MODEL)) as client:
        for n in SIZES:
            body = json.dumps({"machine_id": "valve1-13", "samples": all_samples[:n]})
            times = []
            for _ in range(REPEATS):
                t0 = time.perf_counter()
                r = client.post("/predict", content=body, headers={"content-type": "application/json"})
                times.append((time.perf_counter() - t0) * 1e3)
                assert r.status_code == 200
            med = float(np.median(times))
            records.append({"figure": "latency", "n": n, "median_ms": med, "us_per_sample": med * 1e3 / n,
                            "p90_ms": float(np.percentile(times, 90))})
    df = pd.DataFrame([r for r in records if r["figure"] == "latency"])
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(8.4, 3.6))
    ax1.loglog(df["n"], df["median_ms"], marker="o", color=SERIES[0])
    ax1.set_xlabel("samples per request")
    ax1.set_ylabel("median ms per request")
    ax1.set_title("Per request")
    ax2.loglog(df["n"], df["us_per_sample"], marker="o", color=SERIES[0])
    ax2.set_xlabel("samples per request")
    ax2.set_ylabel("µs per sample")
    ax2.set_title("Per sample (amortised)")
    for ax, col in ((ax1, "median_ms"), (ax2, "us_per_sample")):
        for _, row in df.iloc[[0, -1]].iterrows():
            ax.annotate(f"{row[col]:.3g}", (row["n"], row[col]), xytext=(4, 6), textcoords="offset points",
                        fontsize=8, color=INK["secondary"])
    fig.suptitle("POST /predict in process: fixed cost per request, then cost per sample (REAL SKAB rows; host-dependent)",
                 x=0.02, ha="left", fontsize=10, fontweight="bold")
    fig.subplots_adjust(top=0.82, wspace=0.35)
    save(fig, HERE / "predict_latency.svg")


def fig_breakdown(all_samples: list[dict], n: int = 1140) -> None:
    detector, _ = load_bundle(MODEL)
    body = json.dumps({"machine_id": "valve1-13", "samples": all_samples[:n]})
    stages = {"parse + validate (pydantic)": [], "objects -> DataFrame": [], "detector.score_batch": [],
              "build + serialise response": []}
    for _ in range(REPEATS):
        t0 = time.perf_counter()
        req = PredictRequest.model_validate_json(body)
        t1 = time.perf_counter()
        frame = pd.DataFrame([s.model_dump() for s in req.samples]).rename(columns={"timestamp": "datetime"})
        t15 = time.perf_counter()
        scores = detector.score_batch(frame)
        t2 = time.perf_counter()
        results = [SampleResult(timestamp=s.timestamp, score=None if np.isnan(v) else float(v),
                                status="warming_up" if np.isnan(v) else "ok",
                                exceeds_threshold=None if np.isnan(v) else bool(v >= detector.threshold))
                   for s, v in zip(req.samples, scores)]
        PredictResponse(request_id="x", model_version=detector.version, machine_id=req.machine_id,
                        threshold=detector.threshold, n_samples=len(results), results=results).model_dump_json()
        t3 = time.perf_counter()
        for key, (a, b) in zip(stages, ((t0, t1), (t1, t15), (t15, t2), (t2, t3))):
            stages[key].append((b - a) * 1e3)
    med = {k: float(np.median(v)) for k, v in stages.items()}
    for k, v in med.items():
        records.append({"figure": "breakdown", "n": n, "stage": k, "median_ms": v})
    fig, ax = plt.subplots(figsize=(7.2, 3.2))
    names = list(med)[::-1]
    ax.barh(names, [med[k] for k in names], color=SERIES[0], height=0.55)
    for i, k in enumerate(names):
        ax.text(med[k], i, f"  {med[k]:.2f} ms", va="center", fontsize=9, color=INK["secondary"])
    ax.set_xlabel("median ms (one run of 1,140 samples)")
    ax.set_title("Where a /predict request spends its time: the model is the smallest part (host-dependent)",
                 fontsize=10)
    ax.set_xlim(0, max(med.values()) * 1.3)
    save(fig, HERE / "latency_breakdown.svg")


def main() -> None:
    all_samples = samples_of(max(SIZES))
    fig_latency(all_samples)
    fig_breakdown(all_samples)
    pd.DataFrame(records).to_csv(HERE / "figure_data.csv", index=False)
    print(pd.DataFrame(records).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
