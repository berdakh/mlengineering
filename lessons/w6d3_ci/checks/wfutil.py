"""Small helpers for reading GitHub Actions workflow files as data (shared by the w6d3 checks)."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

PINNED = re.compile(r"^v\d+(\.\d+){0,2}$|^[0-9a-f]{40}$")
PER_RUN = ("github.sha", "github.run_id", "github.run_number", "github.run_attempt")


def load_workflow(path: Path) -> dict:
    yaml = pytest.importorskip("yaml", reason="PyYAML is needed: pip install pyyaml")
    if not path.is_file():
        pytest.fail(f"missing {path}", pytrace=False)
    try:
        wf = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        pytest.fail(f"{path.name} is not valid YAML: {exc}", pytrace=False)
    if not isinstance(wf, dict) or "jobs" not in wf:
        pytest.fail(f"{path.name}: no top-level 'jobs'", pytrace=False)
    # YAML 1.1 reads the bare key `on` as the boolean True; normalise it.
    if True in wf and "on" not in wf:
        wf["on"] = wf.pop(True)
    wf["__path__"] = path
    return wf


def triggers(wf: dict) -> dict:
    on = wf.get("on")
    if isinstance(on, str):
        return {on: None}
    if isinstance(on, list):
        return {t: None for t in on}
    return dict(on or {})


def jobs(wf: dict) -> dict:
    return wf.get("jobs") or {}


def steps(job: dict) -> list[dict]:
    return job.get("steps") or []


def run_text(job: dict) -> str:
    return "\n".join(str(s.get("run", "")) for s in steps(job))


def all_runs(wf: dict) -> list[str]:
    return [str(s["run"]) for j in jobs(wf).values() for s in steps(j) if "run" in s]


def uses(wf: dict) -> list[str]:
    return [str(s["uses"]) for j in jobs(wf).values() for s in steps(j) if "uses" in s]


def job_running(wf: dict, needle: str) -> tuple[str, dict] | tuple[None, None]:
    for name, job in jobs(wf).items():
        if needle in run_text(job):
            return name, job
    return None, None


def builds_image(job: dict) -> bool:
    return "docker build" in run_text(job) or any(
        str(s.get("uses", "")).startswith("docker/build-push-action") for s in steps(job))


def needs(job: dict) -> list[str]:
    n = job.get("needs") or []
    return [n] if isinstance(n, str) else list(n)


def permission_values(perms) -> list[str]:
    if perms is None:
        return []
    if isinstance(perms, str):
        return [perms]
    return [str(v) for v in perms.values()]
