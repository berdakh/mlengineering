"""Three-way parity on real data: evaluation vs batch CSV vs API, every row of every experiment.

    PYTHONPATH=src python scripts/parity_report.py --model models/current --raw data/raw/skab --out parity.json
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from flowguard import __version__
from flowguard.api import create_app
from flowguard.bundle import load_bundle, read_manifest
from flowguard.data import load_raw
from flowguard.evaluation import experiment_scores
from flowguard.inference import api_requests_for


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    model = load_bundle(args.model)
    tidy = load_raw(args.raw)
    evaluation = experiment_scores(model, tidy).set_index(["experiment_id", "t"])["score"].sort_index()
    with tempfile.TemporaryDirectory() as tmp:
        csv = Path(tmp) / "all.csv"
        subprocess.run([sys.executable, "-m", "flowguard", "predict-batch", "--model", args.model, "--raw", args.raw,
                        "--split", "all", "--out", str(csv)], check=True, capture_output=True)
        # float_precision="round_trip": the default parser is off by up to ~1 ulp on 17-digit values
        batch = pd.read_csv(csv, float_precision="round_trip").set_index(["experiment_id", "t"])["score"].sort_index()
    api_parts = {}
    with TestClient(create_app(args.model)) as client:
        version = client.get("/version").json()
        for eid in sorted(tidy["experiment_id"].unique()):
            scores = []
            for body in api_requests_for(model, tidy, eid):
                r = client.post("/predict", json=body)
                r.raise_for_status()
                scores += r.json()["scores"]
            api_parts[eid] = np.asarray(scores)
    api = pd.concat({e: pd.Series(v, index=range(len(v))) for e, v in api_parts.items()}).sort_index()
    api.index.names = ["experiment_id", "t"]
    result = {
        "rows": int(len(batch)), "experiments": int(tidy["experiment_id"].nunique()),
        "max_abs_diff_evaluation_vs_batch": float(np.max(np.abs(evaluation.to_numpy() - batch.to_numpy()))),
        "max_abs_diff_evaluation_vs_api": float(np.max(np.abs(evaluation.to_numpy() - api.to_numpy()))),
        "versions": {"package": __version__, "bundle": read_manifest(args.model)["package_version"],
                     "api": version["package_version"], "model": version["model_version"]},
    }
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
