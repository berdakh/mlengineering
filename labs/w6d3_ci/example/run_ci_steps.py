"""Run the `run:` steps of one workflow job on your machine, in order, and time them.

    python labs/w6d3_ci/example/run_ci_steps.py labs/w6d3_ci/example/churnscore --job test

A teaching tool, not a CI emulator. It shows that a job is a list of steps and that a `run:` step is
just a shell script executed in the repository checkout. It does NOT run `uses:` actions (it prints
what they would do), does not expand `${{ }}` expressions beyond the first matrix entry, has no
secrets, no caches and no fresh virtual machine. A clean temporary virtual environment stands in for
the runner's Python so nothing is installed into yours. For a fuller local run, see `act`
(github.com/nektos/act), which needs Docker and is optional.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import tempfile
import time
import venv
from pathlib import Path

import yaml


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("project", type=Path)
    ap.add_argument("--workflow", default=".github/workflows/ci.yml")
    ap.add_argument("--job", required=True)
    args = ap.parse_args(argv)
    wf = yaml.safe_load((args.project / args.workflow).read_text())
    on = wf.get("on", wf.get(True))
    job = wf["jobs"][args.job]
    matrix = (job.get("strategy") or {}).get("matrix") or {}
    combos = 1
    for values in matrix.values():
        combos *= len(values) if isinstance(values, list) else 1
    print(f"workflow {wf.get('name')!r}: triggers {list(on) if isinstance(on, dict) else on}")
    print(f"job {args.job!r}: runs-on {job.get('runs-on')}, {combos} matrix combination(s) {matrix or ''}")
    print(f"permissions: {wf.get('permissions')}\n")
    with tempfile.TemporaryDirectory() as tmp:
        venv.EnvBuilder(with_pip=True, system_site_packages=True).create(tmp)
        env = dict(os.environ, PATH=f"{Path(tmp) / 'bin'}{os.pathsep}{os.environ['PATH']}", PYTHONDONTWRITEBYTECODE="1")
        total = 0.0
        for i, step in enumerate(job.get("steps") or [], 1):
            label = step.get("name") or step.get("uses") or step["run"].splitlines()[0]
            if "uses" in step:
                print(f"[{i}] {label:<40} uses an action (skipped here) with {step.get('with') or {}}")
                continue
            script = re.sub(r"\$\{\{[^}]*\}\}", "", step["run"])
            start = time.perf_counter()
            proc = subprocess.run(["bash", "-e", "-c", script], cwd=args.project, env=env,
                                  capture_output=True, text=True)
            took = time.perf_counter() - start
            total += took
            print(f"[{i}] {label:<40} exit {proc.returncode}  {took:6.2f} s")
            if proc.returncode != 0:
                print(proc.stdout[-2000:] + proc.stderr[-2000:])
                print("job FAILED: later steps are skipped, exactly as on a runner")
                return proc.returncode
        print(f"\njob succeeded: run steps took {total:.2f} s on this machine")
    return 0


if __name__ == "__main__":
    sys.exit(main())
