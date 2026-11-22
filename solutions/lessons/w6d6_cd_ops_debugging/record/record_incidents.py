"""AUTHOR-SIDE: replay the whole w6d6 lab with Docker and record what production looked like.

Writes lessons/w6d6_cd_ops_debugging/figures/incident_timeline.csv (production /readyz polled every
0.25 s) and incident_events.csv, and prints the log lines and inspect output quoted in the lesson.
Uses the reference ops/rollback.py. Run from the repository root:

    PIP_INSTALL_OPTS="--no-index --find-links=/srv/wheels" python solutions/lessons/w6d6_cd_ops_debugging/record/record_incidents.py

Removes every container, image tag and the registry it created at the end, and the ops/state/ it wrote.
"""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
LAB = ROOT / "solutions/lessons/w6d6_cd_ops_debugging/lab"
OUT = ROOT / "lessons/w6d6_cd_ops_debugging/figures"
sys.path.insert(0, str(LAB / "ops"))
import fgops  # noqa: E402
import rollback  # noqa: E402

T0 = time.time()
samples: list[tuple[float, int]] = []
events: list[tuple[float, str]] = []
stop = threading.Event()


def poll() -> None:
    while not stop.is_set():
        samples.append((round(time.time() - T0, 2), fgops.http_status(8102, "/readyz")))
        time.sleep(0.25)


def event(label: str) -> None:
    events.append((round(time.time() - T0, 2), label))
    print(f"[{time.time() - T0:6.1f}s] {label}")


def logs(n: int = 4) -> str:
    """The last ``n`` log lines of production that are not access-log lines (the poller floods those)."""
    out = subprocess.run(["docker", "logs", "fgops-production"], capture_output=True, text=True)
    lines = [ln for ln in (out.stdout + out.stderr).splitlines() if '"uvicorn.access"' not in ln]
    return "\n".join(lines[-n:])


def inspect() -> str:
    return fgops.docker("inspect", "-f", "{{.State.Status}} oom={{.State.OOMKilled}} exit={{.State.ExitCode}}",
                        "fgops-production", check=False)


def build_variant(release: str, version: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        svc = Path(tmp) / "service"
        shutil.copytree(LAB / "service", svc, ignore=shutil.ignore_patterns("__pycache__"))
        init = svc / "src/flowguard/__init__.py"
        init.write_text(init.read_text().replace('"0.6.0"', f'"{version}"'))
        fgops.build(release, svc, quiet=True)


def main() -> int:
    shutil.rmtree(fgops.STATE, ignore_errors=True)
    fgops.reset()
    fgops.registry_up()
    threading.Thread(target=poll, daemon=True).start()
    fgops.build("a1b2c3d4e5f6", quiet=True)
    event("release A to staging")
    fgops.deploy("staging", "a1b2c3d4e5f6", quiet=True)
    event("promote A")
    print(fgops.promote("staging", "production")["status"])
    build_variant("b7c8d9e0f1a2", "0.6.1")
    event("release B to staging")
    fgops.deploy("staging", "b7c8d9e0f1a2", quiet=True)
    event("promote B")
    print(fgops.promote("staging", "production")["status"])
    time.sleep(3)

    event("scenario 2 (bad promotion)")
    fgops.scenario(2)
    time.sleep(2)
    print("--- scenario 2 logs\n" + logs(6))
    target = rollback.select_rollback_target(fgops.load_history(), "production")
    print("rollback target:", target["release"])
    event("rollback")
    print("rollback exit:", rollback.main(["production", "--apply"]))
    time.sleep(3)

    event("scenario 1 (config)")
    fgops.scenario(1)
    time.sleep(2)
    print("--- scenario 1 logs\n" + logs(6))
    print("rollback would pick:", rollback.select_rollback_target(fgops.load_history(), "production")["release"])
    event("fix config, redeploy same digest")
    fgops.reset()
    cur = fgops.current("production")
    print(fgops.deploy("production", f"{cur['image']}@{cur['digest']}", note="revert MODEL_DIR", quiet=True)["status"])
    time.sleep(3)

    event("scenario 3 (memory)")
    fgops.scenario(3)
    time.sleep(8)
    print("--- scenario 3 inspect:", inspect())
    print("--- scenario 3 logs\n" + logs(3))
    event("fix memory, redeploy same digest")
    fgops.reset()
    cur = fgops.current("production")
    print(fgops.deploy("production", f"{cur['image']}@{cur['digest']}", note="revert memory", quiet=True)["status"])
    time.sleep(4)
    event("end")
    stop.set()
    time.sleep(0.5)
    print("--- history")
    fgops.history(None)

    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / "incident_timeline.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t_seconds", "readyz_status"])
        w.writerows(samples)
    with open(OUT / "incident_events.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["t_seconds", "event"])
        w.writerows(events)
    (OUT / "incident_history.json").write_text(json.dumps(fgops.load_history(), indent=2) + "\n")
    fgops.cleanup()
    shutil.rmtree(fgops.STATE, ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
