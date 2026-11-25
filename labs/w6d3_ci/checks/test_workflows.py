"""Contract checks for the learner's CI workflows (lesson w6d3, section 4)."""
from __future__ import annotations

import re
import shutil
import subprocess

import pytest
from wfutil import (
    PER_RUN,
    PINNED,
    all_runs,
    builds_image,
    job_running,
    jobs,
    needs,
    permission_values,
    steps,
    triggers,
    uses,
)

# ---------------------------------------------------------------- the per-push workflow (ci.yml)


def test_ci_runs_on_push_and_pull_request(ci):
    on = triggers(ci)
    assert "push" in on, "ci.yml must run on push"
    assert "pull_request" in on, "ci.yml must also run on pull_request, so a PR is checked before merge"


def test_ci_permissions_are_least_privilege(ci):
    perms = ci.get("permissions")
    assert isinstance(perms, dict) and perms, (
        "set top-level `permissions:` as a mapping (e.g. `contents: read`); without it the token gets "
        "the repository's default, which may include write access")
    for name, job in jobs(ci).items():
        for value in permission_values(perms) + permission_values(job.get("permissions")):
            assert value in ("read", "none"), (
                f"`{value}` permission in ci.yml (job {name!r} or top level): a test-and-build workflow "
                "only needs to read the repository")


def test_ci_cancels_superseded_runs(ci):
    conc = ci.get("concurrency")
    assert isinstance(conc, dict), "add a top-level `concurrency:` group so a new push cancels the old run"
    assert "github.ref" in str(conc.get("group", "")), "key the concurrency group on github.ref (per branch/PR)"
    assert conc.get("cancel-in-progress") is True, "set cancel-in-progress: true"


def test_actions_are_pinned_to_a_version(ci, evaluate):
    for ref in uses(ci) + uses(evaluate):
        assert "@" in ref, f"{ref}: pin every action to a version tag or a commit SHA"
        version = ref.split("@", 1)[1]
        assert PINNED.match(version), (
            f"{ref}: `{version}` is a moving branch name; use a release tag such as v7 or a full commit SHA")


def test_every_job_has_a_timeout(ci, evaluate):
    for wf in (ci, evaluate):
        for name, job in jobs(wf).items():
            t = job.get("timeout-minutes")
            assert isinstance(t, int) and 0 < t <= 60, (
                f"{wf['__path__'].name}: job {name!r} needs timeout-minutes (<= 60); the default is 360")


def test_lint_runs(ci):
    assert any("ruff check" in r for r in all_runs(ci)), "run `ruff check .` in ci.yml"


def test_tests_run_on_a_quoted_python_matrix(ci):
    name, job = job_running(ci, "pytest")
    assert job is not None, "no job in ci.yml runs pytest"
    assert not job.get("continue-on-error"), f"job {name!r}: tests must be able to fail the run"
    matrix = (job.get("strategy") or {}).get("matrix") or {}
    versions = matrix.get("python-version")
    assert isinstance(versions, list), f"job {name!r}: use strategy.matrix.python-version as a list"
    for v in versions:
        assert isinstance(v, str), (
            f"python-version {v!r} is read by YAML as a number; quote it. Unquoted 3.10 becomes 3.1")
    assert {"3.11", "3.12"} <= set(versions), f"the matrix must include \"3.11\" and \"3.12\", got {versions}"


def test_pip_cache_is_used(ci):
    name, job = job_running(ci, "pytest")
    assert job is not None
    ok = False
    for s in steps(job):
        ref = str(s.get("uses", ""))
        w = s.get("with") or {}
        if ref.startswith("actions/setup-python") and w.get("cache") == "pip":
            ok = True
        if ref.startswith("actions/cache") and "pip" in str(w.get("path", "")):
            key = str(w.get("key", ""))
            assert not any(p in key for p in PER_RUN), f"cache key {key!r} changes on every run, so it never hits"
            ok = True
    assert ok, f"job {name!r}: cache pip downloads (setup-python `cache: pip`, or actions/cache)"


def test_image_is_built_after_tests_and_smoke_tested(ci):
    test_name, _ = job_running(ci, "pytest")
    image_jobs = [(n, j) for n, j in jobs(ci).items() if builds_image(j)]
    assert image_jobs, "add a job that builds the Docker image"
    for name, job in image_jobs:
        assert name != test_name, "build the image in its own job, so tests and image build are separate gates"
        assert test_name in needs(job), (
            f"job {name!r} must declare `needs: [{test_name}]`: do not spend a build on code that fails its tests")
        text = "\n".join(str(s.get("run", "")) for s in steps(job))
        assert "smoke_test.py" in text, f"job {name!r}: run scripts/smoke_test.py against the running container"


def test_no_secret_is_interpolated_into_a_shell_command(ci, evaluate):
    for wf in (ci, evaluate):
        for r in all_runs(wf):
            assert not re.search(r"\$\{\{\s*secrets\.", r), (
                f"{wf['__path__'].name}: a `run:` interpolates a secret into the script text. Pass secrets "
                "through `env:` and never print them. (This workflow should need no secrets at all.)")


def test_per_push_gate_has_no_data_dependent_or_wall_clock_steps(ci):
    for r in all_runs(ci):
        assert "fetch_skab" not in r and "evaluate.py" not in r, (
            "ci.yml downloads data or runs the evaluation: that belongs to the scheduled workflow")
        assert not re.search(r"-m\s+['\"]?perf", r), "ci.yml runs the perf tests: they belong to the slow lane"


# ---------------------------------------------------------------- the scheduled workflow (evaluate.yml)


def test_evaluation_runs_on_schedule_not_on_push(evaluate):
    on = triggers(evaluate)
    assert "push" not in on and "pull_request" not in on, "evaluate.yml must not run on push or pull_request"
    assert "schedule" in on or "workflow_dispatch" in on, "run evaluate.yml on a schedule and/or workflow_dispatch"
    if "schedule" in on:
        crons = on["schedule"]
        assert isinstance(crons, list) and all("cron" in c for c in crons), "schedule needs `- cron: \"...\"` entries"


def test_evaluation_permissions_are_least_privilege(evaluate):
    perms = evaluate.get("permissions")
    assert isinstance(perms, dict) and perms, "set top-level permissions in evaluate.yml too"
    for value in permission_values(perms):
        assert value in ("read", "none"), f"evaluate.yml: `{value}` permission is not needed"


def test_evaluation_fetches_data_evaluates_and_keeps_the_report(evaluate):
    runs = "\n".join(all_runs(evaluate))
    assert "fetch_skab" in runs, "evaluate.yml must download the data (scripts/fetch_skab.py)"
    assert "evaluate.py" in runs, "evaluate.yml must run scripts/evaluate.py"
    assert re.search(r"-m\s+['\"]?perf", runs), "run the wall-clock tests here: pytest -m perf"
    uploads = [s for j in jobs(evaluate).values() for s in steps(j)
               if str(s.get("uses", "")).startswith("actions/upload-artifact")]
    assert uploads, "upload the report with actions/upload-artifact so it outlives the runner"
    assert any(str(s.get("if", "")).strip() == "always()" for s in uploads), (
        "upload the report `if: always()`: the report matters most when the evaluation step failed")


def test_actionlint_if_available(target):
    exe = shutil.which("actionlint")
    if exe is None:
        pytest.skip("actionlint not installed (optional: pip install actionlint-py)")
    proc = subprocess.run([exe, "-shellcheck=", "-pyflakes=",
                           str(target / ".github/workflows/ci.yml"), str(target / ".github/workflows/evaluate.yml")],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stdout + proc.stderr
