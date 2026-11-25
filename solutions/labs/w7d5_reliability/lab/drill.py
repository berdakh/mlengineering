"""Failure-injection drill against a REAL server process on 127.0.0.1 (one server per scenario).

    python drill.py [--raw ../../../data/raw/skab] [--out drill_log]      # from the lab directory

For each scenario: start uvicorn with FLOWGUARD_FAULTS / FLOWGUARD_* settings, wait for /healthz,
replay one SKAB test experiment (valve1/13) in chunks of 300 values, record status codes, the
`degraded`/`reason` fields, out-of-support counts and client-side latency, scrape /metrics, stop the
server. Writes <out>.json and <out>.md. The server is always stopped, also on errors.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import httpx
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "src"))

from flowguard.client import RetryingClient, RetryPolicy  # noqa: E402
from flowguard.data import load_raw  # noqa: E402

EXPERIMENT = "valve1/13"
CHUNK = 300
SCENARIOS = [
    {"name": "normal", "env": {}},
    {"name": "units_bug", "env": {}, "scale": 60.0,
     "note": "client sends L/h instead of L/min (x60)"},
    {"name": "model_error", "env": {"FLOWGUARD_FAULTS": "model_error"}},
    {"name": "nan_scores", "env": {"FLOWGUARD_FAULTS": "nan_scores"}},
    {"name": "slow_model", "env": {"FLOWGUARD_FAULTS": "slow_model=1.0", "FLOWGUARD_DEADLINE_S": "0.25"}},
    {"name": "bundle_corrupt", "env": {"FLOWGUARD_FAULTS": "bundle_corrupt"}},
    {"name": "overload", "env": {"FLOWGUARD_FAULTS": "slow_model=0.3", "FLOWGUARD_MAX_INFLIGHT": "1",
                                 "FLOWGUARD_DEADLINE_S": "1.0"}, "concurrency": 4,
     "note": "4 concurrent clients, bulkhead of 1, retrying client honouring Retry-After"},
]


def default_raw() -> str:
    """data/raw/skab of the repository this lab lives in (works for lessons/ and solutions/ copies)."""
    for parent in HERE.parents:
        if (parent / "data" / "raw" / "skab").is_dir():
            return str(parent / "data" / "raw" / "skab")
    return "data/raw/skab"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class Server:
    def __init__(self, env: dict) -> None:
        self.port = free_port()
        full_env = {**os.environ, "PYTHONPATH": str(HERE / "src"), "FLOWGUARD_MODEL_DIR": str(HERE / "bundle"),
                    "FLOWGUARD_SETTINGS": str(HERE / "configs" / "service.toml"), **env}
        self.proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "--factory", "flowguard.api:app_from_env",
             "--host", "127.0.0.1", "--port", str(self.port), "--log-level", "warning"],
            env=full_env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        self.url = f"http://127.0.0.1:{self.port}"

    def __enter__(self) -> "Server":
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline:
            try:
                if httpx.get(self.url + "/healthz", timeout=0.5).status_code == 200:
                    return self
            except httpx.TransportError:
                time.sleep(0.1)
        self.stop()
        raise RuntimeError("server did not become healthy")

    def stop(self) -> None:
        if self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                self.proc.wait()

    def __exit__(self, *exc) -> None:
        self.stop()


def requests_for(x: np.ndarray, n_burn: int, scale: float) -> list[dict]:
    burn = (x[:n_burn] * scale).tolist()
    return [{"burn_in": burn, "values": (x[i:i + CHUNK] * scale).tolist()} for i in range(0, len(x), CHUNK)]


def run_scenario(sc: dict, x: np.ndarray, n_burn: int) -> dict:
    bodies = requests_for(x, n_burn, sc.get("scale", 1.0))
    record = {"name": sc["name"], "note": sc.get("note", ""), "faults": sc["env"].get("FLOWGUARD_FAULTS", ""),
              "requests": len(bodies), "statuses": {}, "reasons": {}, "out_of_support_values": 0,
              "alarms": 0, "latency_ms": [], "attempts": 0, "retries_after_429": 0}
    with Server(sc["env"]) as server:
        ready = httpx.get(server.url + "/readyz", timeout=2)
        record["readyz"] = {"status_code": ready.status_code, "body": ready.json()}
        record["healthz"] = httpx.get(server.url + "/healthz", timeout=2).status_code
        lock = threading.Lock()

        def worker(chunk: list[dict]) -> None:
            with RetryingClient(server.url, policy=RetryPolicy(max_attempts=8, base_delay=0.1, max_delay=2.0),
                                timeout=10.0) as client:
                for body in chunk:
                    t0 = time.perf_counter()
                    r = client.post_json("/predict", body)
                    ms = (time.perf_counter() - t0) * 1000
                    data = r.json()
                    with lock:
                        record["latency_ms"].append(ms)
                        record["statuses"][str(r.status_code)] = record["statuses"].get(str(r.status_code), 0) + 1
                        if r.status_code == 200:
                            reason = data["reason"] if data["degraded"] else "none"
                            record["reasons"][reason] = record["reasons"].get(reason, 0) + 1
                            record["out_of_support_values"] += len(data["out_of_support"])
                            record["alarms"] += sum(data["above_threshold"])
                        record["attempts"] += len(client.log)
                        record["retries_after_429"] += sum(1 for e in client.log if e["status"] == 429)
                        client.log.clear()

        n = sc.get("concurrency", 1)
        threads = [threading.Thread(target=worker, args=(bodies[i::n],)) for i in range(n)]
        t0 = time.perf_counter()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        record["wall_s"] = time.perf_counter() - t0
        record["metrics"] = [ln for ln in httpx.get(server.url + "/metrics", timeout=2).text.splitlines()
                             if not ln.startswith("flowguard_requests_total")]
    record["server_exit_code"] = server.proc.returncode
    lat = np.array(record.pop("latency_ms"))
    record["latency_ms"] = {"p50": float(np.percentile(lat, 50)), "p95": float(np.percentile(lat, 95)),
                            "max": float(lat.max())}
    return record


def to_markdown(results: list[dict]) -> str:
    lines = [f"# Drill log: {EXPERIMENT}, {results[0]['requests']} requests of up to {CHUNK} values per scenario",
             "", "Generated by `drill.py`; real server processes on 127.0.0.1, stopped after each scenario.", "",
             "| Scenario | Injected | /readyz | /healthz | Statuses | Degraded reasons | Out-of-support values | "
             "Alarms | Attempts | p50 ms | p95 ms |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        st = ", ".join(f"{v}× {k}" for k, v in sorted(r["statuses"].items()))
        rs = ", ".join(f"{v}× {k}" for k, v in sorted(r["reasons"].items()))
        lines.append(f"| {r['name']} | {r['faults'] or r['note'] or '-'} | {r['readyz']['status_code']} | "
                     f"{r['healthz']} | {st} | {rs} | {r['out_of_support_values']} | {r['alarms']} | {r['attempts']} | "
                     f"{r['latency_ms']['p50']:.1f} | {r['latency_ms']['p95']:.1f} |")
    lines += ["", "Metrics scraped at the end of each scenario (request counters omitted):", ""]
    for r in results:
        lines += [f"* **{r['name']}**: " + ("; ".join(f"`{m}`" for m in r["metrics"]) or "(none)")]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--raw", default=default_raw())
    ap.add_argument("--out", default=str(HERE / "results" / "drill_log"))
    ap.add_argument("--only", nargs="*", help="run only these scenario names")
    args = ap.parse_args()
    from flowguard.bundle import load_bundle
    n_burn = load_bundle(HERE / "bundle").n_burn_in
    tidy = load_raw(args.raw)
    x = tidy[tidy["experiment_id"] == EXPERIMENT].sort_values("t")["flow_rate"].to_numpy(dtype=float)
    results = []
    for sc in SCENARIOS:
        if args.only and sc["name"] not in args.only:
            continue
        r = run_scenario(sc, x, n_burn)
        print(f"{r['name']:15s} readyz {r['readyz']['status_code']} statuses {r['statuses']} reasons {r['reasons']} "
              f"oos {r['out_of_support_values']} attempts {r['attempts']} p50 {r['latency_ms']['p50']:.1f} ms")
        results.append(r)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".json").write_text(json.dumps(results, indent=2) + "\n")
    out.with_suffix(".md").write_text(to_markdown(results))
    print(f"wrote {out.with_suffix('.md')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
