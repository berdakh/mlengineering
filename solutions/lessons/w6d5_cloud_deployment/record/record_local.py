"""AUTHOR-SIDE: measure the local equivalent of the deployment, for the w6d5 figures.

Builds the lab's image, then 5 times: `docker run` with the task definition's settings (0.25 CPU,
512 MiB, same env and health check) and records seconds until /healthz answers 200, /readyz answers 200,
and Docker reports the container healthy, plus memory in use once healthy. Also records the image's
layer sizes. Writes lessons/w6d5_cloud_deployment/figures/{startup_runs,image_layers}.csv.
Removes every container and the image afterwards. Run from the repository root:

    PIP_INSTALL_OPTS="--no-index --find-links=/srv/wheels" python solutions/lessons/w6d5_cloud_deployment/record/record_local.py
"""
from __future__ import annotations

import csv
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SERVICE = ROOT / "solutions/lessons/w6d5_cloud_deployment/lab/service"
OUT = ROOT / "lessons/w6d5_cloud_deployment/figures"
IMAGE = "flowguard-w6d5-record:0d5c0ffee000"
NAME = "flowguard-w6d5-record"
PORT = 18085
HEALTH = "python -c \"import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=2)\" || exit 1"


def sh(*args: str) -> str:
    return subprocess.run(list(args), capture_output=True, text=True, check=True).stdout.strip()


def code(path: str) -> int:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}{path}", timeout=1) as r:
            return r.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except OSError:
        return 0


def mib(text: str) -> float:
    value = text.split("/")[0].strip()
    for unit, f in (("GiB", 1024), ("MiB", 1), ("KiB", 1 / 1024)):
        if value.endswith(unit):
            return float(value[: -len(unit)]) * f
    return float("nan")


def main() -> None:
    sh("docker", "build", "-q", "--build-arg", f"PIP_INSTALL_OPTS={os.environ.get('PIP_INSTALL_OPTS', '')}",
       "-t", IMAGE, str(SERVICE))
    rows = []
    for run in range(1, 6):
        subprocess.run(["docker", "rm", "-f", NAME], capture_output=True)
        t0 = time.time()
        sh("docker", "run", "-d", "--name", NAME, "-p", f"127.0.0.1:{PORT}:8000",
           "-e", "FLOWGUARD_ENV=production", "-e", "FLOWGUARD_RELEASE=0d5c0ffee000",
           "-e", "FLOWGUARD_MODEL_DIR=/models/flowguard-z/1.0.0", "--memory", "512m", "--cpus", "0.25",
           "--health-cmd", HEALTH, "--health-interval", "2s", "--health-timeout", "5s",
           "--health-retries", "3", "--health-start-period", "20s", IMAGE)
        marks = {}
        while len(marks) < 3 and time.time() - t0 < 60:
            t = time.time() - t0
            if "healthz" not in marks and code("/healthz") == 200:
                marks["healthz"] = t
            if "readyz" not in marks and code("/readyz") == 200:
                marks["readyz"] = t
            if "healthy" not in marks and sh("docker", "inspect", "-f", "{{.State.Health.Status}}", NAME) == "healthy":
                marks["healthy"] = t
            time.sleep(0.05)
        mem = mib(sh("docker", "stats", "--no-stream", "--format", "{{.MemUsage}}", NAME))
        rows.append([run, round(marks["healthz"], 2), round(marks["readyz"], 2), round(marks["healthy"], 2),
                     round(mem, 1)])
        print(rows[-1])
    subprocess.run(["docker", "rm", "-f", NAME], capture_output=True)
    layers = []
    for line in sh("docker", "history", "--no-trunc", "--format", "{{.Size}}\t{{.CreatedBy}}", IMAGE).splitlines():
        size, created = line.split("\t", 1)
        layers.append([size, created[:90]])
    sh("docker", "rmi", "-f", IMAGE)
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "startup_runs.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["run", "healthz_s", "readyz_s", "healthy_s", "mem_mib_when_healthy"])
        w.writerows(rows)
    with open(OUT / "image_layers.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["size", "created_by"])
        w.writerows(layers)


if __name__ == "__main__":
    main()
