"""Run the real measurements behind lesson w6d4's figures (host-dependent; about 10 minutes).

    python lessons/w6d4_latency_resources/figures/measure.py
    python lessons/w6d4_latency_resources/figures/make_figures.py

Uses the REFERENCE solution's measure_service.py (open-loop load on 127.0.0.1) for 1, 2 and 4 uvicorn
workers at four request rates, twice each in interleaved order, plus one detailed run that keeps every
request's latency for the distribution figure. `--only-serve` re-runs just the serve.py (TCP_NODELAY) configuration. Results are JSON files in figures/data/.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LAB = ROOT / "solutions" / "lessons" / "w6d4_latency_resources" / "lab"
DATA = HERE / "data"
RATES = ["20", "60", "90", "120"]


def run(workers: int, rep: int, launcher: str = "uvicorn") -> None:
    tag = "" if launcher == "uvicorn" else f"_{launcher}"
    out = DATA / f"workers{workers}{tag}_rep{rep}.json"
    cmd = [sys.executable, str(LAB / "measure_service.py"), "--workers", str(workers), "--rates", *RATES,
           "--duration", "15", "--warmup", "3", "--launcher", launcher, "--out", str(out)]
    print(" ".join(cmd[1:]), flush=True)
    subprocess.run(cmd, check=True)


def main() -> None:
    DATA.mkdir(exist_ok=True)
    if "--only-serve" in sys.argv:
        for rep in (1, 2):
            run(2, rep, launcher="serve")
        return
    for rep in (1, 2):
        for workers in (1, 2, 4):
            run(workers, rep)
        run(2, rep, launcher="serve")     # the fix: TCP_NODELAY with 2 workers
    cmd = [sys.executable, str(LAB / "measure_service.py"), "--workers", "1", "--rates", "60", "95",
           "--duration", "30", "--warmup", "3", "--keep-latencies", "--out", str(DATA / "detail_workers1.json")]
    subprocess.run(cmd, check=True)
    print(json.dumps(sorted(p.name for p in DATA.glob("*.json"))))


if __name__ == "__main__":
    main()
