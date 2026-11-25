"""Measure the flowguard API under open-loop load (given; uses your loadtest.py).

    python labs/w6d4_latency_resources/lab/measure_service.py --workers 1 --rates 10 40 80 \
        --duration 20 --out labs/w6d4_latency_resources/lab/results/workers1.json

Starts uvicorn on 127.0.0.1 (a free port, never a public interface) as a child process group, waits for
/readyz, sends each rate for --duration seconds after a warm-up, records latency percentiles, errors and
the server's resident memory (sum of VmRSS over the process group, read from /proc; Linux only), and
ALWAYS stops the server on exit, including on Ctrl-C. The request body is the first --batch samples
of real SKAB test experiment valve1/13 if the data has been downloaded (python project/get_skab.py),
otherwise a SYNTHETIC run with the same shape. The load generator runs on the same machine as the
server and competes with it for CPU; on a shared or small machine, say so when you report numbers.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import tomllib

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "src"))

from loadtest import compare_to_budget, run_open_loop, summarise, write_report  # noqa: E402

REPO_ROOT = next((p for p in HERE.parents if (p / "project" / "get_skab.py").is_file()), None)
MODEL_DIR = HERE / "models" / "flowguard-z" / "1.0.0"
SENSORS = {"accelerometer1_rms": 0.21, "accelerometer2_rms": 0.27, "current": 1.9, "pressure": 0.3,
           "temperature": 80.0, "thermocouple": 25.0, "voltage": 230.0, "flow_rate": 32.0}


def request_body(batch: int) -> tuple[bytes, str]:
    raw = REPO_ROOT / "data" / "raw" / "skab" if REPO_ROOT else None
    if raw and (raw / "valve1" / "13.csv").is_file():
        from flowguard.data import SENSOR_COLUMNS, load_experiment
        run = load_experiment(raw / "valve1" / "13.csv").head(batch)
        samples = [{"timestamp": r["datetime"].isoformat(), **{c: float(r[c]) for c in SENSOR_COLUMNS}}
                   for r in run.to_dict("records")]
        source = f"real SKAB valve1/13, first {len(samples)} samples"
    else:
        start = datetime(2026, 3, 1, 10)
        samples = [{"timestamp": (start + timedelta(seconds=i)).isoformat(), **SENSORS} for i in range(batch)]
        source = f"SYNTHETIC constant run, {batch} samples"
    return json.dumps({"machine_id": "loadtest", "samples": samples}).encode(), source


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def group_rss_mb(pgid: int) -> float:
    total_kb = 0
    for d in Path("/proc").iterdir():
        if not d.name.isdigit():
            continue
        try:
            stat = (d / "stat").read_text()
            if int(stat.rsplit(")", 1)[1].split()[2]) != pgid:
                continue
            for line in (d / "status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    total_kb += int(line.split()[1])
        except (OSError, ValueError, IndexError):
            continue
    return total_kb / 1024


def start_server(port: int, workers: int, extra_env: dict, server_args: list[str] = (),
                 launcher: str = "uvicorn") -> subprocess.Popen:
    env = dict(os.environ, PYTHONPATH=str(HERE / "src"), FLOWGUARD_MODEL_DIR=str(MODEL_DIR), **extra_env)
    if launcher == "serve":   # serve.py: same app, listening socket created with IPPROTO_TCP (TCP_NODELAY)
        cmd = [sys.executable, str(HERE / "serve.py"), "--host", "127.0.0.1", "--port", str(port),
               "--workers", str(workers), *server_args]
    else:
        cmd = [sys.executable, "-m", "uvicorn", "--factory", "flowguard.api:create_app_from_env", "--host",
               "127.0.0.1", "--port", str(port), "--workers", str(workers), "--log-level", "warning", *server_args]
    return subprocess.Popen(cmd, env=env, start_new_session=True,
                            stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)


def stop_server(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        os.killpg(proc.pid, signal.SIGKILL)
        proc.wait(timeout=5)
    except ProcessLookupError:
        pass


def wait_ready(base: str, proc: subprocess.Popen, timeout: float = 60.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError(f"server exited early: {proc.stderr.read()[-2000:]}")
        try:
            if httpx.get(f"{base}/readyz", timeout=1.0).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    raise RuntimeError("server not ready in time")


async def measure(base: str, body: bytes, rates: list[float], duration: float, warmup: float,
                  timeout: float) -> list[tuple[float, list[dict]]]:
    limits = httpx.Limits(max_connections=2000, max_keepalive_connections=2000)
    async with httpx.AsyncClient(base_url=base, timeout=timeout, limits=limits) as client:
        async def send() -> int:
            r = await client.post("/predict", content=body, headers={"Content-Type": "application/json"})
            return r.status_code
        for _ in range(20):  # warm the server and the connection pool
            await send()
        out = []
        for rate in rates:
            out.append((rate, await run_open_loop(send, rate, duration + warmup)))
        return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--rates", type=float, nargs="+", default=[10, 40, 80])
    ap.add_argument("--duration", type=float, default=20.0, help="measured seconds per rate")
    ap.add_argument("--warmup", type=float, default=3.0, help="seconds per rate excluded from statistics")
    ap.add_argument("--batch", type=int, default=600, help="samples per request")
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--budget", default=str(HERE / "budget.toml"))
    ap.add_argument("--env", nargs="*", default=[], help="extra server env vars, e.g. OMP_NUM_THREADS=1")
    ap.add_argument("--launcher", choices=["uvicorn", "serve"], default="uvicorn",
                    help="uvicorn: the uvicorn command line; serve: serve.py (sets TCP_NODELAY with N workers)")
    ap.add_argument("--server-arg", action="append", default=[],
                    help="extra uvicorn argument, repeatable, e.g. --server-arg=--http=h11")
    ap.add_argument("--keep-latencies", action="store_true", help="store every successful request's latency")
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    budget = tomllib.loads(Path(args.budget).read_text())["budget"]
    body, source = request_body(args.batch)
    extra_env = dict(kv.split("=", 1) for kv in args.env)
    port = free_port()
    base = f"http://127.0.0.1:{port}"
    proc = start_server(port, args.workers, extra_env, args.server_arg, args.launcher)
    runs = []
    try:
        wait_ready(base, proc)
        rss_idle = group_rss_mb(proc.pid)
        results = asyncio.run(measure(base, body, args.rates, args.duration, args.warmup, args.timeout))
        rss_after = group_rss_mb(proc.pid)
        for rate, records in results:
            summary = summarise(records, warmup_s=args.warmup)
            check = compare_to_budget(summary, budget)
            run = {"target_rps": rate, "duration_s": args.duration, "summary": summary, "budget": check}
            if args.keep_latencies:
                first = min(r["intended"] for r in records)
                run["latencies_ms"] = [round(1000 * r["latency"], 3) for r in records
                                       if r["intended"] >= first + args.warmup and r["status"] == 200]
            runs.append(run)
            print(f"{args.launcher:<7} workers={args.workers} rate={rate:>5.0f}/s  sent={summary['n_sent']:>5}  "
                  f"p50={summary['p50_ms']:7.1f}  p95={summary['p95_ms']:7.1f}  p99={summary['p99_ms']:7.1f} ms  "
                  f"errors={summary['error_rate']:.3f}  thr={summary['throughput_rps']:6.1f}/s  "
                  f"late={summary['late_starts']}  budget={'OK' if check['ok'] else 'MISSED'}", flush=True)
    finally:
        stop_server(proc)
    meta = {"workers": args.workers, "body": source, "body_bytes": len(body), "batch": args.batch,
            "warmup_s": args.warmup, "server_rss_mb_idle": round(rss_idle, 1),
            "server_rss_mb_after": round(rss_after, 1), "cpus": os.cpu_count(), "env": extra_env,
            "server_args": args.server_arg, "launcher": args.launcher,
            "load_average_at_end": os.getloadavg(), "budget": budget}
    print(f"server RSS {rss_idle:.0f} MB idle, {rss_after:.0f} MB after load ({args.workers} worker(s)); "
          f"{source}")
    write_report(args.out, runs, meta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
