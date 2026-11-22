"""Write the smoke-test fixture: a SYNTHETIC request and the scores the shipped model must return.

    python <lab>/scripts/make_smoke_fixture.py        # writes smoke/request.json and smoke/expected.json

The request is SYNTHETIC (seeded random sensor values in the testbed's normal range, with a flow
drop injected at sample 220), so it can be committed; the real SKAB files are GPL-licensed and are
not redistributed. The expected scores come from loading ``models/flowguard-z/1.0.0`` in this
process and calling ``Detector.score_batch`` directly: the same code path the API must reproduce.
What a pass proves: the container starts, loads THIS model, and computes the same numbers as the
package does outside the container. It says nothing about detection quality.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "src"))

from flowguard.bundle import load_bundle  # noqa: E402
from flowguard.data import SENSOR_COLUMNS  # noqa: E402

N_SAMPLES = 300
FAULT_AT = 220
SEED = 6

NORMAL = {  # rough centre and spread of each sensor in normal SKAB operation (units as in the data dictionary)
    "accelerometer1_rms": (0.21, 0.005), "accelerometer2_rms": (0.27, 0.005), "current": (1.9, 0.3),
    "pressure": (0.3, 0.3), "temperature": (80.0, 0.5), "thermocouple": (25.0, 0.05),
    "voltage": (230.0, 2.0), "flow_rate": (125.0, 1.0),
}


def synthetic_request() -> dict:
    rng = np.random.default_rng(SEED)
    times = pd.date_range("2026-01-05 08:00:00", periods=N_SAMPLES, freq="1s")
    values = {c: rng.normal(mu, sd, N_SAMPLES) for c, (mu, sd) in NORMAL.items()}
    values["flow_rate"][FAULT_AT:] -= 30.0            # a valve closes: flow drops by 30 L/min
    samples = [{"timestamp": t.isoformat(), **{c: round(float(values[c][i]), 6) for c in SENSOR_COLUMNS}}
               for i, t in enumerate(times)]
    return {"machine_id": "smoke-test", "samples": samples}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--model-dir", default=str(HERE / "models" / "flowguard-z" / "1.0.0"))
    ap.add_argument("--out-dir", default=str(HERE / "smoke"))
    args = ap.parse_args(argv)
    detector, _ = load_bundle(args.model_dir)
    body = synthetic_request()
    frame = pd.DataFrame(body["samples"]).rename(columns={"timestamp": "datetime"})
    frame["datetime"] = pd.to_datetime(frame["datetime"])
    scores = detector.score_batch(frame)
    expected = {
        "model_version": detector.version,
        "threshold": detector.threshold,
        "scores": [None if np.isnan(s) else float(s) for s in scores],
        "exceeds_threshold": [None if np.isnan(s) else bool(s >= detector.threshold) for s in scores],
    }
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "request.json").write_text(json.dumps(body, indent=1) + "\n")
    (out / "expected.json").write_text(json.dumps(expected, indent=1) + "\n")
    n_scored = sum(s is not None for s in expected["scores"])
    n_exceed = sum(bool(e) for e in expected["exceeds_threshold"])
    print(f"wrote {out}/request.json ({N_SAMPLES} SYNTHETIC samples) and expected.json "
          f"({n_scored} scored, {n_exceed} above threshold {detector.threshold:.4f}, model {detector.version})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
