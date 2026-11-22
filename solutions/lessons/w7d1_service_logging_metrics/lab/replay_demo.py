"""Replay two real SKAB test experiments through a LOCAL flowguard server and look at the signals.

    python lessons/w7d1_service_logging_metrics/lab/replay_demo.py            # ~1 minute

What it does (given; you do not need to edit it, but read it):

1. Starts ``uvicorn`` for ``flowguard.api:create_app_from_env`` on 127.0.0.1 (a free port), with
   FLOWGUARD_LOG_FILE pointing at ``results/service.log``.
2. For each experiment, behaves like a plant client that re-sends the run so far every 60 samples
   (the API scores a run from the start of monitoring; w5d3 is the stateful alternative).
3. Sends a few bad requests on purpose: a sentinel value (-9999), a missing field, an unknown route,
   and one request whose X-Request-ID it chooses, so you can query it afterwards.
4. Scrapes ``/metrics`` into ``results/metrics.txt``, prints the golden signals computed from the log,
   and runs ``python -m flowguard.cli logs`` for the chosen request id.
5. Stops the server (also on Ctrl-C or error).

Serving requests is not a model decision, so replaying test experiments does not spend the test set.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import numpy as np

HERE = Path(__file__).resolve().parent
REPO_ROOT = next(p for p in HERE.parents if (p / "project" / "get_skab.py").is_file())
sys.path.insert(0, str(HERE / "src"))

from flowguard.data import SENSOR_COLUMNS, load_raw  # noqa: E402

EXPERIMENTS = ("valve1/13", "other/14")
STEP = 60
KNOWN_ID = "replay-demo-0001"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def body_for(run, n: int, machine_id: str) -> dict:
    rows = run.iloc[:n]
    return {"machine_id": machine_id, "samples": [
        {"timestamp": r["datetime"].isoformat(), **{c: float(r[c]) for c in SENSOR_COLUMNS}}
        for r in rows.to_dict("records")]}


def wait_ready(client: httpx.Client, timeout: float = 20.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            if client.get("/readyz").status_code == 200:
                return
        except httpx.TransportError:
            pass
        time.sleep(0.2)
    raise RuntimeError("server did not become ready")


def golden_signals(log_path: Path) -> dict:
    access = [json.loads(l) for l in log_path.read_text().splitlines()
              if l.startswith("{") and '"event":"access"' in l]
    pred = [e for e in access if e.get("route") == "/predict"]
    dur = np.array([e["duration_ms"] for e in pred if e["status"] == 200])
    span = (np.datetime64(access[-1]["ts"][:23]) - np.datetime64(access[0]["ts"][:23])) / np.timedelta64(1, "s")
    return {
        "requests (all routes)": len(access),
        "predict requests": len(pred),
        "traffic, predict req/s over the replay": round(len(pred) / max(span, 1e-9), 2),
        "errors: 4xx (client)": sum(400 <= e["status"] < 500 for e in pred),
        "errors: 5xx (server)": sum(e["status"] >= 500 for e in pred),
        "latency p50 ms (200s)": round(float(np.percentile(dur, 50)), 2),
        "latency p95 ms (200s)": round(float(np.percentile(dur, 95)), 2),
        "latency max ms (200s)": round(float(dur.max()), 2),
    }


def main() -> int:
    raw = REPO_ROOT / "data" / "raw" / "skab"
    try:
        tidy = load_raw(raw)
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    results = HERE / "results"
    results.mkdir(exist_ok=True)
    log_path = results / "service.log"
    log_path.write_text("")
    port = free_port()
    env = dict(os.environ, FLOWGUARD_MODEL_DIR=str(HERE / "models" / "flowguard-z" / "1.0.0"),
               FLOWGUARD_LOG_FILE=str(log_path), PYTHONPATH=str(HERE / "src"),
               OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "--factory", "flowguard.api:create_app_from_env",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning", "--no-access-log"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    try:
        with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=30) as client:
            wait_ready(client)
            for exp in EXPERIMENTS:
                run = tidy[tidy["experiment_id"] == exp].sort_values("t").reset_index(drop=True)
                for n in range(STEP, len(run) + STEP, STEP):
                    client.post("/predict", json=body_for(run, min(n, len(run)), exp))
            # deliberate bad requests
            bad = body_for(tidy[tidy["experiment_id"] == EXPERIMENTS[0]].sort_values("t"), 120, "valve1/13")
            bad["samples"][50]["flow_rate"] = -9999.0
            client.post("/predict", json=bad)
            client.post("/predict", json={"machine_id": "valve1/13"})
            client.get("/predict/valve1/13")
            ok = body_for(tidy[tidy["experiment_id"] == EXPERIMENTS[0]].sort_values("t"), 600, "valve1/13")
            r = client.post("/predict", json=ok, headers={"X-Request-ID": KNOWN_ID})
            print(f"chosen request: status {r.status_code}, X-Request-ID {r.headers.get('x-request-id')}")
            metrics = client.get("/metrics").text
            (results / "metrics.txt").write_text(metrics)
            rss = None
            status_file = Path(f"/proc/{server.pid}/status")
            if status_file.is_file():
                rss = next((l.split()[1] for l in status_file.read_text().splitlines() if l.startswith("VmRSS")), None)
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
    print("\n== golden signals from results/service.log ==")
    for k, v in golden_signals(log_path).items():
        print(f"  {k:40s} {v}")
    if rss:
        print(f"  {'saturation: server RSS at the end (kB)':40s} {rss}")
    print("\n== selected lines of results/metrics.txt ==")
    for line in metrics.splitlines():
        if line.startswith(("flowguard_http_requests_total", "flowguard_model_info", "flowguard_http_requests_in_flight",
                            'flowguard_http_request_duration_seconds_bucket{route="/predict",le="0.05"}',
                            'flowguard_http_request_duration_seconds_count{route="/predict"}',
                            "flowguard_predicted_samples_total")):
            print("  " + line)
    print(f"\n== python -m flowguard.cli logs --file results/service.log --request-id {KNOWN_ID} ==")
    subprocess.run([sys.executable, "-m", "flowguard.cli", "logs", "--file", str(log_path),
                    "--request-id", KNOWN_ID], env=env, check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
