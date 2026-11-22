"""Collect the measurements behind lesson w6d3's figures (host-dependent; results go to figure_data.csv).

    python lessons/w6d3_ci/figures/measure.py          # about 3-5 minutes, needs network for pip
    python lessons/w6d3_ci/figures/make_figures.py     # plots from the CSV

1. Dependency install time for the lab project in a fresh virtual environment: cold (empty pip
   cache) and warm (the same cache reused), two runs each. This is what a CI cache saves.
2. How often the challenge's 50 ms timing test fails, as a function of competing CPU-bound
   processes on the machine (0, 2, 4, 6 busy-loop processes; 40 runs each). This is why a
   single wall-clock assertion is flaky on shared runners.
"""
from __future__ import annotations

import csv
import os
import subprocess
import sys
import tempfile
import time
import venv
from pathlib import Path

HERE = Path(__file__).resolve().parent
UNIT = HERE.parent
LAB = UNIT / "lab"
CHALLENGE_PROJECT = UNIT / "challenge" / "project"
OUT = HERE / "figure_data.csv"


def install_time(cache_dir: Path) -> float:
    with tempfile.TemporaryDirectory() as tmp:
        venv.EnvBuilder(with_pip=True).create(tmp)
        py = Path(tmp) / "bin" / "python"
        env = dict(os.environ, PIP_CACHE_DIR=str(cache_dir), PIP_DISABLE_PIP_VERSION_CHECK="1")
        start = time.perf_counter()
        subprocess.run([str(py), "-m", "pip", "install", "-q", f"{LAB}[dev]"], check=True, env=env,
                       capture_output=True)
        return time.perf_counter() - start


def flaky_rate(n_busy: int, runs: int = 40) -> int:
    busy = [subprocess.Popen([sys.executable, "-c", "while True: pass"]) for _ in range(n_busy)]
    failures = 0
    try:
        time.sleep(0.5)
        env = dict(os.environ, PYTHONPATH=str(CHALLENGE_PROJECT / "src"), PYTHONDONTWRITEBYTECODE="1")
        for _ in range(runs):
            proc = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider",
                                   "tests/test_latency.py"], cwd=CHALLENGE_PROJECT, env=env, capture_output=True)
            failures += proc.returncode != 0
    finally:
        for p in busy:
            p.kill()
    return failures


def main() -> None:
    rows = []
    with tempfile.TemporaryDirectory() as cache:
        for i in range(2):
            rows.append({"measure": "install_s", "condition": "cold", "rep": i,
                         "value": round(install_time(Path(tempfile.mkdtemp(dir=cache))), 2)})
        warm = Path(cache) / "shared"
        install_time(warm)  # fill
        for i in range(2):
            rows.append({"measure": "install_s", "condition": "warm", "rep": i, "value": round(install_time(warm), 2)})
    for n_busy in (0, 2, 4, 6):
        rows.append({"measure": "flaky_failures_of_40", "condition": n_busy, "rep": 0, "value": flaky_rate(n_busy)})
        print(rows[-1], flush=True)
    with OUT.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["measure", "condition", "rep", "value"])
        w.writeheader()
        w.writerows(rows)
    for r in rows:
        print(r)


if __name__ == "__main__":
    main()
