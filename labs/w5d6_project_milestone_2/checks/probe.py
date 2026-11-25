"""Run inside the project under test (PYTHONPATH=<project>/src, cwd=<project>). Prints one JSON object.

Computes the three paths independently of the project's own tests:
evaluation (flowguard.evaluation.experiment_scores), batch (the CLI, as a subprocess, CSV read back
exactly) and API (TestClient against create_app, values sent in chunks of at most 3600 per request).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

import flowguard
from flowguard.api import create_app
from flowguard.bundle import load_bundle
from flowguard.data import load_raw
from flowguard.evaluation import experiment_scores

model_dir, raw = sys.argv[1], sys.argv[2]
model = load_bundle(model_dir)
tidy = load_raw(raw)
evaluation = experiment_scores(model, tidy).set_index(["experiment_id", "t"])["score"].sort_index()

with tempfile.TemporaryDirectory() as tmp:
    out = Path(tmp) / "all.csv"
    proc = subprocess.run([sys.executable, "-m", "flowguard", "predict-batch", "--model", model_dir, "--raw", raw,
                           "--split", "all", "--out", str(out)], capture_output=True, text=True)
    batch_ok = proc.returncode == 0 and out.is_file()
    if batch_ok:
        frame = pd.read_csv(out, float_precision="round_trip")
        columns = list(frame.columns)
        batch = frame.set_index(["experiment_id", "t"])["score"].sort_index()
    else:
        columns, batch = [], None

api_scores = {}
with TestClient(create_app(model_dir)) as client:
    version = client.get("/version").json()
    for eid, group in tidy.groupby("experiment_id"):
        x = group.sort_values("t")[model.sensor].to_numpy(dtype=float)
        burn = x[: model.n_burn_in].tolist()
        scores = []
        for i in range(0, len(x), 3600):
            r = client.post("/predict", json={"burn_in": burn, "values": x[i:i + 3600].tolist()})
            scores += r.json()["scores"] if r.status_code == 200 else [float("nan")] * len(x[i:i + 3600])
        api_scores[eid] = scores
api = pd.concat({e: pd.Series(v, index=range(len(v))) for e, v in api_scores.items()}).sort_index()


def max_diff(a, b):
    if b is None or len(a) != len(b):
        return None
    return float(np.max(np.abs(a.to_numpy() - b.to_numpy())))


print(json.dumps({
    "package_version": flowguard.__version__,
    "api_version": version.get("package_version"),
    "batch_ok": batch_ok, "batch_stderr": proc.stderr[-500:], "batch_columns": columns,
    "rows": int(len(evaluation)),
    "eval_vs_batch": max_diff(evaluation, batch),
    "eval_vs_api": max_diff(evaluation, api),
}))
