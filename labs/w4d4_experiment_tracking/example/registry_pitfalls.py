"""Worked example for w4d4: four ways a home-made experiment registry lies, each in a few lines.

    python labs/w4d4_experiment_tracking/example/registry_pitfalls.py      # under 5 seconds

Everything here is SYNTHETIC and self-contained (standard library, NumPy, pandas). It does not use
the lab package, so you can read it before writing any of the lab.
"""
from __future__ import annotations

import hashlib
import json
import statistics
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd


def section(title: str) -> None:
    print(f"\n=== {title}")


# ----------------------------------------------------------------------------- 1. identity
section("1. The same configuration, two different run ids")
a = {"model": {"alpha": 1.0, "kind": "ridge"}, "seed": 0}
b = {"seed": 0, "model": {"kind": "ridge", "alpha": 1.0}}          # same content, built in another order
naive = [hashlib.sha256(json.dumps(c).encode()).hexdigest()[:12] for c in (a, b)]
canonical = [hashlib.sha256(json.dumps(c, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:12]
             for c in (a, b)]
print(f"json.dumps(config)                 -> {naive[0]} vs {naive[1]}  (equal: {naive[0] == naive[1]})")
print(f"json.dumps(config, sort_keys=True) -> {canonical[0]} vs {canonical[1]}  (equal: {canonical[0] == canonical[1]})")
print("1.0 vs 1:", json.dumps({"alpha": 1.0}), "vs", json.dumps({"alpha": 1}),
      "- the canonical form still distinguishes int and float; keep config values typed consistently")

# ----------------------------------------------------------------------------- 2. disappearing rows
section("2. A results table that silently drops configurations")
index = pd.DataFrame([
    {"sweep": "ridge", "param.alpha": 0.1, "param.trees": np.nan, "seed": 0, "metric": 0.81},
    {"sweep": "ridge", "param.alpha": 0.1, "param.trees": np.nan, "seed": 1, "metric": 0.79},
    {"sweep": "forest", "param.alpha": np.nan, "param.trees": 200, "seed": 0, "metric": 0.84},
    {"sweep": "forest", "param.alpha": np.nan, "param.trees": 200, "seed": 1, "metric": 0.86},
])
keys = ["sweep", "param.alpha", "param.trees"]
print("groupby(keys):               ", index.groupby(keys)["metric"].mean().to_dict(), "  <- both sweeps gone")
print("groupby(keys, dropna=False): ", index.groupby(keys, dropna=False)["metric"].mean().round(2).to_dict())

# ----------------------------------------------------------------------------- 3. partial runs
section("3. 'metrics.json exists' is not 'the run finished'")
with tempfile.TemporaryDirectory() as tmp:
    runs = Path(tmp)
    for rid, finished in (("r1", True), ("r2", True), ("r3", False)):
        d = runs / rid
        d.mkdir()
        (d / "metrics.json").write_text(json.dumps({"ap": {"r1": 0.70, "r2": 0.72, "r3": 0.95}[rid]}))
        if finished:                                         # r3 crashed after writing an interim metric
            (d / "status.json").write_text(json.dumps({"status": "complete"}))
    by_metrics = [json.loads((d / "metrics.json").read_text())["ap"] for d in sorted(runs.iterdir())]
    by_status = [json.loads((d / "metrics.json").read_text())["ap"] for d in sorted(runs.iterdir())
                 if (d / "status.json").is_file()]
    print(f"mean over dirs with metrics.json: {np.mean(by_metrics):.3f}  (n = {len(by_metrics)})")
    print(f"mean over dirs with status.json : {np.mean(by_status):.3f}  (n = {len(by_status)})")

# ----------------------------------------------------------------------------- 4. how many seeds
section("4. How well do n seeds estimate the seed spread? (true sd = 0.020)")
rng = np.random.default_rng(0)
print("| seeds | median estimated sd | 10th-90th percentile of the estimate |")
print("|---|---|---|")
for n in (2, 3, 5, 10, 20):
    estimates = [statistics.stdev(rng.normal(0.80, 0.02, size=n)) for _ in range(20000)]
    lo, med, hi = np.percentile(estimates, [10, 50, 90])
    print(f"| {n} | {med:.4f} | {lo:.4f} - {hi:.4f} |")
