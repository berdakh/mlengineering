"""Checks for the w6d3 challenge: the three CI failures are fixed, by behaviour where possible."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from wfutil import PER_RUN, all_runs, builds_image, jobs, load_workflow, steps, triggers

HERE = Path(__file__).resolve().parent


def _pytest(project: Path, *args: str) -> subprocess.CompletedProcess:
    env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(project / "src"), str(HERE)]),
               PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--strict-markers", *args],
                          cwd=project, env=env, capture_output=True, text=True, timeout=180)


# ------------------------------------------------------------------ 1. the flaky timing test

def test_default_run_has_no_wall_clock_assertion(project):
    """The per-push run must pass even when the wall clock runs 0.5 s per read."""
    proc = _pytest(project, "-p", "slowclock")
    assert proc.returncode == 0, ("the default test run still depends on elapsed wall-clock time "
                                  "(or fails for another reason):\n" + proc.stdout[-1500:])
    passed = re.search(r"(\d+) passed", proc.stdout)
    assert passed and int(passed.group(1)) >= 5, "keep the functional API tests in the default run"


def test_latency_check_is_kept_in_the_perf_lane(project):
    proc = _pytest(project, "-m", "perf", "--collect-only")
    n = re.findall(r"(\d+) (?:tests? collected|selected)", proc.stdout)
    assert proc.returncode == 0 and n and int(n[-1]) >= 1, (
        "keep the latency test, marked `perf` (and register the marker): `pytest -m perf` must collect it\n"
        + proc.stdout[-800:])


def test_a_scheduled_workflow_runs_the_perf_lane(project, ci):
    found = False
    for path in (project / ".github" / "workflows").glob("*.y*ml"):
        wf = load_workflow(path)
        on = triggers(wf)
        runs = "\n".join(all_runs(wf))
        if re.search(r"-m\s+['\"]?perf", runs):
            assert "push" not in on and "pull_request" not in on, f"{path.name}: the perf lane must not gate pushes"
            assert "schedule" in on or "workflow_dispatch" in on, f"{path.name}: run it on schedule/dispatch"
            found = True
    assert found, "add a scheduled (or manually dispatched) workflow that runs `pytest -m perf`"


# ------------------------------------------------------------------ 2. the cache that never hits

def test_cache_key_is_stable_and_tracks_dependencies(project, ci):
    cached = False
    for name, job in jobs(ci).items():
        for s in steps(job):
            ref, w = str(s.get("uses", "")), s.get("with") or {}
            if ref.startswith("actions/cache"):
                key = str(w.get("key", ""))
                assert not any(p in key for p in PER_RUN), f"job {name!r}: cache key {key!r} is new on every run"
                files = re.findall(r"hashFiles\(\s*'([^']+)'", key)
                assert files, f"job {name!r}: key the cache on hashFiles(<dependency file>)"
                for f in files:
                    assert list(project.glob(f)), f"hashFiles('{f}') matches no file in the project"
                cached = True
            if ref.startswith("actions/setup-python") and w.get("cache") == "pip":
                dep = w.get("cache-dependency-path")
                if dep:
                    for f in str(dep).split():
                        assert list(project.glob(f)), f"cache-dependency-path {f!r} matches no file"
                else:
                    assert (project / "pyproject.toml").is_file() or (project / "requirements.txt").is_file()
                cached = True
    assert cached, "keep a pip cache in ci.yml (fixed, not removed)"


# ------------------------------------------------------------------ 3. the missing tool in the image

def _dockerfile_installs(project: Path, tool: str) -> bool:
    text = (project / "Dockerfile").read_text()
    return bool(re.search(rf"(apt-get|apk)[^\n]*install[^\n]*\b{tool}\b", text))


def test_image_check_does_not_need_tools_the_image_lacks(project, ci):
    image_jobs = [j for j in jobs(ci).values() if builds_image(j)]
    assert image_jobs, "keep the image job"
    for job in image_jobs:
        for s in steps(job):
            for line in str(s.get("run", "")).splitlines():
                inside = re.search(r"docker\s+(exec|run)\b", line)
                for tool in ("curl", "wget"):
                    if inside and re.search(rf"\b{tool}\b", line):
                        assert _dockerfile_installs(project, tool), (
                            f"`{line.strip()}` runs {tool} inside the container, but the Dockerfile does not "
                            f"install {tool} (python:3.12-slim has neither curl nor wget)")
        text = "\n".join(str(s.get("run", "")) for s in steps(job))
        assert re.search(r"smoke_test\.py|healthz|readyz", text), "the image job must still check the running service"
    dockerfile = (project / "Dockerfile").read_text()
    for tool in ("curl", "wget"):
        if re.search(rf"HEALTHCHECK[^\n]*\b{tool}\b", dockerfile):
            assert _dockerfile_installs(project, tool), f"HEALTHCHECK uses {tool}, which the image does not install"


def test_fixed_workflow_passes_actionlint_if_available(project):
    exe = shutil.which("actionlint")
    if exe is None:
        pytest.skip("actionlint not installed (optional: pip install actionlint-py)")
    files = [str(p) for p in (project / ".github" / "workflows").glob("*.y*ml")]
    proc = subprocess.run([exe, "-shellcheck=", "-pyflakes=", *files], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr


# ------------------------------------------------------------------ the write-up

def test_diagnosis_written(target):
    path = target / "DIAGNOSIS.md"
    assert path.is_file(), "write DIAGNOSIS.md"
    text = path.read_text()
    sections = re.split(r"^## ", text, flags=re.M)[1:]
    assert len(sections) >= 3, "one `## ` section per log"
    for i, words in enumerate([("perf", "flak"), ("cache",), ("curl",)]):
        body = sections[i].lower()
        assert len(body.split()) >= 60, f"section {i + 1} is too short to explain cause, fix and evidence"
        assert any(w in body for w in words), f"section {i + 1} should name the cause ({' / '.join(words)})"
