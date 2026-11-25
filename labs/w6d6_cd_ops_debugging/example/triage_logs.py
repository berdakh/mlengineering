"""Worked example (w6d6): triage an incident from structured logs, before touching anything.

    python labs/w6d6_cd_ops_debugging/example/triage_logs.py            # SYNTHETIC log, generated
    python labs/w6d6_cd_ops_debugging/example/triage_logs.py FILE.log   # your own JSON-lines log

The SYNTHETIC log is from a different service than the lab's: a product-recommendation API that
calls a feature store. 40 minutes of traffic at about 5 requests per second; release `r2` goes out
at 10:20. Each line is one JSON object, like the lab's logs: ts, level, event, release, plus
event-specific fields. Generated with a fixed seed, so the output below is reproducible.

The method (lesson, section 2.4): look at what changed and when, compare before and after per
release, find the first error, and only then form hypotheses. The questions this script answers are
the first four you should ask of any incident:
  1. What changed, and when? (deploy events)
  2. Which release is answering, and how does each release behave? (error rate, latency)
  3. What is the first error after the change, and which error dominates?
  4. Is the effect everywhere or in a slice? (by endpoint)
"""
from __future__ import annotations

import json
import sys
import tempfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np


def generate(path: Path, seed: int = 7) -> None:
    rng = np.random.default_rng(seed)
    t, end = datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc), datetime(2026, 3, 10, 10, 40, tzinfo=timezone.utc)
    deploy = datetime(2026, 3, 10, 10, 20, tzinfo=timezone.utc)
    lines = [{"ts": t.isoformat(), "level": "INFO", "event": "deploy", "release": "r1"}]
    deployed = False
    while t < end:
        t += timedelta(seconds=float(rng.exponential(0.2)))
        if not deployed and t >= deploy:
            lines.append({"ts": deploy.isoformat(), "level": "INFO", "event": "deploy", "release": "r2"})
            deployed = True
        release = "r2" if deployed else "r1"
        endpoint = rng.choice(["/recommend", "/similar"], p=[0.8, 0.2])
        latency = float(rng.lognormal(np.log(35), 0.35))
        if release == "r2" and endpoint == "/recommend":
            latency += float(rng.exponential(25))
            if rng.random() < 0.08:  # r2 adds a feature lookup with a 250 ms timeout
                lines.append({"ts": t.isoformat(), "level": "ERROR", "event": "feature_store_timeout",
                              "release": release, "endpoint": str(endpoint), "timeout_ms": 250})
                lines.append({"ts": t.isoformat(), "level": "INFO", "event": "request", "release": release,
                              "endpoint": str(endpoint), "status": 503, "latency_ms": 251.0})
                continue
        if rng.random() < 0.002:
            lines.append({"ts": t.isoformat(), "level": "WARNING", "event": "slow_client", "release": release})
        lines.append({"ts": t.isoformat(), "level": "INFO", "event": "request", "release": release,
                      "endpoint": str(endpoint), "status": 200, "latency_ms": round(latency, 1)})
    path.write_text("\n".join(json.dumps(x) for x in lines) + "\n")


def triage(path: Path) -> None:
    records = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    deploys = [r for r in records if r["event"] == "deploy"]
    print("1. changes:")
    for d in deploys:
        print(f"   {d['ts']}  deploy {d['release']}")
    by_release = defaultdict(list)
    for r in records:
        if r["event"] == "request":
            by_release[r["release"]].append(r)
    print("2. behaviour by release:")
    for rel, reqs in by_release.items():
        lat = np.array([r["latency_ms"] for r in reqs])
        errors = sum(r["status"] >= 500 for r in reqs)
        print(f"   {rel}: {len(reqs):>5} requests, 5xx {errors / len(reqs):6.2%}, "
              f"p50 {np.percentile(lat, 50):5.1f} ms, p95 {np.percentile(lat, 95):5.1f} ms")
    errors = [r for r in records if r["level"] == "ERROR"]
    print("3. errors:")
    if errors:
        last_deploy = max(d["ts"] for d in deploys if d["ts"] <= errors[0]["ts"])
        gap = (datetime.fromisoformat(errors[0]["ts"]) - datetime.fromisoformat(last_deploy)).total_seconds()
        print(f"   first ERROR at {errors[0]['ts']} ({gap:.1f} s after the deploy at {last_deploy}): "
              f"{errors[0]['event']} release={errors[0]['release']}")
        for (event, rel), n in Counter((e["event"], e["release"]) for e in errors).most_common(3):
            print(f"   {n:>5} x {event} (release {rel})")
    print("4. 5xx rate by endpoint and release:")
    for rel, reqs in by_release.items():
        for ep in sorted({r["endpoint"] for r in reqs}):
            sub = [r for r in reqs if r["endpoint"] == ep]
            print(f"   {rel} {ep:<11} {sum(r['status'] >= 500 for r in sub) / len(sub):6.2%} of {len(sub)}")


def main(argv: list[str]) -> int:
    if argv:
        triage(Path(argv[0]))
        return 0
    with tempfile.TemporaryDirectory() as tmp:
        log = Path(tmp) / "recsys.log"
        generate(log)
        print(f"SYNTHETIC log: {sum(1 for _ in log.open())} lines\n")
        triage(log)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
